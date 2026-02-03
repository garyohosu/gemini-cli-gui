from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import threading
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from core.audit_log import AuditLog
from core.operation_executor import OperationExecutor
from core.operations_parser import OperationParseError, parse_operations
from core.workspace_sandbox import WorkspaceSandbox


VERSION = "0.1.0"


@dataclass
class PromptResponse:
    request_id: Optional[str]
    payload: dict


class GeminiClient(QtCore.QObject):
    response_ready = QtCore.Signal(object)
    started = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base_url = base_url.rstrip("/")

    def send_prompt(self, prompt: str, timeout_ms: int) -> None:
        thread = threading.Thread(
            target=self._send_blocking,
            args=(prompt, timeout_ms),
            daemon=True,
        )
        thread.start()

    def _send_blocking(self, prompt: str, timeout_ms: int) -> None:
        payload = json.dumps(
            {
                "prompt": prompt,
                "timeoutMs": timeout_ms,
            }
        ).encode("utf-8")
        start_req = urllib.request.Request(
            f"{self._base_url}/prompt/start",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(start_req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                payload_json = json.loads(raw)
                request_id = payload_json.get("requestId")
                if not request_id:
                    raise RuntimeError("requestId not returned")
                self.started.emit(request_id)

            result_req = urllib.request.Request(
                f"{self._base_url}/prompt/result?requestId={request_id}",
                headers={"Content-Type": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(result_req, timeout=timeout_ms / 1000) as resp:
                raw = resp.read().decode("utf-8")
                payload_json = json.loads(raw)
                response = PromptResponse(request_id=payload_json.get("requestId"), payload=payload_json)
                self.response_ready.emit(response)
        except Exception as exc:
            self.error.emit(str(exc))

    def cancel(self, request_id: str) -> None:
        payload = json.dumps({"requestId": request_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/cancel",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5):
                return
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gemini CLI GUI Wrapper")
        self.resize(1000, 700)

        self._setup_logging()
        self._client = GeminiClient("http://127.0.0.1:9876")
        self._client.response_ready.connect(self._on_response)
        self._client.started.connect(self._on_started)
        self._client.error.connect(self._on_error)

        self._workspace_root: Optional[Path] = None
        self._sandbox: Optional[WorkspaceSandbox] = None
        self._audit_log: Optional[AuditLog] = None
        self._executor: Optional[OperationExecutor] = None
        self._pending_operations = []
        self._current_request_id: Optional[str] = None

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        # メニューバー
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        view_menu = menubar.addMenu("View")
        window_menu = menubar.addMenu("Window")
        help_menu = menubar.addMenu("Help")

        # メインウィジェット
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ヘッダー
        header = self._build_header()
        main_layout.addWidget(header)

        # コンテンツエリア（サイドバー + メイン）
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 左サイドバー
        sidebar = self._build_sidebar()
        content_layout.addWidget(sidebar)

        # 右メインエリア
        main_area = self._build_main_area()
        content_layout.addWidget(main_area, stretch=1)

        main_layout.addWidget(content, stretch=1)

        # フッター
        footer = self._build_footer()
        main_layout.addWidget(footer)

    def _build_header(self) -> QtWidgets.QWidget:
        header = QtWidgets.QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(40)

        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QtWidgets.QLabel("Gemini CLI GUI Wrapper")
        title.setObjectName("HeaderTitle")

        self._status_indicator = QtWidgets.QLabel()
        self._status_indicator.setObjectName("StatusIndicator")
        self._update_status("停止中", False)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self._status_indicator)

        return header

    def _build_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)

        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # ワークスペースセクション
        ws_section = QtWidgets.QWidget()
        ws_layout = QtWidgets.QVBoxLayout(ws_section)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(8)

        ws_label = QtWidgets.QLabel("ワークスペース")
        ws_label.setObjectName("SectionLabel")

        self._folder_btn = QtWidgets.QPushButton("フォルダを選択")
        self._folder_btn.setObjectName("PrimaryButton")
        self._folder_btn.clicked.connect(self._on_select_workspace)

        self._workspace_label = QtWidgets.QLabel("未選択")
        self._workspace_label.setObjectName("WorkspaceLabel")
        self._workspace_label.setWordWrap(True)

        ws_layout.addWidget(ws_label)
        ws_layout.addWidget(self._folder_btn)
        ws_layout.addWidget(self._workspace_label)

        layout.addWidget(ws_section)

        # ファイル一覧セクション
        files_section = QtWidgets.QWidget()
        files_layout = QtWidgets.QVBoxLayout(files_section)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)

        files_label = QtWidgets.QLabel("ファイル一覧")
        files_label.setObjectName("SectionLabel")

        self._file_list = QtWidgets.QListWidget()
        self._file_list.setObjectName("FileList")
        self._file_list.addItem("ワークスペースを選択してください")

        files_layout.addWidget(files_label)
        files_layout.addWidget(self._file_list, stretch=1)

        layout.addWidget(files_section, stretch=1)

        return sidebar

    def _build_main_area(self) -> QtWidgets.QWidget:
        main_area = QtWidgets.QWidget()
        main_area.setObjectName("MainArea")

        layout = QtWidgets.QVBoxLayout(main_area)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 出力ヘッダー
        output_header = QtWidgets.QWidget()
        output_header_layout = QtWidgets.QHBoxLayout(output_header)
        output_header_layout.setContentsMargins(0, 0, 0, 0)

        output_label = QtWidgets.QLabel("出力")
        output_label.setObjectName("SectionLabel")

        clear_btn = QtWidgets.QPushButton("クリア")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.clicked.connect(self._on_clear_output)

        output_header_layout.addWidget(output_label)
        output_header_layout.addStretch()
        output_header_layout.addWidget(clear_btn)

        layout.addWidget(output_header)

        # 出力エリア
        self._output = QtWidgets.QTextEdit()
        self._output.setObjectName("OutputArea")
        self._output.setReadOnly(True)
        self._append_welcome_message()

        layout.addWidget(self._output, stretch=1)

        # 入力エリア
        input_container = QtWidgets.QWidget()
        input_container.setObjectName("InputContainer")
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)

        self._input = QtWidgets.QTextEdit()
        self._input.setObjectName("InputArea")
        self._input.setPlaceholderText("メッセージを入力... (Ctrl+Enter で送信)")
        self._input.setFixedHeight(80)
        self._input.installEventFilter(self)

        self._send_btn = QtWidgets.QPushButton("送信")
        self._send_btn.setObjectName("SendButton")
        self._send_btn.setFixedSize(60, 36)
        self._send_btn.clicked.connect(self._on_send)

        input_layout.addWidget(self._input, stretch=1)
        input_layout.addWidget(self._send_btn, alignment=QtCore.Qt.AlignBottom)

        layout.addWidget(input_container)

        return main_area

    def _build_footer(self) -> QtWidgets.QWidget:
        footer = QtWidgets.QWidget()
        footer.setObjectName("Footer")
        footer.setFixedHeight(24)

        layout = QtWidgets.QHBoxLayout(footer)
        layout.setContentsMargins(16, 0, 16, 0)

        version_label = QtWidgets.QLabel(f"Gemini CLI GUI Wrapper v{VERSION}")
        version_label.setObjectName("FooterLabel")

        platform_label = QtWidgets.QLabel(f"Platform: {sys.platform}")
        platform_label.setObjectName("FooterLabel")

        layout.addWidget(version_label)
        layout.addStretch()
        layout.addWidget(platform_label)

        return footer

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background: #f5f5f5;
            }

            /* ヘッダー */
            #Header {
                background: #2563eb;
            }
            #HeaderTitle {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            #StatusIndicator {
                color: white;
                font-size: 12px;
            }

            /* サイドバー */
            #Sidebar {
                background: #f0f0f0;
                border-right: 1px solid #d0d0d0;
            }
            #SectionLabel {
                color: #333;
                font-size: 13px;
                font-weight: bold;
            }
            #WorkspaceLabel {
                color: #666;
                font-size: 11px;
            }
            #PrimaryButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            #PrimaryButton:hover {
                background: #1d4ed8;
            }
            #FileList {
                background: white;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 11px;
            }
            #FileList::item {
                padding: 4px;
            }

            /* メインエリア */
            #MainArea {
                background: #f5f5f5;
            }
            #SecondaryButton {
                background: #4a5568;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            #SecondaryButton:hover {
                background: #2d3748;
            }

            /* 出力エリア */
            #OutputArea {
                background: #1e1e1e;
                color: #d4d4d4;
                border: none;
                border-radius: 4px;
                font-family: Consolas, 'MS Gothic', monospace;
                font-size: 12px;
                padding: 12px;
            }

            /* 入力エリア */
            #InputContainer {
                background: white;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            #InputArea {
                background: white;
                border: none;
                font-size: 12px;
            }
            #SendButton {
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            #SendButton:hover {
                background: #dc2626;
            }
            #SendButton:disabled {
                background: #9ca3af;
            }

            /* フッター */
            #Footer {
                background: #e5e5e5;
                border-top: 1px solid #d0d0d0;
            }
            #FooterLabel {
                color: #666;
                font-size: 11px;
            }

            /* メニューバー */
            QMenuBar {
                background: #f5f5f5;
                border-bottom: 1px solid #d0d0d0;
            }
            QMenuBar::item {
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background: #e0e0e0;
            }
        """)

    def _append_welcome_message(self) -> None:
        self._append_output("Gemini CLI GUI Wrapper へようこそ!", "welcome")
        self._append_output("", "")
        self._append_output("1. まず「フォルダを選択」からワークスペースを選択してください", "info")
        self._append_output("2. 下のテキストエリアからメッセージを送信できます", "info")
        self._append_output("", "")

    def _append_output(self, message: str, msg_type: str = "normal") -> None:
        cursor = self._output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)

        if msg_type == "welcome":
            color = "#4ade80"  # green
        elif msg_type == "info":
            color = "#d4d4d4"  # gray
        elif msg_type == "system":
            color = "#60a5fa"  # blue
        elif msg_type == "error":
            color = "#f87171"  # red
        elif msg_type == "user":
            color = "#fbbf24"  # yellow
        else:
            color = "#d4d4d4"

        timestamp = datetime.now().strftime("%H:%M:%S")

        if msg_type in ("system", "error", "user"):
            prefix = f"[{timestamp}] "
            if msg_type == "system":
                prefix += "[SYS] "
            elif msg_type == "error":
                prefix += "[ERR] "
            elif msg_type == "user":
                prefix += "[YOU] "
        else:
            prefix = ""

        html = f'<span style="color: {color};">{prefix}{message}</span><br>'
        cursor.insertHtml(html)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _update_status(self, text: str, running: bool) -> None:
        indicator = "●" if running else "●"
        color = "#4ade80" if running else "#9ca3af"
        self._status_indicator.setText(f'<span style="color: {color};">{indicator}</span> {text}')

    def _on_select_workspace(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "ワークスペースを選択")
        if not directory:
            return

        self._workspace_root = Path(directory)
        self._workspace_label.setText(directory)

        try:
            self._sandbox = WorkspaceSandbox.create(self._workspace_root)
            self._audit_log = AuditLog(self._workspace_root / "logs")
            self._executor = OperationExecutor(self._sandbox, self._audit_log)
        except Exception as e:
            self._append_output(f"ワークスペース設定エラー: {e}", "error")
            return

        self._append_output(f"ワークスペースを設定しました: {directory}", "system")
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        self._file_list.clear()
        if not self._workspace_root or not self._workspace_root.exists():
            self._file_list.addItem("ワークスペースを選択してください")
            return

        try:
            items = []
            for item in self._workspace_root.iterdir():
                if item.name.startswith("."):
                    continue
                prefix = "📁 " if item.is_dir() else "📄 "
                items.append((item.name, prefix + item.name))

            items.sort(key=lambda x: (not x[0].startswith("📁"), x[0].lower()))

            for _, display in items[:50]:  # 最大50件
                self._file_list.addItem(display)

            if len(list(self._workspace_root.iterdir())) > 50:
                self._file_list.addItem("...")

        except Exception as e:
            self._file_list.addItem(f"エラー: {e}")

    def _on_clear_output(self) -> None:
        self._output.clear()
        self._append_welcome_message()

    def _on_send(self) -> None:
        prompt = self._input.toPlainText().strip()
        if not prompt:
            return

        if not self._workspace_root:
            self._append_output("先にワークスペースを選択してください", "error")
            return

        self._append_output(prompt, "user")
        self._input.clear()
        self._send_btn.setEnabled(False)
        self._update_status("実行中", True)
        self._current_request_id = None
        self._client.send_prompt(prompt, timeout_ms=120000)

    def _on_response(self, response: PromptResponse) -> None:
        payload = response.payload
        text = payload.get("response", {}).get("response")
        if not text:
            text = json.dumps(payload, ensure_ascii=False, indent=2)

        self._append_output(text, "system")
        self._send_btn.setEnabled(True)
        self._update_status("停止中", False)
        self._current_request_id = None
        self._load_operations(payload)

    def _on_started(self, request_id: str) -> None:
        self._current_request_id = request_id
        self._append_output(f"ipc:gemini:status", "system")

    def _on_error(self, message: str) -> None:
        self._append_output(f"エラー: {message}", "error")
        self._send_btn.setEnabled(True)
        self._update_status("停止中", False)
        logging.getLogger(__name__).error("GUI error: %s", message)

    def _load_operations(self, payload: dict) -> None:
        self._pending_operations = []
        operations = self._extract_operations(payload)
        if operations is None:
            return

        try:
            parsed = parse_operations(json.dumps({"operations": operations}))
            self._pending_operations = list(parsed)
            if self._pending_operations:
                self._append_output(f"操作提案: {len(self._pending_operations)} 件", "system")
        except OperationParseError as exc:
            self._append_output(f"操作解析エラー: {exc}", "error")

    def _extract_operations(self, payload: dict) -> Optional[list]:
        if "operations" in payload and isinstance(payload["operations"], list):
            return payload["operations"]
        response = payload.get("response")
        if isinstance(response, dict) and isinstance(response.get("operations"), list):
            return response["operations"]
        if isinstance(response, str):
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict) and isinstance(parsed.get("operations"), list):
                    return parsed["operations"]
            except json.JSONDecodeError:
                return None
        return None

    def _setup_logging(self) -> None:
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "gui.log"
        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj == self._input and event.type() == QtCore.QEvent.KeyPress:
            key_event = event
            if key_event.key() == QtCore.Qt.Key_Return and key_event.modifiers() == QtCore.Qt.ControlModifier:
                self._on_send()
                return True
        return super().eventFilter(obj, event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Yu Gothic UI", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
