import tempfile
import unittest
from pathlib import Path

from core.audit_log import AuditLog
from core.operation_executor import OperationExecutor
from core.operations_parser import Operation
from core.workspace_sandbox import WorkspaceSandbox


class OperationExecutorRealTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.sandbox = WorkspaceSandbox.create(self.root)
        self.log = AuditLog(self.root / "logs")
        self.executor = OperationExecutor(self.sandbox, self.log)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_write_read_delete(self) -> None:
        ops = [
            Operation(type="write", path="a.txt", mode="overwrite", content="hello"),
            Operation(type="read", path="a.txt"),
            Operation(type="delete", path="a.txt"),
        ]
        results = self.executor.execute(ops)
        self.assertEqual([r.status for r in results], ["ok", "ok", "ok"])
        self.assertFalse((self.root / "a.txt").exists())

    def test_move_copy_mkdir(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "src" / "file.txt").write_text("data", encoding="utf-8")

        ops = [
            Operation(type="mkdir", path="dst"),
            Operation(type="copy", src="src/file.txt", dst="dst/copy.txt"),
            Operation(type="move", src="src/file.txt", dst="dst/moved.txt"),
        ]
        results = self.executor.execute(ops)
        self.assertEqual([r.status for r in results], ["ok", "ok", "ok"])
        self.assertTrue((self.root / "dst" / "copy.txt").exists())
        self.assertTrue((self.root / "dst" / "moved.txt").exists())

    def test_zip_unzip(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs" / "a.txt").write_text("a", encoding="utf-8")
        ops = [
            Operation(type="zip", path="docs"),
        ]
        results = self.executor.execute(ops)
        self.assertEqual(results[0].status, "ok")
        archive = self.root / "docs.zip"
        self.assertTrue(archive.exists())

        ops = [
            Operation(type="unzip", path="docs.zip"),
        ]
        results = self.executor.execute(ops)
        self.assertEqual(results[0].status, "ok")
        self.assertTrue((self.root / "docs" / "a.txt").exists())


if __name__ == "__main__":
    unittest.main()
