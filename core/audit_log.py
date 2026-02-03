"""Audit logging for gemini-cli-gui."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditEntry:
    timestamp: str
    action: str
    path: Optional[str]
    status: str
    duration_ms: Optional[int]
    error: Optional[str]
    details: Dict[str, Any]


class AuditLog:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._log_path = self._root / "audit.log.jsonl"

    def record(
        self,
        action: str,
        *,
        path: Optional[str],
        status: str,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            path=path,
            status=status,
            duration_ms=duration_ms,
            error=error,
            details=details or {},
        )
        with self._log_path.open("a", encoding="utf-8") as handle:
            json.dump(asdict(entry), handle, ensure_ascii=False)
            handle.write("\n")

    @property
    def log_path(self) -> Path:
        return self._log_path
