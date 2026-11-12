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
_HANDLERS_KEY = "audiconnect_v3_dashboard_commands_registered"


def _engine(hass: Any, entry_id: str) -> V3Engine:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError("Unknown Audi integration")
    if (
        entry.options.get("runtime_version", "v2") != "v3_climate"
        or not entry.options.get("v3_development_workbench", False)
    ):
        raise ValueError("V3 Development Workbench is not enabled")
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
        if (
            not isinstance(engine, V3Engine)
            or entry.options.get("runtime_version", "v2") != "v3_climate"
            or not entry.options.get("v3_development_workbench", False)
        ):
            continue
        records.append({
            "entry_id": entry.entry_id,
            "vehicles": [{
                "vin": car.vin,
                "name": car.name,
                "model": car.model,
                "api_family": "mbb" if car.context.auth == "legacy" else "cariad",
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
    vol.Required("type"): "audiconnect/v3/status",
    vol.Required("entry_id"): str,
    vol.Required("vin"): str,
})
@websocket_api.async_response
async def ws_status(hass, connection, msg):
    try:
        from .capability_status import build_status_report
        engine = _engine(hass, msg["entry_id"])
        vehicle = engine.require_vehicle(msg["vin"])
        profile = engine.profiles[vehicle.vin.lower()]
        report = build_status_report(vehicle, profile)
        report["normal_command"] = profile.last_command.snapshot() if profile.last_command else None
        engine.commands.refresh_bindings()
        report["fast_bindings"] = profile.fast_bindings
        connection.send_result(msg["id"], report)
    except (ValueError, KeyError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_status_failed", str(exc))


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
            "routes": rows,
            "draft_candidate": profile.draft_selected.get(f"climate.{aspect}"),
            "disabled": f"climate.{aspect}"
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
    vol.Required("aspect"): str,
    vol.Optional("capability", default="climate"): str,
    vol.Required("operation"): str, vol.Optional("parameters"): dict,
    vol.Optional("approval"): vol.In(("non_spin", "spin")),
})
@websocket_api.async_response
async def ws_test(hass, connection, msg):
    try:
        engine = _engine(hass, msg["entry_id"])
        if msg["aspect"] == "status":
            result = await engine.test_status_route(
                msg["vin"], msg["operation"], params=msg.get("parameters"),
                capability=msg["capability"],
            )
        else:
            result = await engine.approved_control_discovery(
                msg["vin"], msg["aspect"], msg["operation"],
                params=msg.get("parameters"), approval=msg.get("approval"),
                capability=msg["capability"],
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
    vol.Required("type"): "audiconnect/v3/review_normal_command",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("command_id"): str,
})
@websocket_api.async_response
async def ws_review_normal_command(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).review_normal_command(
            msg["vin"], msg["command_id"]
        )
        connection.send_result(msg["id"], {"reviewed": True})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_review_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/select",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): str,
    vol.Optional("capability", default="climate"): str,
    vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_select(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).select_working(
            msg["vin"], msg["aspect"], msg["operation"], capability=msg["capability"]
        )
        connection.send_result(msg["id"], {"selected": msg["operation"]})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_select_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/save_candidate",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): str,
    vol.Optional("capability", default="climate"): str,
    vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_save_candidate(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).save_candidate(
            msg["vin"], msg["aspect"], msg["operation"], capability=msg["capability"]
        )
        connection.send_result(msg["id"], {
            "saved": msg["operation"], "activated": False,
        })
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_save_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/disable",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("aspect"): str,
    vol.Optional("capability", default="climate"): str,
})
@websocket_api.async_response
async def ws_disable(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).disable_action(
            msg["vin"], msg["aspect"], capability=msg["capability"]
        )
        connection.send_result(msg["id"], {"disabled": msg["aspect"]})
    except (ValueError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_disable_failed", str(exc))



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_routes",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("attribute"): str,
})
@websocket_api.async_response
async def ws_attribute_routes(hass, connection, msg):
    try:
        result = _engine(hass, msg["entry_id"]).attribute_routes_for(
            msg["vin"], msg["attribute"]
        )
        connection.send_result(msg["id"], result)
    except (ValueError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_attribute_routes_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_add",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("definition"): dict,
})
@websocket_api.async_response
async def ws_attribute_add(hass, connection, msg):
    try:
        ident = await _engine(hass, msg["entry_id"]).add_attribute_route(
            msg["vin"], msg["definition"]
        )
        connection.send_result(msg["id"], {"saved": ident, "activated": False})
    except (ValueError, KeyError, TypeError) as exc:
        connection.send_error(msg["id"], "v3_attribute_add_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_test",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("attribute"): str, vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_attribute_test(hass, connection, msg):
    try:
        result = await _engine(hass, msg["entry_id"]).test_attribute_route(
            msg["vin"], msg["attribute"], msg["operation"]
        )
        connection.send_result(msg["id"], result)
    except (ValueError, RuntimeError, KeyError, TimeoutError, OSError) as exc:
        connection.send_error(msg["id"], "v3_attribute_test_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_save",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("attribute"): str, vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_attribute_save(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).save_attribute_candidate(
            msg["vin"], msg["attribute"], msg["operation"]
        )
        connection.send_result(msg["id"], {"saved": msg["operation"], "activated": False})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_attribute_save_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_activate",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("attribute"): str, vol.Required("operation"): str,
})
@websocket_api.async_response
async def ws_attribute_activate(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).activate_attribute_route(
            msg["vin"], msg["attribute"], msg["operation"]
        )
        connection.send_result(msg["id"], {"active": msg["operation"]})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_attribute_activation_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/attribute_disable",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("attribute"): str,
})
@websocket_api.async_response
async def ws_attribute_disable(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).disable_attribute_route(
            msg["vin"], msg["attribute"]
        )
        connection.send_result(msg["id"], {"disabled": msg["attribute"]})
    except (ValueError, RuntimeError, KeyError) as exc:
        connection.send_error(msg["id"], "v3_attribute_disable_failed", str(exc))



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/control_routes",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("capability"): str, vol.Required("action"): str,
})
@websocket_api.async_response
async def ws_control_routes(hass, connection, msg):
    try:
        value = _engine(hass, msg["entry_id"]).control_routes_for(
            msg["vin"], msg["capability"], msg["action"]
        )
        connection.send_result(msg["id"], value)
    except (ValueError, KeyError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_control_routes_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/control_test",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("capability"): str, vol.Required("action"): str,
    vol.Required("operation"): str,
    vol.Required("approval"): vol.In(("non_spin", "spin")),
    vol.Optional("parameters"): dict,
})
@websocket_api.async_response
async def ws_control_test(hass, connection, msg):
    try:
        value = await _engine(hass, msg["entry_id"]).approved_control_discovery(
            msg["vin"], msg["action"], msg["operation"],
            capability=msg["capability"], approval=msg["approval"],
            params=msg.get("parameters"),
        )
        connection.send_result(msg["id"], value)
    except (ValueError, KeyError, RuntimeError, TypeError) as exc:
        connection.send_error(msg["id"], "v3_control_test_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/control_disable",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("capability"): str, vol.Required("action"): str,
})
@websocket_api.async_response
async def ws_control_disable(hass, connection, msg):
    try:
        await _engine(hass, msg["entry_id"]).disable_control(
            msg["vin"], msg["capability"], msg["action"]
        )
        connection.send_result(msg["id"], {"disabled": True})
    except (ValueError, KeyError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_control_disable_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/api_results",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Optional("family", default="all"): vol.In(("all", "cariad", "mbb", "graphql")),
})
@websocket_api.async_response
async def ws_api_results(hass, connection, msg):
    try:
        engine = _engine(hass, msg["entry_id"])
        connection.send_result(msg["id"], {
            "records": engine.api_results_for(msg["vin"], msg.get("family", "all"))
        })
    except (ValueError, KeyError, RuntimeError) as exc:
        connection.send_error(msg["id"], "v3_api_results_failed", str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "audiconnect/v3/test_family_reads",
    vol.Required("entry_id"): str, vol.Required("vin"): str,
    vol.Required("family"): vol.In(("cariad", "mbb")),
})
@websocket_api.async_response
async def ws_test_family_reads(hass, connection, msg):
    try:
        result = await _engine(hass, msg["entry_id"]).test_family_reads(
            msg["vin"], msg["family"]
        )
        connection.send_result(msg["id"], result)
    except (ValueError, KeyError, RuntimeError, OSError, TimeoutError) as exc:
        connection.send_error(msg["id"], "v3_family_read_test_failed", str(exc))


