"""Basic verification for WorkspaceSandbox rules."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.workspace_sandbox import WorkspaceSandbox, SandboxViolation


def expect_ok(sandbox: WorkspaceSandbox, path: str) -> str:
    resolved = sandbox.resolve(path)
    return str(resolved)


def expect_fail(sandbox: WorkspaceSandbox, path: str) -> str:
    try:
        sandbox.resolve(path)
    except SandboxViolation as exc:
        return str(exc)
    raise AssertionError(f"Expected failure for: {path}")


def main() -> None:
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "dir").mkdir()
        sandbox = WorkspaceSandbox.create(root)

        results["ok_relative"] = expect_ok(sandbox, "dir/file.txt")
        results["ok_absolute"] = expect_ok(sandbox, str(root / "dir" / "file2.txt"))
        results["fail_traversal"] = expect_fail(sandbox, "..\\outside.txt")
        results["fail_unc"] = expect_fail(sandbox, "\\\\server\\share\\file.txt")
        results["fail_long_path"] = expect_fail(sandbox, "\\\\?\\C:\\temp\\file.txt")

        root_drive = Path(root).drive
        other_drive = "Z:" if root_drive.upper() != "Z:" else "Y:"
        results["fail_other_drive"] = expect_fail(sandbox, other_drive + "\\tmp\\file.txt")

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
