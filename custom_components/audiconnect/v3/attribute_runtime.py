"""V3 read-only attribute recovery from one shared CARIAD selective-status batch.

No V2 runtime imports, no automatic vehicle commands or position requests.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from .freshness import timestamp_is_fresh
from .historical_catalog import ATTRIBUTES, V2_JOBS, advertised_capabilities, extract_attributes


def planned_jobs(vehicle: Any, profile: Any) -> tuple[str, ...]:
    if not getattr(vehicle, "v2_initial_discovery_completed", False):
        return V2_JOBS
    active = {ATTRIBUTES[name]["job"] for name in profile.attribute_routes
              if name in ATTRIBUTES and ATTRIBUTES[name]["job"]}
    active.update(("climatisation", "userCapabilities"))
    return tuple(job for job in V2_JOBS if job in active)


def observe_read_only(vehicle: Any, profile: Any, payload: Any, observed_at: datetime) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {"mapped": 0, "fresh": 0}
    reported, impaired = advertised_capabilities(payload)
    if reported:
        vehicle.advertised_capabilities = reported
        vehicle.impaired_capabilities = impaired
    mapped = fresh_count = 0
    for row in extract_attributes(payload):
        ident, value = row["id"], row["value"]
        if isinstance(value, str) and value.strip().lower() in (
            "unknown", "invalid", "unsupported", "unavailable", "error", ""
        ):
            continue
        if len(str(value)) > 10000:
            continue
        fresh = timestamp_is_fresh(row["captured"], observed_at)
        previous = vehicle.readings.get(ident)
        if previous is None or fresh or not previous.get("fresh"):
            vehicle.readings[ident] = {
                "value": value, "captured": row["captured"],
                "observed": observed_at.isoformat(), "fresh": fresh,
                "path": row["path"], "job": row["job"],
                "status": "verified" if fresh else "readable_but_stale",
            }
        profile.attribute_evidence[ident] = {
            "status": "verified" if fresh else "readable_but_stale",
            "path": row["path"], "job": row["job"],
            "source": "cariad.selectivestatus",
            "timestamp_present": bool(row["captured"]),
        }
        if fresh and ident not in profile.attribute_routes:
            profile.attribute_routes[ident] = "cariad.selectivestatus.batch"
        mapped += 1
        fresh_count += int(fresh)
    vehicle.v2_initial_discovery_completed = True
    return {"mapped": mapped, "fresh": fresh_count}
