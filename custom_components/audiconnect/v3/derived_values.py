"""V3 normalization of historical profile/timer data from one GET batch.

Never persist profile coordinates in HA entities or diagnostics. No inferred
timezone, no fabricated defaults, and no extra cloud request.
"""
from __future__ import annotations
from typing import Any
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
