import json
import tempfile
import unittest
from pathlib import Path

from core.audit_log import AuditLog
from core.operation_executor import OperationExecutor
from core.operations_parser import Operation
from core.workspace_sandbox import WorkspaceSandbox


class AuditLogTests(unittest.TestCase):
    def test_audit_log_records_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp))
            log.record(
                action="read",
                path="docs/readme.txt",
                status="ok",
                duration_ms=5,
                details={"note": "test"},
            )
            entries = log.log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(entries), 1)
            payload = json.loads(entries[0])
            self.assertEqual(payload["action"], "read")
            self.assertEqual(payload["status"], "ok")


class OperationExecutorTests(unittest.TestCase):
    def test_executor_records_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "readme.txt").write_text("hello", encoding="utf-8")
            sandbox = WorkspaceSandbox.create(root)
            log = AuditLog(root / "logs")
            executor = OperationExecutor(sandbox, log)

            ops = [Operation(type="read", path="docs/readme.txt")]
            results = executor.execute(ops)
            self.assertEqual(results[0].status, "ok")

            entries = log.log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(entries), 1)
            payload = json.loads(entries[0])
            self.assertEqual(payload["action"], "read")
            self.assertEqual(payload["status"], "ok")

    def test_executor_records_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox = WorkspaceSandbox.create(root)
            log = AuditLog(root / "logs")
            executor = OperationExecutor(sandbox, log)

            ops = [Operation(type="read", path="..\\escape.txt")]
            results = executor.execute(ops)
            self.assertEqual(results[0].status, "failed")

            entries = log.log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(entries), 1)
            payload = json.loads(entries[0])
            self.assertEqual(payload["status"], "failed")


if __name__ == "__main__":
    unittest.main()
