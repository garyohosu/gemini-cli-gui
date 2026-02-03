"""Operation execution stubs with audit logging."""

from __future__ import annotations

import logging
import os
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from core.audit_log import AuditLog
from core.operations_parser import Operation
from core.workspace_sandbox import SandboxViolation, WorkspaceSandbox


@dataclass(frozen=True)
class OperationResult:
    operation: Operation
    status: str
    error: str | None


class OperationExecutor:
    def __init__(self, workspace: WorkspaceSandbox, audit_log: AuditLog) -> None:
        self._workspace = workspace
        self._audit_log = audit_log
        self._logger = logging.getLogger(__name__)

    def execute(self, operations: Iterable[Operation]) -> List[OperationResult]:
        results: List[OperationResult] = []
        for op in operations:
            start = time.monotonic()
            try:
                self._validate_operation(op)
                self._execute_operation(op)
                duration = int((time.monotonic() - start) * 1000)
                self._logger.debug("operation ok", extra={"operation": op.__dict__})
                self._audit_log.record(
                    action=op.type,
                    path=op.path or op.dst or op.src,
                    status="ok",
                    duration_ms=duration,
                    details={"operation": op.__dict__},
                )
                results.append(OperationResult(operation=op, status="ok", error=None))
            except Exception as exc:
                duration = int((time.monotonic() - start) * 1000)
                self._logger.exception("operation failed", extra={"operation": op.__dict__})
                self._audit_log.record(
                    action=op.type,
                    path=op.path or op.dst or op.src,
                    status="failed",
                    duration_ms=duration,
                    error=str(exc),
                    details={"operation": op.__dict__},
                )
                results.append(OperationResult(operation=op, status="failed", error=str(exc)))
        return results

    def _validate_operation(self, op: Operation) -> None:
        if op.path:
            self._workspace.resolve(op.path)
        if op.src:
            self._workspace.resolve(op.src)
        if op.dst:
            self._workspace.resolve(op.dst)

    def _execute_operation(self, op: Operation) -> None:
        if op.type == "read":
            _ = self._read_text(op.path)
        elif op.type == "write":
            self._write_text(op.path, op.content or "", op.mode)
        elif op.type == "move":
            self._move(op.src, op.dst)
        elif op.type == "copy":
            self._copy(op.src, op.dst)
        elif op.type == "mkdir":
            self._mkdir(op.path)
        elif op.type == "delete":
            self._delete(op.path)
        elif op.type == "zip":
            self._zip(op.path)
        elif op.type == "unzip":
            self._unzip(op.path)
        else:
            raise ValueError(f"Unsupported operation type: {op.type}")

    def _read_text(self, path: str | None) -> str:
        if not path:
            raise ValueError("read requires path")
        resolved = self._workspace.resolve(path)
        return resolved.read_text(encoding="utf-8")

    def _write_text(self, path: str | None, content: str, mode: str | None) -> None:
        if not path:
            raise ValueError("write requires path")
        if mode not in {"overwrite", "append", "create"}:
            raise ValueError(f"invalid write mode: {mode}")
        resolved = self._workspace.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if mode == "create" and resolved.exists():
            raise FileExistsError(f"file exists: {resolved}")
        if mode == "append":
            resolved.write_text(resolved.read_text(encoding="utf-8") + content, encoding="utf-8")
        else:
            resolved.write_text(content, encoding="utf-8")

    def _move(self, src: str | None, dst: str | None) -> None:
        if not src or not dst:
            raise ValueError("move requires src and dst")
        src_path = self._workspace.resolve(src)
        dst_path = self._workspace.resolve(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

    def _copy(self, src: str | None, dst: str | None) -> None:
        if not src or not dst:
            raise ValueError("copy requires src and dst")
        src_path = self._workspace.resolve(src)
        dst_path = self._workspace.resolve(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)

    def _mkdir(self, path: str | None) -> None:
        if not path:
            raise ValueError("mkdir requires path")
        resolved = self._workspace.resolve(path)
        resolved.mkdir(parents=True, exist_ok=True)

    def _delete(self, path: str | None) -> None:
        if not path:
            raise ValueError("delete requires path")
        resolved = self._workspace.resolve(path)
        if resolved.is_dir():
            shutil.rmtree(resolved)
        elif resolved.exists():
            resolved.unlink()

    def _zip(self, path: str | None) -> None:
        if not path:
            raise ValueError("zip requires path")
        resolved = self._workspace.resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(str(resolved))
        archive_path = resolved.with_suffix(resolved.suffix + ".zip") if resolved.is_file() else Path(str(resolved) + ".zip")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if resolved.is_dir():
                for root, _, files in os.walk(resolved):
                    for filename in files:
                        file_path = Path(root) / filename
                        zf.write(file_path, file_path.relative_to(resolved.parent))
            else:
                zf.write(resolved, resolved.name)

    def _unzip(self, path: str | None) -> None:
        if not path:
            raise ValueError("unzip requires path")
        resolved = self._workspace.resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(str(resolved))
        target_dir = resolved.parent / resolved.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(resolved, "r") as zf:
            zf.extractall(target_dir)


__all__ = ["OperationExecutor", "OperationResult"]
