"""V3 normalization of historical profile/timer data from one GET batch.

Never persist profile coordinates in HA entities or diagnostics. No inferred
timezone, no fabricated defaults, and no extra cloud request.
"""
from __future__ import annotations
from typing import Any
from datetime import timedelta
from .registry import read_json_path
from .freshness import timestamp_is_fresh


def observe_derived(car, profile, payload: dict, observed_at, accepts) -> None:
    def record(ident, value, captured, job, path):
        if value is None or not accepts(car.readings.get(ident), captured):
            return
        fresh = timestamp_is_fresh(captured, observed_at)
        car.readings[ident] = {
            "value": value, "captured": captured,
            "observed": observed_at.isoformat(), "fresh": fresh,
            "path": path, "job": job, "family": "cariad",
            "status": "verified" if fresh else "readable_but_stale",
        }
        # Derived observations need no extra API route; HA setup can see them
        # directly while the original batch job remains in the polling plan.

    # Independent historical aliases use the original HA keys. Preserve
    # existing source timestamps rather than inventing new observations.
    for ident, source in (
        ("charging_type", "chargeType"), ("plug_led_color", "plugledColor"),
        ("primary_engine_type", "engineTypeFirstEngine"),
        ("secondary_engine_type", "engineTypeSecondEngine"),
        ("max_charge_current", "chargingCurrentLimitA"),
    ):
        row = car.readings.get(source)
        if row and row.get("value") is not None:
            record(ident, row["value"], row.get("captured"),
                   row.get("job"), row.get("path"))
    remaining = car.readings.get("remainingChargingTime", {})
    from .attribute_runtime import _capture_in_utc
    stamp = _capture_in_utc(remaining.get("captured"))
    minutes = remaining.get("value")
    if stamp and type(minutes) in (int, float) and 0 < minutes <= 10080:
        record("charging_complete_time", (stamp + timedelta(minutes=minutes)).isoformat(),
               remaining["captured"], "charging", remaining.get("path"))

    # Historical auxiliary-heating status is distinct from electric cabin
    # climatisation. Do not infer heating from a generic climate state.
    path = "climatisation.auxiliaryHeatingStatus.value"
    auxiliary = read_json_path(payload, path)
    if isinstance(auxiliary, dict):
        stamp = auxiliary.get("carCapturedTimestamp")
        state = auxiliary.get("climatisationState")
        if isinstance(state, str):
            state = state.strip().lower()
            active = True if state in ("heating", "on", "active") else (
                False if state in ("off", "inactive", "stopped") else None
            )
            record("preheater_active", active, stamp, "climatisation", path)
        for ident, field in (("preheater_duration", "climatisationDuration"),
                             ("preheater_remaining", "remainingClimateTime")):
            value = auxiliary.get(field)
            if type(value) is int and value >= 0:
                record(ident, value, stamp, "climatisation", path)

    # Derive native access booleans from explicit status enums, not from
    # absence of a "closed" token (unknown must never mean open/unlocked).
    path = "access.accessStatus.value"
    block = read_json_path(payload, path)
    if isinstance(block, dict):
        captured = block.get("carCapturedTimestamp")
        names = {"frontLeft": "left_front", "frontRight": "right_front",
                 "rearLeft": "left_rear", "rearRight": "right_rear"}
        opened, unlocked, windows = [], [], []
        for row in block.get("doors", []) if isinstance(block.get("doors"), list) else []:
            if not isinstance(row, dict):
                continue
            name, states = row.get("name"), row.get("status")
            if not isinstance(states, list) or "unsupported" in states:
                continue
            open_state = True if "open" in states else False if "closed" in states else None
            lock_state = True if "unlocked" in states else False if "locked" in states else None
            if name in names:
                record(names[name] + "_door_open", open_state, captured, "access", path)
                opened.append(open_state)
                unlocked.append(lock_state)
            elif name == "trunk":
                record("trunk_open", open_state, captured, "access", path)
                record("trunk_unlocked", lock_state, captured, "access", path)
                opened.append(open_state)
                unlocked.append(lock_state)
            elif name == "bonnet":
                record("hood_open", open_state, captured, "access", path)
        # Positive is conclusive even if other components are not present.
        # Negative requires complete, known evidence; no fabricated safe state.
        for key, values in (("any_door_open", opened), ("any_door_unlocked", unlocked)):
            value = True if True in values else False if len(values) >= 3 and all(x is False for x in values) else None
            record(key, value, captured, "access", path)
        if True in opened:
            record("doors_trunk_status", "Open", captured, "access", path)
        elif opened and all(x is False for x in opened):
            lock = block.get("doorLockStatus")
            if lock in ("locked", "unlocked"):
                record("doors_trunk_status", "Locked" if lock == "locked" else "Closed", captured, "access", path)
        for row in block.get("windows", []) if isinstance(block.get("windows"), list) else []:
            if not isinstance(row, dict):
                continue
            name, states = row.get("name"), row.get("status")
            if not isinstance(states, list) or "unsupported" in states:
                continue
            state = True if "open" in states else False if "closed" in states else None
            key = (names[name] + "_window_open" if name in names else
                   {"sunRoof": "sun_roof", "roofCover": "roof_cover"}.get(name))
            if key:
                record(key, state, captured, "access", path)
                windows.append(state)
        record("any_window_open", True if True in windows else
               False if len(windows) >= 4 and all(x is False for x in windows) else None,
               captured, "access", path)
    path = "vehicleLights.lightsStatus.value"
    lights = read_json_path(payload, path)
    if isinstance(lights, dict) and isinstance(lights.get("lights"), list):
        states = [x.get("status") for x in lights["lights"] if isinstance(x, dict)]
        if states and all(x in ("on", "off") for x in states):
            record("parking_light", "on" in states, lights.get("carCapturedTimestamp"),
                   "vehicleLights", path)
    oil = read_json_path(payload, "oilLevel.oilLevelStatus.value")
    if isinstance(oil, dict) and type(oil.get("value")) is bool:
        record("oil_level_binary", not oil["value"], oil.get("carCapturedTimestamp"),
               "oilLevel", "oilLevel.oilLevelStatus.value")
    # The preference block may lack a timestamp. Borrow ONLY the sibling
    # charging status clock from this response, matching the historical source.
    mode = read_json_path(payload, "charging.chargeMode.value")
    charge = read_json_path(payload, "charging.chargingStatus.value")
    if isinstance(mode, dict) and isinstance(charge, dict):
        captured = mode.get("carCapturedTimestamp") or charge.get("carCapturedTimestamp")
        for key in ("preferredChargeMode", "availableChargeModes"):
            record(key, mode.get(key), captured, "charging", "charging.chargeMode.value")
    path = "chargingProfiles.chargingProfilesStatus.value"
    block = read_json_path(payload, path)
    if isinstance(block, dict) and isinstance(block.get("profiles"), list):
        captured = block.get("carCapturedTimestamp")
        if accepts({"captured": car.charging_profiles_captured}
                   if car.charging_profiles_captured else None, captured):
            profiles = [dict(id=x["id"], name=x.get("name"),
                        targetSOC_pct=x.get("targetSOC_pct"),
                        minSOC_pct=x.get("minSOC_pct"),
                        preferredChargingTimes=[
                            {k: t.get(k) for k in ("enabled", "startTimeLocal", "endTimeLocal")}
                            for t in x.get("preferredChargingTimes", [])[:12]
                            if isinstance(t, dict)
                        ] if isinstance(x.get("preferredChargingTimes"), list) else [])
                        for x in block["profiles"][:30] if isinstance(x, dict)
                        and type(x.get("id")) is int]
            car.charging_profiles = profiles
            car.charging_profiles_captured = captured
            active_id = block.get("vehiclePositionedInProfileID")
            car.active_charging_profile_id = active_id if type(active_id) is int else None
            active = next((x for x in profiles if x["id"] == car.active_charging_profile_id), None)
            keys = {"active_charging_profile_target_soc": "targetSOC_pct",
                    "active_charging_profile_name": "name",
                    "active_charging_profile_min_soc": "minSOC_pct"}
            for ident, key in keys.items():
                car.readings.pop(ident, None)
                if active:
                    record(ident, active.get(key), captured, "chargingProfiles", path)
            for ident in ("preferred_charging_time_start", "preferred_charging_time_end"):
                car.readings.pop(ident, None)
            if active and active["preferredChargingTimes"]:
                times = active["preferredChargingTimes"]
                window = next((x for x in times if x.get("enabled") is True), times[0])
                record("preferred_charging_time_start", window.get("startTimeLocal"), captured, "chargingProfiles", path)
                record("preferred_charging_time_end", window.get("endTimeLocal"), captured, "chargingProfiles", path)

    for job, count in (("chargingTimers", "charging_timer_enabled_count"),
                       ("climatisationTimers", "climatisation_timer_enabled_count")):
        path = f"{job}.{job}Status.value"
        block = read_json_path(payload, path)
        if not isinstance(block, dict) or not isinstance(block.get("timers"), list):
            continue
        captured = block.get("carCapturedTimestamp")
        entries = [t for t in block["timers"][:30] if isinstance(t, dict)]
        record(count, sum(t.get("enabled") is True for t in entries), captured, job, path)
        if job == "climatisationTimers":
            starts = sorted(v for t in entries if t.get("enabled") is True
                            and isinstance(t.get("singleTimer"), dict)
                            and isinstance(v := t["singleTimer"].get("startDateTimeLocal"), str))
            if starts:
                record("next_climatisation_timer_local", starts[0], captured, job, path)
            elif accepts(car.readings.get("next_climatisation_timer_local"), captured):
                car.readings.pop("next_climatisation_timer_local", None)
