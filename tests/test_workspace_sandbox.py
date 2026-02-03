import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.workspace_sandbox import WorkspaceSandbox, SandboxViolation


class WorkspaceSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "dir").mkdir()
        self.sandbox = WorkspaceSandbox.create(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_allows_relative_path(self) -> None:
        resolved = self.sandbox.resolve("dir/file.txt")
        self.assertTrue(str(resolved).startswith(str(self.root)))

    def test_allows_absolute_path_inside_root(self) -> None:
        target = self.root / "dir" / "file2.txt"
        resolved = self.sandbox.resolve(str(target))
        self.assertEqual(resolved, target)

    def test_blocks_traversal(self) -> None:
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("..\\outside.txt")

    def test_blocks_unc(self) -> None:
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("\\\\server\\share\\file.txt")

    def test_blocks_long_path(self) -> None:
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("\\\\?\\C:\\temp\\file.txt")

    def test_blocks_other_drive(self) -> None:
        root_drive = Path(self.root).drive.upper()
        other_drive = "Z:" if root_drive != "Z:" else "Y:"
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(other_drive + "\\tmp\\file.txt")

    def test_blocks_symlink_escape(self) -> None:
        outside = self.root.parent / "outside"
        outside.mkdir(exist_ok=True)
        (outside / "secret.txt").write_text("secret", encoding="utf-8")

        link = self.root / "link_outside"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink not supported: {exc}")

        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(str(link / "secret.txt"))

    def test_blocks_junction_escape(self) -> None:
        if os.name != "nt":
            self.skipTest("junction test is Windows-only")

        outside = self.root.parent / "outside2"
        outside.mkdir(exist_ok=True)
        (outside / "secret.txt").write_text("secret", encoding="utf-8")

        junction = self.root / "junction_outside"
        cmd = f'mklink /J "{junction}" "{outside}"'
        result = subprocess.run(
            ["cmd", "/c", cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.skipTest(f"junction not created: {result.stderr.strip()}")

        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(str(junction / "secret.txt"))


if __name__ == "__main__":
    unittest.main()
