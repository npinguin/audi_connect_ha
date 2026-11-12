"""Bounded per-session response preview for the admin-only V3 Workbench.

This is NOT a public diagnostics or community-data export. Never store or
publish full OEM responses, auth headers, vehicle identifiers or coordinates.
"""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE = re.compile(
    r"vin|authorization|password|access.?token|refresh.?token|bearer|spin|s.?pin|"
    r"secret|token|credential|challenge|email|phone|location|latitude|longitude|position|account.?id|user.?id|"
    r"coordinates|street|address|request.?id|session.?id|user.?prompt.?proof|secured.?activation.?data|^lat$|^lon$|^lng$",
    re.IGNORECASE,
)
_VIN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.IGNORECASE)
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def safe_response_preview(
    payload: Any, *, vehicle_vin: str = "", depth_limit: int = 5
) -> Any:
    """Provide just a small recognizable redacted JSON shape and values."""

    def visit(value: Any, depth: int) -> Any:
        if depth >= depth_limit:
            return "[nested content omitted]"
        if isinstance(value, dict):
            clean = {}
            for index, (key, child) in enumerate(value.items()):
                if index >= 25:
                    clean["[more fields omitted]"] = True
                    break
                name = str(key)[:80]
                if _VIN.search(name) or _EMAIL.search(name) or (vehicle_vin and vehicle_vin.lower() in name.lower()):
                    continue
                clean[name] = (
                    "[redacted]" if _SENSITIVE.search(name)
                    else visit(child, depth + 1)
                )
            return clean
        if isinstance(value, list):
            result = [visit(item, depth + 1) for item in value[:8]]
            if len(value) > 8:
                result.append("[more items omitted]")
            return result
        if isinstance(value, str):
            if vehicle_vin:
                value = re.sub(re.escape(vehicle_vin), "[redacted]", value, flags=re.I)
            return _EMAIL.sub("[redacted]", _VIN.sub("[redacted]", value[:240]))
        if value is None or type(value) in (bool, int, float):
            return value
        return "[unsupported value type]"

    return visit(payload, 0)

MAX_SCHEMA_FIELDS = 128
MAX_SCHEMA_CHARS = 16000
_SCHEMA_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_SCHEMA_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\])*(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\])*)*$")
_SCHEMA_TYPES = frozenset(("object", "array", "boolean", "integer", "number", "string", "null"))


def safe_schema_fields(payload: Any, *, vehicle_vin: str = "") -> list[dict[str, str]]:
    """Bounded structural inventory of GET fields; no values or sensitive keys."""
    from collections import deque
    from itertools import islice
    import json

    queue = deque([(payload, "", 0)])
    rows: dict[tuple[str, str], dict[str, str]] = {}
    budget = 640
    while queue and budget and len(rows) < MAX_SCHEMA_FIELDS:
        value, path, depth = queue.popleft()
        budget -= 1
        if depth > 12 or len(path) > 220:
            continue
        kind = {dict: "object", list: "array", bool: "boolean", int: "integer",
                float: "number", str: "string", type(None): "null"}.get(type(value))
        if kind is None:
            continue
        if path:
            quality = "observed"
            if value is None:
                quality = "null"
            elif type(value) is str and value.strip().lower() in (
                "", "invalid", "unknown", "unsupported", "unavailable", "error"
            ):
                quality = "vendor_sentinel"
            elif type(value) in (int, float) and value < 0 and (
                "remaining" in path.lower() or "duration" in path.lower()
            ):
                quality = "negative_duration_candidate"
            # Preserve a detected issue even if another array member is valid.
            key = (path, kind)
            if key not in rows or quality != "observed":
                rows[key] = {"path": path, "type": kind, "quality": quality}
        if isinstance(value, dict):
            for key, child in islice(value.items(), 40):
                if (not isinstance(key, str) or not _SCHEMA_KEY.fullmatch(key)
                        or _SENSITIVE.search(key) or _VIN.search(key)
                        or (vehicle_vin and vehicle_vin.lower() in key.lower())):
                    continue
                queue.append((child, f"{path}.{key}" if path else key, depth + 1))
        elif isinstance(value, list) and path:
            for child in value[:4]:
                queue.append((child, path + "[]", depth + 1))
    result = list(rows.values())
    while result and len(json.dumps(result, ensure_ascii=True)) > MAX_SCHEMA_CHARS:
        result.pop()
    return result


def validate_schema_fields(rows: Any) -> None:
    """Validate persisted structural evidence without trusting arbitrary paths."""
    import json

    if not isinstance(rows, list) or len(rows) > MAX_SCHEMA_FIELDS:
        raise ValueError("Invalid response schema inventory")
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"path", "type", "quality"}
                or not isinstance(row["path"], str) or len(row["path"]) > 220
                or not _SCHEMA_PATH.fullmatch(row["path"]) or _SENSITIVE.search(row["path"])
                or _VIN.search(row["path"]) or not isinstance(row["type"], str)
                or row["type"] not in _SCHEMA_TYPES
                or row["quality"] not in ("observed", "null", "vendor_sentinel",
                                          "negative_duration_candidate")):
            raise ValueError("Invalid response schema field")
    if len(json.dumps(rows, ensure_ascii=True)) > MAX_SCHEMA_CHARS:
        raise ValueError("Excessive response schema inventory")
