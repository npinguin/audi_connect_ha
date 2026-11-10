"""Opt-in, bounded and read-only probes of known CARIAD routes.

No guesses, arbitrary URLs, authentication fallback or mutation requests.
Only status/classification is retained; the raw response is immediately discarded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from aiohttp import ClientResponseError

# Known GET-only paths already used or queried by the upstream integration.
# (name, route suffix, named selectivestatus job, if applicable)
READ_ONLY_PROBES: tuple[tuple[str, str, str | None], ...] = (
    ("capabilities", "selectivestatus?jobs=userCapabilities", "userCapabilities"),
    ("charging", "selectivestatus?jobs=charging", "charging"),
    ("charging_profiles", "selectivestatus?jobs=chargingProfiles", "chargingProfiles"),
    ("charging_timers", "selectivestatus?jobs=chargingTimers", "chargingTimers"),
    ("climatisation", "selectivestatus?jobs=climatisation", "climatisation"),
    (
        "hybrid_auxiliary_heating",
        "selectivestatus?jobs=hybridCarAuxiliaryHeating",
        "hybridCarAuxiliaryHeating",
    ),
    ("parking_position", "parkingposition", None),
    ("pending_requests", "pendingrequests", None),
)
# New candidates are explicitly experimental: the HAR advertises the feature,
# not a working CARIAD job. These are optional GETs only.
EXTENDED_READ_ONLY_PROBES: tuple[tuple[str, str, str | None], ...] = (
    ("climatisation_timers", "selectivestatus?jobs=climatisationTimers", "climatisationTimers"),
    ("measurements", "selectivestatus?jobs=measurements", "measurements"),
    ("vehicle_health_inspection", "selectivestatus?jobs=vehicleHealthInspection", "vehicleHealthInspection"),
    ("trip_statistics_experimental", "selectivestatus?jobs=tripStatistics", "tripStatistics"),
    ("auxiliary_heating", "selectivestatus?jobs=auxiliaryHeating", "auxiliaryHeating"),
)
# Experimental candidates from third-party Audi/VW client implementations.
# Read-only, on explicit user invocation; data is never retained in reports.
FEATURE_RESTORE_PROBES: tuple[tuple[str, str, str | None], ...] = (
    ("trip_shortterm", "trips:shortterm", None),
    ("trip_longterm", "trips:longterm", None),
    ("trip_last", "trips:shortterm/last", None),
    ("tripstatistics_shortterm", "tripstatistics?type=shortTerm", None),
    ("tripstatistics_longterm", "tripstatistics?type=longTerm", None),
    ("battery_support", "selectivestatus?jobs=batterySupport", "batterySupport"),
    ("tyre_pressure", "selectivestatus?jobs=tyrePressure", "tyrePressure"),
    (
        "vehicle_health_warnings",
        "selectivestatus?jobs=vehicleHealthWarnings",
        "vehicleHealthWarnings",
    ),
)
KNOWN_TRIP_ROUTES = frozenset({"shortterm", "longterm", "shortterm/last"})
MAX_FEATURE_RESTORE_PROBES = 8
MIN_FEATURE_RESTORE_START_BUDGET = 20
MIN_FEATURE_RESTORE_RESERVE = 12
# Audi may omit Vcf-Remaining-Calls entirely. One explicit probe invocation
# can still inspect five fixed GET routes, but never more while unmetered.
UNKNOWN_BUDGET_RESTORE_MAX_REQUESTS = 5

MAX_PROBES = 8
MAX_EXTENDED_PROBES = 13
MIN_RATE_LIMIT_REMAINING = 12
MIN_EXTENDED_RATE_LIMIT_REMAINING = 17


def _has_error(value: Any, max_nodes: int = 64) -> bool:
    """Inspect response *shape* only, bounded; never serialize its contents."""
    pending = [value]
    while pending and max_nodes > 0:
        max_nodes -= 1
        item = pending.pop()
        if isinstance(item, dict):
            if item.get("error") is not None:
                return True
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item[:16])
    return False


def classify_payload(payload: Any, job: str | None) -> str:
    """HTTP 200 with an embedded job error is not usable vehicle data."""
    if not isinstance(payload, (dict, list)) or not payload:
        return "empty_or_unrecognized_payload"
    if job is not None:
        if not isinstance(payload, dict) or job not in payload:
            return "job_missing_from_response"
        value = payload[job]
        if _has_error(value):
            return "job_returned_error"
        if not isinstance(value, (dict, list)) or not value:
            return "job_empty_or_unrecognized"
        return "readable_job_not_command_proven"
    if _has_error(payload):
        return "response_contains_error"
    return "readable_response_not_command_proven"


def classify_http_status(status: int) -> str:
    if status == 204:
        return "no_content_now"
    if status == 401:
        return "authentication_rejected"
    if status == 403:
        return "authorization_denied"
    if status == 404:
        return "route_not_found_or_not_provisioned"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "upstream_error"
    return "http_error"


def resolve_restore_probe_url(
    suffix: str,
    vehicle_url: Callable[[str], str],
    trip_url: Callable[[str], str],
) -> str:
    """Resolve only hard-coded, reviewed trip routes to the BFF trips path."""
    if suffix.startswith("trips:"):
        kind = suffix.removeprefix("trips:")
        if kind not in KNOWN_TRIP_ROUTES:
            raise ValueError("Unrecognised trip restore route")
        return trip_url(kind)
    if suffix not in {probe[1] for probe in FEATURE_RESTORE_PROBES}:
        raise ValueError("Unrecognised feature restore route")
    return vehicle_url(suffix)


async def run_read_only_probes(
    api: Any, access_token: str, url_for_suffix: Callable[[str], str],
    *,
    extended: bool = False,
    restore: bool = False,
    restore_url_for_route: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Run only fixed, bounded GET probes on explicit user request."""
    if restore and extended:
        raise ValueError("Extended and restore probes are mutually exclusive")
    if restore and restore_url_for_route is None:
        raise ValueError("Restore probes require an approved route resolver")
    if not access_token:
        raise ValueError("Missing active Audi access token")
    if restore:
        paths = FEATURE_RESTORE_PROBES[:MAX_FEATURE_RESTORE_PROBES]
        minimum_budget = MIN_FEATURE_RESTORE_RESERVE
        mode = "restore"
    else:
        paths = READ_ONLY_PROBES[:MAX_PROBES]
        if extended:
            paths += EXTENDED_READ_ONLY_PROBES[
                : MAX_EXTENDED_PROBES - MAX_PROBES
            ]
        minimum_budget = (
            MIN_EXTENDED_RATE_LIMIT_REMAINING
            if extended
            else MIN_RATE_LIMIT_REMAINING
        )
        mode = "extended" if extended else "core"
    outcomes: list[dict[str, Any]] = []
    stop_reason: str | None = None
    unknown_budget_at_start = (
        restore and not isinstance(getattr(api, "vcf_remaining_calls", None), int)
    )
    for name, suffix, job in paths:
        if stop_reason:
            outcomes.append({"probe": name, "outcome": "skipped", "reason": stop_reason})
            continue
        remaining = getattr(api, "vcf_remaining_calls", None)
        if (
            unknown_budget_at_start
            and len(outcomes) >= UNKNOWN_BUDGET_RESTORE_MAX_REQUESTS
        ):
            stop_reason = "unknown_budget_probe_cap_reached"
        elif restore and isinstance(remaining, int) and not outcomes and (
            remaining < MIN_FEATURE_RESTORE_START_BUDGET
        ):
            stop_reason = "low_rate_limit_budget"
        elif remaining is not None and remaining <= minimum_budget:
            stop_reason = "low_rate_limit_budget"
        if stop_reason:
            outcomes.append({"probe": name, "outcome": "skipped", "reason": stop_reason})
            continue
        try:
            # Existing authenticated API path; payload never persisted.
            resolver = restore_url_for_route if restore else url_for_suffix
            assert resolver is not None
            response = await api.get(resolver(suffix))
            outcome = classify_payload(response, job)
            outcomes.append({"probe": name, "outcome": outcome, "http_status": "2xx"})
        except ClientResponseError as exc:
            outcome = classify_http_status(exc.status)
            outcomes.append({
                "probe": name, "outcome": outcome, "http_status": int(exc.status)
            })
            if exc.status in (401, 429) or (restore and exc.status >= 500):
                stop_reason = outcome
        except TimeoutError:
            outcomes.append({"probe": name, "outcome": "request_timed_out"})
            stop_reason = "request_timed_out"
        except Exception:
            # Exception text may contain VIN, token, URLs or raw response data.
            outcomes.append({"probe": name, "outcome": "request_error"})
            stop_reason = "request_error"

    return {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "attempted": sum(row["outcome"] != "skipped" for row in outcomes),
        "max_allowed": len(paths),
        "mode": mode,
        "mutating_requests": 0,
        "results": outcomes,
    }
