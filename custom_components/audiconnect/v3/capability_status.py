"""V3 Capability Status Dashboard — evidence, not inferred support.

A read-only inventory of known paths from the V3 catalog and carefully
copied V2 references.  The V2 references do NOT import or execute V2 code,
and MUST NEVER be reported as tested by V3 without actual V3 evidence.

Rows use placeholders instead of real VINs and never expose raw responses.
"""

from __future__ import annotations

from typing import Any

from .development_profiles import DevelopmentProfile
from .vehicle import V3Vehicle

# Source: V2 capability_jobs.BASE_SELECTIVE_JOBS and api_probe.py.
# This is a migration backlog, not 24 proven V3 capabilities.
_V2_SELECTIVE_JOBS = {
    "access": "remote",
    "activeVentilation": "climate",
    "auxiliaryHeating": "climate",
    "batteryChargingCare": "charging",
    "batterySupport": "charging",
    "charging": "charging",
    "chargingProfiles": "charging",
    "chargingTimers": "charging",
    "climatisation": "climate",
    "climatisationTimers": "climate",
    "departureProfiles": "charging",
    "departureTimers": "charging",
    "fuelStatus": "vehicle_status",
    "honkAndFlash": "remote",
    "hybridCarAuxiliaryHeating": "climate",
    "lvBattery": "vehicle_status",
    "measurements": "vehicle_status",
    "oilLevel": "vehicle_status",
    "readiness": "vehicle_status",
    "userCapabilities": "vehicle_status",
    "vehicleHealthInspection": "vehicle_status",
    "vehicleHealthWarnings": "vehicle_status",
    "vehicleLights": "vehicle_status",
}
_V2_ADDITIONAL_GET = {
    "parkingPosition": "/vehicle/v1/vehicles/{VIN}/parkingposition",
    "pendingRequests": "/vehicle/v1/vehicles/{VIN}/pendingrequests",
    "tripStatistics": "/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs=tripStatistics",
}


def build_status_report(
    vehicle: V3Vehicle, profile: DevelopmentProfile,
) -> dict[str, Any]:
    """Produce independently understandable API/attribute/control coverage.

    Workbench candidates are listed even if context-incompatible; 'absent'
    evidence is always 'not_tested', never 'unsupported'.
    """
    rows: list[dict[str, Any]] = []
    seen_paths: set[tuple[str, str]] = set()
    for capability, definition in profile.registry.capabilities.items():
        for aspect in ("status", "start", "stop"):
            ids = profile.registry.operations_for(capability, aspect)
            applicable = set(profile.registry.resolve(
                capability, aspect, vehicle.context
            )["available_operations"])
            for ident in ids:
                op = profile.registry.operations[ident]
                key = f"{capability}.{aspect}"
                read_evidence = profile.read_results.get(ident, {})
                control_evidence = profile.control_results.get(ident)
                result = (
                    read_evidence.get("outcome", "not_tested")
                    if aspect == "status" else control_evidence or "not_tested"
                )
                if ident not in applicable:
                    result = "not_applicable_to_vehicle"
                elif key in profile.discovery.disabled and aspect != "status":
                    result = "disabled_by_user"
                paths = op.get("response_paths") or [None]
                for path in paths:
                    # A 2xx GET mapping is proof for one actual extracted
                    # response field only, not every fallback path in catalog.
                    attr_result = result
                    if (
                        aspect == "status" and result == "worked"
                        and path != vehicle.climate_field
                    ):
                        attr_result = "mapped_not_confirmed"
                    rows.append({
                        "capability": capability,
                        "aspect": aspect,
                        "attribute": path if path is not None else (
                            "control." + aspect
                        ),
                        "api_family": op["family"],
                        "operation": ident,
                        "method": op["method"],
                        "path": op["path"],
                        "status": attr_result,
                        "route_result": result,
                        "source": "v3_live_evidence" if (
                            read_evidence or control_evidence is not None
                        ) else "v3_catalog",
                        "selected": profile.active.get(key) == ident,
                        "saved_candidate": profile.draft_selected.get(key) == ident,
                        "custom": ident in profile.custom,
                        "context_applicable": ident in applicable,
                    })
                if op["method"] == "GET":
                    seen_paths.add((op["family"], op["path"]))

    for job, family_group in _V2_SELECTIVE_JOBS.items():
        path = f"/vehicle/v1/vehicles/{{VIN}}/selectivestatus?jobs={job}"
        if ("cariad", path) in seen_paths:
            continue
        rows.append({
            "capability": family_group,
            "aspect": "status",
            "attribute": job,
            "api_family": "cariad",
            "operation": f"v2.reference.selectivestatus.{job}",
            "method": "GET",
            "path": path,
            "status": "known_v2_not_migrated",
            "route_result": "known_v2_not_migrated",
            "source": "v2_reference_only",
            "selected": False,
            "saved_candidate": False,
            "custom": False,
            "context_applicable": None,
        })
    for label, path in _V2_ADDITIONAL_GET.items():
        if ("cariad", path) in seen_paths:
            continue
        rows.append({
            "capability": "mobility" if label != "pendingRequests" else "remote",
            "aspect": "status",
            "attribute": label,
            "api_family": "cariad",
            "operation": f"v2.reference.{label}",
            "method": "GET",
            "path": path,
            "status": "known_v2_not_migrated",
            "route_result": "known_v2_not_migrated",
            "source": "v2_reference_only",
            "selected": False,
            "saved_candidate": False,
            "custom": False,
            "context_applicable": None,
        })

    counts = {
        "total": len(rows),
        "verified_working": sum(x["status"] == "worked" for x in rows),
        "reported_failed": sum(x["status"] in ("failed", "previously_failed") for x in rows),
        "stale": sum(x["status"] == "readable_but_stale" for x in rows),
        "not_tested": sum(x["status"] == "not_tested" for x in rows),
        "v2_reference_only": sum(x["source"] == "v2_reference_only" for x in rows),
        "not_applicable": sum(x["status"] == "not_applicable_to_vehicle" for x in rows),
    }
    return {
        "schema_version": 1,
        "vehicle": {
            "label": vehicle.name,
            "model": vehicle.model,
            "model_family": vehicle.model_family or "unknown",
            "region": vehicle.country,
            "authentication": vehicle.context.auth,
        },
        "counts": counts,
        "rows": rows,
        "notes": (
            "V2 reference paths are only migration candidates: not discovered "
            "or validated by V3. A cloud response is not a physical command "
            "confirmation. No VIN, tokens or response data are included."
        ),
    }
