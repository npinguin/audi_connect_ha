"""V3 read-only attribute recovery from one shared CARIAD selective-status batch.

No V2 runtime imports, no automatic vehicle commands or position requests.
"""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
from .freshness import timestamp_is_fresh
from .historical_catalog import ATTRIBUTES, V2_JOBS, advertised_capabilities, extract_attributes
from .api_value_mappings import normalize_api_value, transform_for
from .attribute_contracts import semantic_value_issue


def planned_jobs(vehicle: Any, profile: Any) -> tuple[str, ...]:
    if not getattr(vehicle, "v2_initial_discovery_completed", False):
        return V2_JOBS
    active = {ATTRIBUTES[name]["job"] for name, route in profile.attribute_routes.items()
              if name in ATTRIBUTES and ATTRIBUTES[name]["job"] and route == "cariad.selectivestatus.batch"}
    # A mapped but stale field is not active, yet it must keep being refreshed.
    # Dropping it from the next batch would prevent later vehicle updates from
    # ever recovering without a manual restart or discovery.
    active.update(ATTRIBUTES[name]["job"] for name, evidence in profile.attribute_evidence.items()
                  if name in ATTRIBUTES and ATTRIBUTES[name]["job"] and
                  evidence.get("status") == "readable_but_stale")
    # A previously readable job can legitimately provide no *fresh* values when
    # the car is parked.  V2 keeps such jobs in subsequent selective-status
    # requests; dropping them makes existing HA sensors disappear.
    active.update(
        job for job, result in getattr(profile, "job_discovery", {}).items()
        if result == "observed"
    )
    # Keep explicitly advertised jobs as well as observed jobs. A partial
    # 207/error does not erase previously learned readable capabilities.
    reported = getattr(vehicle, "advertised_capabilities", set())
    impaired = getattr(vehicle, "impaired_capabilities", set())
    active.update(job for job in V2_JOBS if job in reported and job not in impaired)
    if "oilLevelStatus" in reported and "oilLevelStatus" not in impaired:
        active.add("oilLevel")
    active.update(("climatisation", "userCapabilities"))
    return tuple(job for job in V2_JOBS if job in active)


def _capture_in_utc(value: Any) -> datetime | None:
    """Parse a vehicle capture time without treating cloud receipt as capture."""
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp.astimezone(UTC) if stamp.tzinfo is not None else None


def _accept_observation(previous: dict[str, Any] | None, captured: Any) -> bool:
    """Never replace a newer car reading with an older cached API value."""
    if previous is None:
        return True
    prior = _capture_in_utc(previous.get("captured"))
    incoming = _capture_in_utc(captured)
    if prior is None:
        return True
    return incoming is not None and incoming >= prior


def record_invalid_observation(vehicle: Any, ident: str, captured: Any, observed_at: datetime,
                               path: str, job: str | None, reason: str, family: str = "cariad") -> None:
    """Invalidate a contradictory newer sample without accepting old cache."""
    if _accept_observation(vehicle.readings.get(ident), captured):
        vehicle.readings[ident] = {
            "value": None, "captured": captured, "observed": observed_at.isoformat(),
            "fresh": False, "path": path, "job": job, "status": "invalid_value",
            "family": family, "reason": reason,
        }


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
        try:
            value = normalize_api_value(value, transform_for("cariad", ident))
        except ValueError:
            # Misconfigured or incompatible response mapping is not a valid sensor.
            continue
        selected = profile.attribute_routes.get(ident)
        if selected and selected != "cariad.selectivestatus.batch":
            continue
        issue = semantic_value_issue(row["entity_key"], value)
        if issue:
            record_invalid_observation(vehicle, ident, row["captured"], observed_at,
                                       row["path"], row["job"], issue)
            continue
        if isinstance(value, str) and value.strip().lower() in (
            "unknown", "invalid", "unsupported", "unavailable", "error", ""
        ) and not (ident == "externalPower" and value.strip().lower() == "unavailable"):
            if ident == "chargingState":
                record_invalid_observation(vehicle, ident, row["captured"], observed_at,
                                           row["path"], row["job"], "unknown_charging_state")
            continue
        if len(str(value)) > 10000:
            continue
        fresh = timestamp_is_fresh(row["captured"], observed_at)
        previous = vehicle.readings.get(ident)
        if not _accept_observation(previous, row["captured"]):
            continue
        vehicle.readings[ident] = {
            "value": value, "captured": row["captured"],
            "observed": observed_at.isoformat(), "fresh": fresh,
            "path": row["path"], "job": row["job"],
            "status": "verified" if fresh else "readable_but_stale",
            "family": "cariad",
        }
        profile.attribute_evidence[ident] = {
            "status": "verified" if fresh else "readable_but_stale",
            "path": row["path"], "job": row["job"],
            "source": "cariad.selectivestatus",
            "timestamp_present": bool(row["captured"]),
        }
        # A proven V2 response field is *readable* even if the vehicle's
        # capture time is older than 60 minutes.  Activation exposes a clearly
        # marked last-known sensor, not a fresh control or lock reading.
        if (ident not in profile.attribute_routes
                and ATTRIBUTES[ident]["platform"] in ("sensor", "binary_sensor")):
            profile.attribute_routes[ident] = "cariad.selectivestatus.batch"
        mapped += 1
        fresh_count += int(fresh)
    from .derived_values import observe_derived
    observe_derived(vehicle, profile, payload, observed_at, _accept_observation)
    from .structured_details import observe_structured
    observe_structured(vehicle, payload, observed_at, _accept_observation)
    vehicle.v2_initial_discovery_completed = True
    return {"mapped": mapped, "fresh": fresh_count}
