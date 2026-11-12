"""Bounded automatic read-only CARIAD discovery.

The first request is the existing 23-job shared selectivestatus GET. These
small, prioritized follow-up groups are used only when its response has no
recognizable field for a historical job. Never send a vehicle action, wake-up,
location request, or every possible route on startup.

Discovery evidence is *vehicle-scoped*: a requested but missing field is not
evidence that the capability is unsupported on other Audi models.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .historical_catalog import ATTRIBUTES, V2_JOBS

MAX_EXTRA_INITIAL_REQUESTS = 2
MAX_EXTRA_PERIODIC_REQUESTS = 1

# Prioritize jobs with concrete V2 response mappings. Unmapped historical jobs
# are inventoried and included in the initial shared batch, not sprayed as GETs.
PROBE_GROUPS: tuple[tuple[str, ...], ...] = (
    ("climatisation",),
    ("charging",),
    ("fuelStatus", "measurements"),
    ("access", "vehicleLights"),
    ("vehicleHealthInspection", "oilLevel"),
    ("readiness",),
    ("chargingProfiles", "chargingTimers"),
    ("climatisationTimers",),
    ("userCapabilities",),
)

_JOBS = frozenset(V2_JOBS)
_MAPPED = frozenset(
    item["job"] for item in ATTRIBUTES.values()
    if item["paths"] and item["job"]
)


def record_jobs(profile: Any, requested: tuple[str, ...], *,
                status: int, payload: Any) -> None:
    """Store only response-presence evidence, never raw Audi response content."""
    if not getattr(profile, "job_discovery", None) or isinstance(profile.job_discovery, dict):
        pass
    for job in requested:
        if job not in _JOBS:
            continue
        if status in (401, 403, 429) or status >= 500 or not isinstance(payload, dict):
            # Temporary cloud/auth errors do not mean unsupported.
            if profile.job_discovery.get(job) != "observed":
                profile.job_discovery[job] = "inconclusive"
            continue
        top = payload.get(job)
        found = False
        stack = [top]
        budget = 64
        while stack and budget:
            budget -= 1
            item = stack.pop()
            if isinstance(item, Mapping):
                if item.get("error") is not None:
                    continue
                if "value" in item and item["value"] not in (None, {}, []):
                    found = True
                    break
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item[:16])
        if found or any(item["job"] == job for item in profile.attribute_evidence.values()):
            profile.job_discovery[job] = "observed"
        elif profile.job_discovery.get(job) != "observed":
            profile.job_discovery[job] = "not_observed"


def pending_groups(profile: Any, *, max_groups: int) -> list[tuple[str, ...]]:
    """Fair, finite probe plan; each job is targeted at most once automatically."""
    groups = []
    for group in PROBE_GROUPS:
        pending = tuple(job for job in group
                        if job in _MAPPED
                        and profile.job_discovery.get(job) != "observed"
                        and profile.job_probe_attempts.get(job, 0) < 1)
        if pending:
            groups.append(pending)
        if len(groups) == max_groups:
            break
    return groups


def reserve_group(profile: Any, jobs: tuple[str, ...]) -> None:
    for job in jobs:
        if job not in _MAPPED:
            raise ValueError("Unmapped job cannot be auto-probed")
        profile.job_probe_attempts[job] = profile.job_probe_attempts.get(job, 0) + 1


def summary(profile: Any) -> dict[str, int]:
    observed = sum(profile.job_discovery.get(job) == "observed" for job in V2_JOBS)
    missing = sum(profile.job_discovery.get(job) == "not_observed" for job in V2_JOBS)
    inconclusive = sum(profile.job_discovery.get(job) == "inconclusive" for job in V2_JOBS)
    return {
        "catalog_jobs": len(V2_JOBS), "observed_jobs": observed,
        "not_observed_jobs": missing, "inconclusive_jobs": inconclusive,
        "not_scanned_jobs": len(V2_JOBS) - observed - missing - inconclusive,
        "targeted_probe_jobs": len(profile.job_probe_attempts),
    }
