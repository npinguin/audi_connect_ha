"""Conservative physical state readback for supported command semantics.

No new mutation or extra per-command request. An observed expected state
is separate from backend execution proof; unsupported transient commands
remain backend-only or require manual review.
"""
from __future__ import annotations

from datetime import UTC, datetime

from .attribute_runtime import _capture_in_utc


def configure_readback(record, params):
    values = params or {}
    lookup = {
        ("climate", "start"): ("climate", ["heating", "cooling", "ventilation", "on", "active"]),
        ("climate", "start_with_settings"): ("climate", ["heating", "cooling", "ventilation", "on", "active"]),
        ("climate", "stop"): ("climate", ["off", "stopped", "inactive"]),
        ("charging", "start"): ("chargingState", ["charging"]),
        ("charging", "stop"): ("chargingState", ["off", "stopped", "notcharging", "not_charging"]),
        ("access", "lock"): ("doorLockStatus", ["locked"]),
        ("access", "unlock"): ("doorLockStatus", ["unlocked"]),
    }
    match = lookup.get((record.capability, record.action))
    if (record.capability, record.action) == ("charging", "set_target_soc"):
        value = values.get("value")
        if type(value) is int and value in range(20, 101, 5):
            match = ("targetstateOfCharge", [value])
    if (record.capability, record.action) == ("charging", "set_charge_mode"):
        value = values.get("value")
        if value in ("manual", "timer"):
            match = ("preferredChargeMode", [value])
    if match:
        record.readback_attribute, record.readback_values = match


def reconcile_readback(record, car, now=None) -> bool:
    if record.state not in ("accepted_unconfirmed", "backend_completed", "uncertain"):
        return False
    if not record.readback_attribute or not record.readback_values:
        return False
    if record.readback_attribute == "climate":
        value, captured = car.climate_state, car.climate_captured
    else:
        row = car.readings.get(record.readback_attribute) or {}
        value, captured = row.get("value"), _capture_in_utc(row.get("captured"))
    now = now or datetime.now(UTC)
    if captured is None or captured.timestamp() <= record.started_at:
        return False
    age = (now - captured).total_seconds()
    if not -300 <= age <= 3600:
        return False
    if isinstance(value, str):
        value = value.strip().lower()
    if type(value) is bool or value not in record.readback_values:
        return False
    record.state = "verified"
    return True
