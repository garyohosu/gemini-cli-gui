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
        self.setWindowTitle("gemini-cli-gui")
        self.resize(900, 600)

        self._setup_logging()
        self._apply_style()
        self._client = GeminiClient("http://127.0.0.1:9876")
        self._client.response_ready.connect(self._on_response)
        self._client.started.connect(self._on_started)
        self._client.error.connect(self._on_error)

        self._chat = QtWidgets.QTextEdit()
        self._chat.setReadOnly(True)

        self._input = QtWidgets.QTextEdit()
        self._input.setPlaceholderText("Type your request...")

        self._send = QtWidgets.QPushButton("Send")
        self._send.setObjectName("PrimaryButton")
        self._send.clicked.connect(self._on_send)

        self._approve = QtWidgets.QPushButton("Approve")
        self._approve.setEnabled(False)
        self._approve.clicked.connect(self._on_approve)

        self._cancel = QtWidgets.QPushButton("Cancel")
        self._cancel.setObjectName("DangerButton")
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(self._on_cancel)

        self._ops_list = QtWidgets.QTableWidget(0, 7)
        self._ops_list.setHorizontalHeaderLabels(["type", "path/src", "dst", "mode", "result", "error", "detail"])
        self._ops_list.horizontalHeader().setStretchLastSection(True)
        self._ops_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._ops_list.setAlternatingRowColors(True)
        self._ops_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self._ops_status = QtWidgets.QLabel("No pending operations.")

        self._log_view = QtWidgets.QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("Logs will appear here...")

        self._log_refresh = QtWidgets.QPushButton("Refresh Logs")
        self._log_refresh.clicked.connect(self._refresh_logs)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self._send)
        button_row.addWidget(self._cancel)
        button_row.addWidget(self._approve)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._workspace_root = Path.cwd()
        self._sandbox = WorkspaceSandbox.create(self._workspace_root)
        self._audit_log = AuditLog(self._workspace_root / "logs")
        self._executor = OperationExecutor(self._sandbox, self._audit_log)
        self._pending_operations = []

        layout.addWidget(self._build_header())

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_beginner_tab(button_row), "Chat")
        self._tabs.addTab(self._build_advanced_tab(), "Advanced")
        layout.addWidget(self._tabs)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _on_send(self) -> None:
        prompt = self._input.toPlainText().strip()
        if not prompt:
            return
        self._append_chat("You", prompt)
        self._input.clear()
        self._send.setEnabled(False)
        self._cancel.setEnabled(True)
        self._current_request_id = None
        self._client.send_prompt(prompt, timeout_ms=120000)

    def _on_response(self, response: PromptResponse) -> None:
        payload = response.payload
        text = payload.get("response", {}).get("response")
        if not text:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        self._append_chat("Gemini", text)
        self._send.setEnabled(True)
        self._cancel.setEnabled(False)
        self._current_request_id = None
        self._load_operations(payload)
        self._refresh_logs()

    def _on_started(self, request_id: str) -> None:
        self._current_request_id = request_id
        self._append_chat("System", f"requestId: {request_id}")

    def _on_error(self, message: str) -> None:
        self._append_chat("Error", message)
        self._send.setEnabled(True)
        self._cancel.setEnabled(False)
        logging.getLogger(__name__).error("GUI error: %s", message)
        self._refresh_logs()

    def _on_cancel(self) -> None:
        if not self._current_request_id:
            return
        self._append_chat("System", "Cancelling request...")
        self._client.cancel(self._current_request_id)
        self._cancel.setEnabled(False)

    def _load_operations(self, payload: dict) -> None:
        self._ops_list.setRowCount(0)
        self._approve.setEnabled(False)
        self._pending_operations = []
        operations = self._extract_operations(payload)
        if operations is None:
            self._ops_status.setText("No operations found.")
            return

        try:
            parsed = parse_operations(json.dumps({"operations": operations}))
        except OperationParseError as exc:
            self._ops_status.setText(f"Operations parse error: {exc}")
            return

        for op in parsed:
            row = self._ops_list.rowCount()
            self._ops_list.insertRow(row)
            type_item = QtWidgets.QTableWidgetItem(op.type)
            self._ops_list.setItem(row, 0, type_item)
            self._ops_list.setItem(row, 1, QtWidgets.QTableWidgetItem(op.path or op.src or ""))
            self._ops_list.setItem(row, 2, QtWidgets.QTableWidgetItem(op.dst or ""))
            self._ops_list.setItem(row, 3, QtWidgets.QTableWidgetItem(op.mode or ""))
            self._ops_list.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
            self._ops_list.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
            self._ops_list.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
            self._pending_operations.append(op)
            self._apply_risk_styling(row, op)

        self._ops_status.setText(f"Pending operations: {len(parsed)}")
        self._approve.setEnabled(True)

    def _on_approve(self) -> None:
        if not self._pending_operations:
            return
        if self._has_dangerous_ops(self._pending_operations):
            if not self._confirm_dangerous_ops():
                self._append_chat("System", "Approval cancelled for dangerous operations.")
                return
        results = self._executor.execute(self._pending_operations)
        ok = sum(1 for r in results if r.status == "ok")
        failed = sum(1 for r in results if r.status == "failed")
        for idx, result in enumerate(results):
            if idx < self._ops_list.rowCount():
                self._ops_list.setItem(idx, 4, QtWidgets.QTableWidgetItem(result.status))
                self._ops_list.setItem(idx, 5, QtWidgets.QTableWidgetItem(self._summarize_error(result.error)))
                detail = result.operation.path or result.operation.dst or result.operation.src or ""
                self._ops_list.setItem(idx, 6, QtWidgets.QTableWidgetItem(detail))
        self._append_chat("System", f"Executed {ok} operations. Failed: {failed}.")
        self._pending_operations = []
        self._refresh_logs()

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

    def _summarize_error(self, error: Optional[str]) -> str:
        if not error:
            return ""
        message = error.replace("\r", " ").replace("\n", " ").strip()
        if len(message) > 120:
            return message[:117] + "..."
        return message

    def _apply_risk_styling(self, row: int, op) -> None:
        danger_types = {"delete", "move"}
        caution = op.type in danger_types or (op.type == "write" and op.mode == "overwrite")
        if not caution:
            return
        color = QtCore.Qt.GlobalColor.red if op.type == "delete" else QtCore.Qt.GlobalColor.darkYellow
        for col in range(self._ops_list.columnCount()):
            item = self._ops_list.item(row, col)
            if item:
                item.setForeground(color)

    def _has_dangerous_ops(self, ops) -> bool:
        for op in ops:
            if op.type in {"delete", "move"}:
                return True
            if op.type == "write" and op.mode == "overwrite":
                return True
        return False

    def _confirm_dangerous_ops(self) -> bool:
        message = (
            "Dangerous operations detected (delete/move/overwrite). "
            "Do you want to proceed?"
        )
        result = QtWidgets.QMessageBox.question(
            self,
            "Confirm Dangerous Operations",
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

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

    def _apply_style(self) -> None:
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)
        self.setStyleSheet(
            """
            QMainWindow {
              background: #f4f5f7;
            }
            QLabel#HeaderTitle {
              font-size: 16px;
              font-weight: 600;
              color: #1f2937;
            }
            QLabel#HeaderStatus {
              font-size: 11px;
              color: #6b7280;
            }
            QGroupBox {
              border: 1px solid #d6d9de;
              border-radius: 10px;
              margin-top: 10px;
              background: #ffffff;
            }
            QGroupBox::title {
              subcontrol-origin: margin;
              left: 12px;
              padding: 0 6px;
              color: #374151;
              font-weight: 600;
            }
            QTextEdit, QTableWidget {
              border: 1px solid #d1d5db;
              border-radius: 8px;
              background: #ffffff;
            }
            QHeaderView::section {
              background: #f3f4f6;
              border: none;
              padding: 6px;
              font-weight: 600;
              color: #374151;
            }
            QPushButton {
              border-radius: 8px;
              padding: 6px 14px;
              background: #e5e7eb;
            }
            QPushButton:disabled {
              color: #9ca3af;
              background: #f1f5f9;
            }
            QPushButton#PrimaryButton {
              background: #2563eb;
              color: #ffffff;
              font-weight: 600;
            }
            QPushButton#DangerButton {
              background: #ef4444;
              color: #ffffff;
            }
            QTabWidget::pane {
              border: 1px solid #d6d9de;
              border-radius: 10px;
              background: #ffffff;
            }
            QTabBar::tab {
              background: #eef2f7;
              border: 1px solid #d6d9de;
              border-bottom: none;
              border-top-left-radius: 8px;
              border-top-right-radius: 8px;
              padding: 6px 12px;
              margin-right: 4px;
            }
            QTabBar::tab:selected {
              background: #ffffff;
              font-weight: 600;
            }
            """
        )

    def _build_header(self) -> QtWidgets.QWidget:
        title = QtWidgets.QLabel("Gemini CLI GUI")
        title.setObjectName("HeaderTitle")
        subtitle = QtWidgets.QLabel("Safe workspace operations with approval flow")
        subtitle.setObjectName("HeaderStatus")
        title_col = QtWidgets.QVBoxLayout()
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        title_col.setSpacing(2)

        status = QtWidgets.QLabel("Status: Ready")
        status.setObjectName("HeaderStatus")

        header = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(title_col)
        layout.addStretch()
        layout.addWidget(status)
        header.setLayout(layout)
        return header

    def _build_beginner_tab(self, button_row: QtWidgets.QHBoxLayout) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)

        layout.addWidget(self._build_workspace_box())
        layout.addWidget(self._build_getting_started())

        chat_group = QtWidgets.QGroupBox("Chat")
        chat_layout = QtWidgets.QVBoxLayout()
        chat_layout.addWidget(self._chat)
        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)

        prompt_group = QtWidgets.QGroupBox("Prompt")
        prompt_layout = QtWidgets.QVBoxLayout()
        prompt_layout.addWidget(self._input)
        prompt_layout.addLayout(button_row)
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        container.setLayout(layout)
        return container

    def _build_advanced_tab(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)

        ops_group = QtWidgets.QGroupBox("Operations")
        ops_layout = QtWidgets.QVBoxLayout()
        ops_layout.addWidget(self._ops_status)
        ops_layout.addWidget(self._ops_list)
        ops_group.setLayout(ops_layout)
        layout.addWidget(ops_group)

        logs_group = QtWidgets.QGroupBox("Logs")
        logs_layout = QtWidgets.QVBoxLayout()
        logs_layout.addWidget(self._log_view)
        logs_layout.addWidget(self._log_refresh)
        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)

        container.setLayout(layout)
        return container

    def _build_workspace_box(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Workspace")
        self._workspace_label = QtWidgets.QLabel(str(self._workspace_root))
        self._workspace_label.setObjectName("HeaderStatus")
        select_btn = QtWidgets.QPushButton("Select Folder")
        select_btn.clicked.connect(self._on_select_workspace)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self._workspace_label)
        row.addStretch()
        row.addWidget(select_btn)
        group.setLayout(row)
        return group

    def _build_getting_started(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Getting Started")
        text = QtWidgets.QLabel(
            "1. Choose a workspace folder.\n"
            "2. Type what you want in the prompt box.\n"
            "3. Review suggested operations in the Advanced tab.\n"
            "4. Click Approve to execute."
        )
        text.setWordWrap(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(text)
        group.setLayout(layout)
        return group

    def _on_select_workspace(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not directory:
            return
        self._workspace_root = Path(directory)
        self._workspace_label.setText(directory)
        self._sandbox = WorkspaceSandbox.create(self._workspace_root)
        self._audit_log = AuditLog(self._workspace_root / "logs")
        self._executor = OperationExecutor(self._sandbox, self._audit_log)
        self._append_chat("System", f"Workspace set to: {directory}")
        self._refresh_logs()

    def _refresh_logs(self) -> None:
        logs_dir = Path.cwd() / "logs"
        gui_log = logs_dir / "gui.log"
        audit_log = logs_dir / "audit.log.jsonl"
        lines = []
        if gui_log.exists():
            lines.append("== gui.log ==")
            lines.extend(self._tail_lines(gui_log, 40))
        if audit_log.exists():
            lines.append("== audit.log.jsonl ==")
            lines.extend(self._tail_lines(audit_log, 40))
        self._log_view.setPlainText("\n".join(lines))

    @staticmethod
    def _tail_lines(path: Path, limit: int) -> list[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return content[-limit:]
        except Exception as exc:
            return [f"Failed to read {path}: {exc}"]

    def _append_chat(self, speaker: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._chat.append(f"[{timestamp}] {speaker}: {message}")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
