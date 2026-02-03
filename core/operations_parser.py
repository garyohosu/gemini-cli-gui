"""Strict operations parser for gemini-cli-gui v1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


ALLOWED_TYPES = {
    "read",
    "write",
    "move",
    "copy",
    "mkdir",
    "delete",
    "zip",
    "unzip",
}

WRITE_MODES = {"overwrite", "append", "create"}


@dataclass(frozen=True)
class OperationParseError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class Operation:
    type: str
    path: Optional[str] = None
    src: Optional[str] = None
    dst: Optional[str] = None
    content: Optional[str] = None
    mode: Optional[str] = None


def parse_operations(text: str) -> List[Operation]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OperationParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise OperationParseError("Root must be a JSON object")

    if "operations" not in payload:
        raise OperationParseError("Missing 'operations' field")

    operations = payload["operations"]
    if not isinstance(operations, list):
        raise OperationParseError("'operations' must be a list")

    parsed: List[Operation] = []
    for idx, op in enumerate(operations):
        if not isinstance(op, dict):
            raise OperationParseError(f"Operation #{idx} must be an object")

        op_type = op.get("type")
        if op_type not in ALLOWED_TYPES:
            raise OperationParseError(f"Operation #{idx} has invalid type: {op_type}")

        _validate_fields(idx, op_type, op)

        parsed.append(
            Operation(
                type=op_type,
                path=op.get("path"),
                src=op.get("src"),
                dst=op.get("dst"),
                content=op.get("content"),
                mode=op.get("mode"),
            )
        )

    return parsed


def _require(op: Dict[str, Any], key: str, idx: int) -> str:
    value = op.get(key)
    if not isinstance(value, str) or not value:
        raise OperationParseError(f"Operation #{idx} missing or invalid '{key}'")
    return value


def _validate_fields(idx: int, op_type: str, op: Dict[str, Any]) -> None:
    if op_type in {"read", "write", "mkdir", "delete", "zip", "unzip"}:
        _require(op, "path", idx)

    if op_type in {"move", "copy"}:
        _require(op, "src", idx)
        _require(op, "dst", idx)

    if op_type == "write":
        _require(op, "content", idx)
        mode = op.get("mode")
        if mode is None:
            raise OperationParseError(f"Operation #{idx} missing 'mode'")
        if mode not in WRITE_MODES:
            raise OperationParseError(f"Operation #{idx} has invalid mode: {mode}")

    _reject_unknown_fields(idx, op_type, op)


def _reject_unknown_fields(idx: int, op_type: str, op: Dict[str, Any]) -> None:
    allowed = {"type"}
    if op_type in {"read", "write", "mkdir", "delete", "zip", "unzip"}:
        allowed.add("path")
    if op_type in {"move", "copy"}:
        allowed.update({"src", "dst"})
    if op_type == "write":
        allowed.update({"content", "mode"})

    unknown = set(op.keys()) - allowed
    if unknown:
        extra = ", ".join(sorted(unknown))
        raise OperationParseError(f"Operation #{idx} has unknown fields: {extra}")
