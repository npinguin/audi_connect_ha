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
MAX_PROBES = 8
MIN_RATE_LIMIT_REMAINING = 12


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


async def run_read_only_probes(
    api: Any, access_token: str, url_for_suffix: Callable[[str], str]
) -> dict[str, Any]:
    """Run a strictly fixed set of GETs on explicit user request only."""
    if not access_token:
        raise ValueError("Missing active Audi access token")
    outcomes: list[dict[str, Any]] = []
    stop_reason: str | None = None
    for name, suffix, job in READ_ONLY_PROBES[:MAX_PROBES]:
        if stop_reason:
            outcomes.append({"probe": name, "outcome": "skipped", "reason": stop_reason})
            continue
        remaining = getattr(api, "vcf_remaining_calls", None)
        if remaining is not None and remaining < MIN_RATE_LIMIT_REMAINING:
            stop_reason = "low_rate_limit_budget"
            outcomes.append({"probe": name, "outcome": "skipped", "reason": stop_reason})
            continue
        try:
            response = await api.request(
                "GET",
                url_for_suffix(suffix),
                headers={"Authorization": "Bearer " + access_token},
                data=None,
            )
            outcome = classify_payload(response, job)
            outcomes.append({"probe": name, "outcome": outcome, "http_status": 200})
        except ClientResponseError as exc:
            outcome = classify_http_status(exc.status)
            outcomes.append({
                "probe": name, "outcome": outcome, "http_status": int(exc.status)
            })
            if exc.status in (401, 429):
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
        "max_allowed": MAX_PROBES,
        "mutating_requests": 0,
        "results": outcomes,
    }
