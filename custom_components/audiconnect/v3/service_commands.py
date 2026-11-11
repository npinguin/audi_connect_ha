"""Independent V3 implementation of the historical Home Assistant action contract.

The bootstrap resolves which runtime owns a VIN. This module contains V3's
complete action-name translation and fail-closed command execution. Nothing
imports or invokes V2 vehicle business code. Command route/payload resolution
belongs to V3Engine; this module does not build OEM HTTP requests.
"""
from __future__ import annotations

from typing import Any
from homeassistant.exceptions import HomeAssistantError

# Stable HA service action vocabulary, not a second API mapping layer.
# API method, URL and body remain owned by V3's declarative route catalog.
_V2_ACTIONS: dict[str, tuple[str, str]] = {
    "lock": ("access", "lock"),
    "unlock": ("access", "unlock"),
    "start_climatisation": ("climate", "start"),
    "stop_climatisation": ("climate", "stop"),
    "start_charger": ("charging", "start"),
    "stop_charger": ("charging", "stop"),
    "start_window_heating": ("climate", "window_heating_start"),
    "stop_window_heating": ("climate", "window_heating_stop"),
}


async def execute(
    engine: Any, vin: str, action: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Execute one reviewed V3 command via the same external V2 service ID.

    Never discard unknown service parameters or fall back to V2 actions.
    """
    values = data or {}
    if action == "start_climatisation":
        unsupported = set(values) - {"device_id", "action"}
        if unsupported:
            raise HomeAssistantError(
                "V3 parameterized climate start is not yet implemented: "
                + ", ".join(sorted(unsupported))
            )
    mapped = _V2_ACTIONS.get(action)
    if mapped is None:
        raise HomeAssistantError(
            f"Audi action '{action}' is not yet V3-verified; "
            "switch to V2 to use the existing action safely"
        )
    capability, aspect = mapped
    try:
        await engine.send_control(vin, aspect, capability)
    except (RuntimeError, ValueError) as exc:
        raise HomeAssistantError(f"Audi {action}: {exc}") from exc