async def async_setup_dashboard(hass) -> None:
    if hass.data.get(_READY_KEY):
        return
    # HA websocket commands and static paths live for the HA process.
    # Removing/readding the optional sidebar must not register duplicates.
    if not hass.data.get(_HANDLERS_KEY):
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths([
            StaticPathConfig("/audiconnect_v3", str(frontend_dir), False)
        ])
        for handler in (
            ws_list, ws_status, ws_routes, ws_add_route, ws_test,
            ws_review, ws_review_normal_command, ws_select, ws_save_candidate, ws_disable,
            ws_attribute_routes, ws_attribute_add, ws_attribute_test,
            ws_attribute_save, ws_attribute_activate, ws_attribute_disable,
            ws_control_routes, ws_control_test, ws_control_disable, ws_api_results, ws_test_family_reads,
        ):
            websocket_api.async_register_command(hass, handler)
        hass.data[_HANDLERS_KEY] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="audiconnect-v3-panel",
        frontend_url_path=_PANEL,
        module_url="/audiconnect_v3/panel.js?v=3.0.0b8-discovery1",
        sidebar_title="Audi V3 Development",
        sidebar_icon="mdi:car-cog",
        require_admin=True,
        embed_iframe=False,
    )
    hass.data[_READY_KEY] = True


def async_remove_dashboard(hass) -> None:
    if hass.data.pop(_READY_KEY, False):
        frontend.async_remove_panel(hass, _PANEL, warn_if_unknown=False)
