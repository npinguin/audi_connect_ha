"""Typed, bounded functional details from reviewed selective-status schemas.

This is a read-only projection of OEM data, not a new capability or control
authorization source. No unbounded raw dictionaries, geographic data or secrets.
"""
from __future__ import annotations

import re
from datetime import datetime
from .registry import read_json_path

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
_CLOCK = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?$")


def _token(value):
    return value if isinstance(value, str) and _TOKEN.fullmatch(value) else None


def _id(value):
    return value if type(value) is int and 0 <= value <= 1000000 else _token(value)


def _local_datetime(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    return value if stamp.tzinfo is None and "T" in value else None


def _clock(value):
    return value if isinstance(value, str) and _CLOCK.fullmatch(value) else None


def _boolean(value):
    return value if type(value) is bool else None


def _tokens(values, limit=32):
    if not isinstance(values, list):
        return None
    result = [_token(value) for value in values[:limit]]
    return [value for value in result if value is not None]


def _compact(values):
    return {key: value for key, value in values.items() if value is not None}


def _timer(row):
    if not isinstance(row, dict):
        return None
    single = row.get("singleTimer")
    recurring = row.get("recurringTimer")
    result = _compact({"id": _id(row.get("id")), "enabled": _boolean(row.get("enabled")),
                       "climatisation": _boolean(row.get("climatisation"))})
    if isinstance(single, dict):
        local = _local_datetime(single.get("startDateTimeLocal"))
        if local is not None:
            result["start_datetime_local"] = local
    if isinstance(recurring, dict):
        days = recurring.get("repetitionDays")
        if isinstance(days, list):
            days = [d for d in days[:7] if type(d) is int and 0 <= d <= 7 or _token(d) is not None]
        else:
            days = None
        result.update(_compact({"departure_time_local": _clock(recurring.get("departureTimeLocal")),
                                "repetition_days": days}))
    return result or None


def _component(row):
    if not isinstance(row, dict) or (name := _token(row.get("name"))) is None:
        return None
    status = row.get("status")
    if isinstance(status, list):
        status = _tokens(status)
    else:
        status = _token(status)
    return _compact({"name": name, "status": status})


def _window(row):
    if not isinstance(row, dict):
        return None
    location = row.get("windowLocation")
    if location not in ("front", "rear"):
        return None
    return _compact({"location": location, "state": _token(row.get("windowHeatingState"))})


def _service(row):
    if not isinstance(row, dict) or (ident := _token(row.get("id"))) is None:
        return None
    expiration = row.get("expirationDate")
    if isinstance(expiration, str) and len(expiration) <= 40:
        try:
            datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        except ValueError:
            expiration = None
    else:
        expiration = None
    status = row.get("status")
    return _compact({"id": ident, "expiration_date": expiration,
                     "user_disabling_allowed": _boolean(row.get("userDisablingAllowed")),
                     "status": _tokens(status) if isinstance(status, list) else _token(status)})


def _array(rows, normalizer, limit):
    if not isinstance(rows, list):
        return None
    values = [normalizer(row) for row in rows[:limit]]
    return {"items": [row for row in values if row is not None],
            "received_count": len(rows),
            "normalized_count": sum(row is not None for row in values),
            "truncated": len(rows) > limit,
            "all_items_recognized": len(rows) <= limit and all(row is not None for row in values)}


def observe_structured(vehicle, payload, observed_at, accepts):
    """Keep capture-aware structured readings alongside the native scalars."""
    def put(key, value, captured, path):
        if value is not None and accepts(vehicle.readings.get(key), captured):
            vehicle.readings[key] = {"value": value, "captured": captured,
                "observed": observed_at.isoformat(), "path": path, "family": "cariad"}

    for key, path, field, normalizer, limit in (
        ("charging_timers_detail", "chargingTimers.chargingTimersStatus.value", "timers", _timer, 30),
        ("climate_timers_detail", "climatisationTimers.climatisationTimersStatus.value", "timers", _timer, 30),
        ("ventilation_timers_detail", "climatisationTimers.activeVentilationTimersStatus.value", "timers", _timer, 30),
        ("door_detail", "access.accessStatus.value", "doors", _component, 30),
        ("window_detail", "access.accessStatus.value", "windows", _component, 30),
        ("light_detail", "vehicleLights.lightsStatus.value", "lights", _component, 30),
        ("window_heating_detail", "climatisation.windowHeatingStatus.value", "windowHeatingStatus", _window, 12),
    ):
        block = read_json_path(payload, path)
        if isinstance(block, dict) and field in block:
            put(key, _array(block.get(field), normalizer, limit), block.get("carCapturedTimestamp"), path)
    block = read_json_path(payload, "access.accessStatus.value")
    if isinstance(block, dict):
        put("access_overall_detail", _token(block.get("overallStatus")),
            block.get("carCapturedTimestamp"), "access.accessStatus.value.overallStatus")
    services = read_json_path(payload, "userCapabilities.capabilitiesStatus.value")
    if isinstance(services, list):
        put("connected_services_detail", _array(services, _service, 200), None,
            "userCapabilities.capabilitiesStatus.value")


def details_for(vehicle, *keys):
    """Expose normalized data and its own provenance, never an invented timestamp."""
    result = {}
    for key in keys:
        row = vehicle.readings.get(key)
        if row is not None:
            result[key.removesuffix("_detail")] = {
                "data": row.get("value"), "vehicle_captured": row.get("captured"),
                "cloud_observed": row.get("observed"), "source": row.get("path"),
            }
    return result
