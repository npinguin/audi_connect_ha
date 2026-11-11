"""Administrator-only development panel and V3 WebSocket operations.

The dashboard never receives auth tokens, raw cloud dumps, or VIN-containing
diagnostic exports. Admin actions may address their own authenticated VIN.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig

from ..const import DOMAIN
from .engine import V3Engine

_PANEL = "audiconnect-v3"
_READY_KEY = "audiconnect_v3_dashboard_registered"


def _engine(hass: Any, entry_id: str) -> V3Engine:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError("Unknown Audi integration")
    runtime = getattr(entry, "runtime_data", None)
    engine = getattr(runtime, "v3", None)
    if not isinstance(engine, V3Engine):
        raise ValueError("Enable V3 in this Audi integration first")
    return engine


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "audiconnect/v3/list"})
@websocket_api.async_response
async def ws_list(hass, connection, msg):
    records = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        engine = getattr(getattr(entry, "runtime_data", None), "v3", None)
        if not isinstance(engine, V3Engine):
            continue
        records.append({
            "entry_id": entry.entry_id,
            "vehicles": [{
                "vin": car.vin,
                "name": car.name,
                "model": car.model,
                "climate_state": car.climate_state,
                "status_route": car.climate_source,
                "age_minutes": car.capture_age_minutes,
                "start_enabled": engine.control_enabled(car.vin, "start"),
                "stop_enabled": engine.control_enabled(car.vin, "stop"),
            } for car in engine.vehicles.values()],
            "poll_success": engine.last_cloud_poll_success.isoformat()
            if engine.last_cloud_poll_success else None,
            "quota": engine.transport.remaining_calls,
        })
    connection.send_result(msg["id"], {"integrations": records})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/routes",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): vol.In(("status", "start", "stop")),
})
@websocket_api.async_response
async def ws_routes(hass, connection, msg):
    try:
        engine = _engine(hass, msg["entry_id"])
        car = engine.require_vehicle(msg["vin"])
        profile = engine.profiles[car.vin.lower()]
        aspect = msg["aspect"]
        allowed = profile.registry.resolve(
            "climate", aspect, car.context
        )["available_operations"]
        rows = []
        for ident in allowed:
            op = profile.registry.operations[ident]
            result = (
                profile.read_results.get(ident, {}).get("outcome", "untested")
                if aspect == "status" else
                profile.control_results.get(ident, "untested")
            )
            rows.append({
                "id": ident, "family": op["family"],
                "method": op["method"], "path": op["path"],
                "outcome": result, "selected":
                profile.active.get(f"climate.{aspect}") == ident,
                "custom": ident in profile.custom,
            })
        connection.send_result(msg["id"], {
            "routes": rows, "disabled": f"climate.{aspect}"
            in profile.discovery.disabled,
            "history": [
                item.public() for item in profile.discovery.history
                if item.action == aspect
            ][-10:],
        })
    except (ValueError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_invalid_route", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/add_route",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("route"): dict,
})
@websocket_api.async_response
async def ws_add_route(hass, connection, msg):
    try:
        result = await _engine(hass, msg["entry_id"]).add_route(
            msg["vin"], msg["route"]
        )
        connection.send_result(msg["id"], {"operation": result})
    except (ValueError, KeyError, TypeError) as exc:
        connection.send_error(msg["id"], "v3_invalid_route", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/test",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): vol.In(("status", "start", "stop")),
    vol.Required("operation"): str, vol.Optional("parameters"): dict,
})
@websocket_api.async_response
async def ws_test(hass, connection, msg):
    try:
        engine = _engine(hass, msg["entry_id"])
        if msg["aspect"] == "status":
            result = await engine.test_status_route(msg["vin"], msg["operation"])
        else:
            result = await engine.test_action(
                msg["vin"], msg["aspect"], msg["operation"],
                params=msg.get("parameters"),
            )
        connection.send_result(msg["id"], result)
    except (ValueError, TypeError, KeyError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_test_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/review",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("sequence"): int,
    vol.Required("result"): vol.In(("worked", "failed", "uncertain")),
})
@websocket_api.async_response
async def ws_review(hass, connection, msg):
    try:
        engine = _engine(hass, msg["entry_id"])
        result = await engine.review_action(
            msg["vin"], msg["sequence"], msg["result"]
        )
        connection.send_result(msg["id"], result)
    except (ValueError, RuntimeError, TypeError) as exc:
        connection.send_error(msg["id"], "v3_review_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/select",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): vol.In(("status", "start", "stop")),
    vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_select(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).select_working(
            msg["vin"], msg["aspect"], msg["operation"]
        )
        connection.send_result(msg["id"], {"selected": msg["operation"]})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_select_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/disable",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): vol.In(("start", "stop")),
})
@websocket_api.async_response
async def ws_disable(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).disable_action(
            msg["vin"], msg["aspect"]
        )
        connection.send_result(msg["id"], {"disabled": msg["aspect"]})
    except (ValueError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_disable_failed", str(exc))


async def async_setup_dashboard(hass) -> None:
    if hass.data.get(_READY_KEY):
        return
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([
        StaticPathConfig("/audiconnect_v3", str(frontend_dir), False)
    ])
    for handler in (
        ws_list, ws_routes, ws_add_route, ws_test,
        ws_review, ws_select, ws_disable,
    ):
        websocket_api.async_register_command(hass, handler)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="audiconnect-v3-panel",
        frontend_url_path=_PANEL,
        module_url="/audiconnect_v3/panel.js?v=3.0.0b2",
        sidebar_title="Audi V3 Development",
        sidebar_icon="mdi:car-cog",
        require_admin=True,
        embed_iframe=False,
    )
    hass.data[_READY_KEY] = True


def async_remove_dashboard(hass) -> None:
    if hass.data.pop(_READY_KEY, False):
        frontend.async_remove_panel(hass, _PANEL, warn_if_unknown=False)
