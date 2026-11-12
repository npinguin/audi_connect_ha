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

from .historical_catalog import V2_JOBS

MAX_EXTRA_INITIAL_REQUESTS = 4
MAX_EXTRA_PERIODIC_REQUESTS = 2

# Prioritize mapped jobs first, then exhaust all known fixed read-only jobs.
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
    ("activeVentilation", "auxiliaryHeating", "hybridCarAuxiliaryHeating"),
    ("batteryChargingCare", "batterySupport"),
    ("departureProfiles", "departureTimers"),
    ("honkAndFlash", "lvBattery", "vehicleHealthWarnings"),
)

_JOBS = frozenset(V2_JOBS)


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
        # Some reviewed jobs return data inside a shared namespace. A timer
        # schema is read evidence only, never permission to activate ventilation.
        if job == "activeVentilation":
            timers = payload.get("climatisationTimers")
            if isinstance(timers, Mapping):
                stack.append(timers.get("activeVentilationTimersStatus"))
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
                        if job in _JOBS
                        and profile.job_discovery.get(job) != "observed"
                        and profile.job_probe_attempts.get(job, 0) < 1)
        if pending:
            groups.append(pending)
        if len(groups) == max_groups:
            break
    return groups


def reserve_group(profile: Any, jobs: tuple[str, ...]) -> None:
    for job in jobs:
        if job not in _JOBS:
            raise ValueError("Unknown job cannot be auto-probed")
        profile.job_probe_attempts[job] = profile.job_probe_attempts.get(job, 0) + 1


def summary(profile: Any) -> dict[str, int]:
    observed = sum(profile.job_discovery.get(job) == "observed" for job in V2_JOBS)
    missing = sum(profile.job_discovery.get(job) == "not_observed" for job in V2_JOBS)
    inconclusive = sum(profile.job_discovery.get(job) == "inconclusive" for job in V2_JOBS)
    assessed = sum(profile.job_discovery.get(job) == "observed" or
                   (profile.job_discovery.get(job) == "not_observed" and
                    profile.job_probe_attempts.get(job, 0) > 0) for job in V2_JOBS)
    return {
        "catalog_jobs": len(V2_JOBS), "assessed_jobs": assessed,
        "assessment_percent": round(100 * assessed / len(V2_JOBS), 1),
        "observed_percent": round(100 * observed / len(V2_JOBS), 1), "observed_jobs": observed,
        "not_observed_jobs": missing, "inconclusive_jobs": inconclusive,
        "not_scanned_jobs": len(V2_JOBS) - observed - missing - inconclusive,
        "targeted_probe_jobs": len(profile.job_probe_attempts),
    }

def full_read_plan(profile, context, family):
    """One reviewed fixed GET per distinct path, with explicit exclusions."""
    import string
    candidates, excluded = [], []
    seen = set()
    registry = profile.registry
    for capability, definition in registry.capabilities.items():
        if not definition.get("status"):
            continue
        resolved = registry.resolve(capability, "status", context)
        allowed = set(resolved["available_operations"])
        for ident in registry.operations_for(capability, "status"):
            op = registry.operations[ident]
            if op.get("method") != "GET" or op.get("family") != family:
                continue
            reason = None
            if ident not in allowed:
                reason = "context_or_adapter_not_applicable"
            elif ident in profile.custom:
                reason = "custom_route_requires_explicit_test"
            elif "{JOBS}" in op["path"]:
                reason = "shared_batch_covered_separately"
            elif any(name not in ("VIN", "TYPE", "COUNTRY")
                     for _, name, _, _ in string.Formatter().parse(op["path"]) if name):
                reason = "parameters_required"
            elif op.get("request_body") is not None:
                reason = "unexpected_get_body"
            elif op["path"] in seen:
                reason = "duplicate_path"
            if reason:
                excluded.append({"operation": ident, "reason": reason})
                continue
            seen.add(op["path"])
            candidates.append((ident, op["path"]))
    # Prioritize not-observed jobs without omitting already batch-observed routes.
    def priority(item):
        job = item[1].split("jobs=", 1)[-1] if "jobs=" in item[1] else None
        return (profile.job_discovery.get(job) == "observed", item[0])
    return sorted(candidates, key=priority), excluded


def user_progress(car, profile, auth):
    """Read coverage and control evidence are independent, never proof of support."""
    from .historical_catalog import INVENTORY
    from .control_resolution import control_decision
    modern = car.context.auth == "auth0" or car.legacy_cariad
    jobs = {}
    if modern:
        for job in V2_JOBS:
            status = profile.job_discovery.get(job, "not_scanned")
            jobs[job] = {"status": status, "assessed": status == "observed" or (
                status == "not_observed" and profile.job_probe_attempts.get(job, 0) > 0)}
    reads = {}
    if "mobility" in profile.registry.capabilities and modern:
        from .trips import CARIAD_TRIP_OPERATIONS
        available = profile.registry.resolve("mobility", "status", car.context)["available_operations"]
        for operation in CARIAD_TRIP_OPERATIONS:
            if operation in available:
                reads[operation] = profile.api_observations.get(operation, {}).get("http_status")
    if car.context.auth == "legacy":
        from .legacy_read_mappings import ROUTES
        for kind in ROUTES:
            operation = "mbb.discovery." + kind
            reads[operation] = profile.api_observations.get(operation, {}).get("http_status")
    def assessed_http(status):
        return type(status) is int and (200 <= status < 300 or status in (400, 404, 405, 410, 422))
    controls = []
    for capability, definition in profile.registry.capabilities.items():
        for action in definition.get("control", {}):
            available = profile.registry.resolve(capability, action, car.context)["available_operations"]
            decision = control_decision(car, profile, auth, capability, action)
            physical = "worked" if any(profile.control_results.get(op) == "worked" for op in available) else (
                "failed" if any(profile.control_results.get(op) == "failed" for op in available) else "not_tested")
            controls.append({"capability": capability, "action": action,
                "catalog_applicable": bool(available), "eligible": bool(decision["operation"]),
                "status": decision["status"], "physical": physical})
    owners = {row["id"]: row["capability"] for row in INVENTORY["jobs"]}
    capabilities = {}
    for name in profile.registry.capabilities:
        subset = [row for job, row in jobs.items() if owners.get(job) == name]
        actions = [row for row in controls if row["capability"] == name]
        capabilities[name] = {"jobs_total": len(subset),
            "jobs_assessed": sum(row["assessed"] for row in subset),
            "jobs_observed": sum(row["status"] == "observed" for row in subset),
            "controls_catalog_applicable": sum(row["catalog_applicable"] for row in actions),
            "controls_physically_verified": sum(row["physical"] == "worked" for row in actions)}
    total = len(jobs) + len(reads)
    assessed = sum(row["assessed"] for row in jobs.values()) + sum(assessed_http(s) for s in reads.values())
    applicable = [row for row in controls if row["catalog_applicable"]]
    verified = sum(row["physical"] == "worked" for row in applicable)
    return {"read_assessment_percent": round(100 * assessed / total, 1) if total else None,
        "read_assessed": assessed, "read_total": total, "jobs": jobs,
        "standalone_http": reads, "model_present": bool(car.model),
        "controls_catalog_applicable": len(applicable), "controls_physically_verified": verified,
        "control_verification_percent": round(100 * verified / len(applicable), 1) if applicable else None,
        "controls": controls, "capabilities": capabilities,
        "scope": "reviewed_read_assessment_not_vehicle_support; location excluded"}
