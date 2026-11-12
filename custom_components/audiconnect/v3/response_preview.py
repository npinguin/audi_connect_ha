"""Bounded per-session response preview for the admin-only V3 Workbench.

This is NOT a public diagnostics or community-data export. Never store or
publish full OEM responses, auth headers, vehicle identifiers or coordinates.
"""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE = re.compile(
    r"vin|authorization|password|access.?token|refresh.?token|bearer|spin|s.?pin|"
    r"secret|email|phone|location|latitude|longitude|position|"
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
