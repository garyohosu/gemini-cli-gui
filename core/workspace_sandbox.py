"""Workspace path safety checks for gemini-cli-gui.

The sandbox enforces that all operations remain within a single workspace root.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", None)


@dataclass(frozen=True)
class SandboxViolation(Exception):
    reason: str
    path: str

    def __str__(self) -> str:
        return f"{self.reason}: {self.path}"


@dataclass(frozen=True)
class WorkspaceSandbox:
    root: Path

    @staticmethod
    def create(root: str | Path) -> "WorkspaceSandbox":
        root_path = Path(root).resolve(strict=True)
        if not root_path.is_dir():
            raise SandboxViolation("Workspace root is not a directory", str(root_path))
        return WorkspaceSandbox(root=root_path)

    def resolve(self, candidate: str | Path) -> Path:
        candidate_str = str(candidate)

        if self._is_unc_path(candidate_str) or self._is_long_path(candidate_str):
            raise SandboxViolation("UNC/long paths are not allowed", candidate_str)

        path = Path(candidate)
        if path.is_absolute():
            if self._drive(path) != self._drive(self.root):
                raise SandboxViolation("Cross-drive absolute paths are not allowed", candidate_str)
            target = path
        else:
            target = self.root / path

        normalized = Path(os.path.normpath(str(target)))
        normalized = normalized.resolve(strict=False)

        if not self._is_within_root(normalized):
            raise SandboxViolation("Path escapes workspace", str(normalized))

        self._reject_reparse_points(normalized)
        return normalized

    def _reject_reparse_points(self, target: Path) -> None:
        if FILE_ATTRIBUTE_REPARSE_POINT is None:
            return

        for current in self._existing_parents(target):
            try:
                st = current.stat()
            except OSError:
                continue

            if getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
                raise SandboxViolation("Reparse point is not allowed", str(current))

    def _existing_parents(self, target: Path) -> Iterable[Path]:
        current = target
        while True:
            if current.exists():
                yield current
            if current == self.root:
                break
            if current.parent == current:
                break
            current = current.parent

    def _is_within_root(self, target: Path) -> bool:
        try:
            root_norm = os.path.normcase(str(self.root))
            target_norm = os.path.normcase(str(target))
            common = os.path.commonpath([root_norm, target_norm])
            return common == root_norm
        except ValueError:
            return False

    @staticmethod
    def _drive(path: Path) -> str:
        return path.drive.upper()

    @staticmethod
    def _is_unc_path(path_str: str) -> bool:
        return path_str.startswith("\\\\")

    @staticmethod
    def _is_long_path(path_str: str) -> bool:
        return path_str.startswith("\\\\?\\")
