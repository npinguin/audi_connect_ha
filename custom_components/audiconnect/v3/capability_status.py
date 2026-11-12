"""V3 Capability Status Dashboard — evidence, not inferred support.

A read-only inventory of known paths from the V3 catalog and carefully
copied V2 references.  The V2 references do NOT import or execute V2 code,
and MUST NEVER be reported as tested by V3 without actual V3 evidence.

Rows use placeholders instead of real VINs and never expose raw responses.
"""

from __future__ import annotations

from typing import Any

from .development_profiles import DevelopmentProfile
from .action_discovery import approval_group
from .vehicle import V3Vehicle
from .historical_catalog import INVENTORY, ALIAS_OF, CANONICAL_ATTRIBUTES
from .legacy_read_mappings import variant_for as legacy_variant_for
from .read_discovery import summary as discovery_summary

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
        for aspect in ("status", *(definition.get("control") or {})):
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

    for attr in CANONICAL_ATTRIBUTES.values():
        evidence = profile.attribute_evidence.get(attr["id"], {})
        selected = profile.attribute_routes.get(attr["id"])
        legacy = legacy_variant_for(attr["id"])
        candidate = (legacy if vehicle.context.auth == "legacy" else None)
        known = bool(attr["paths"] or candidate)
        family = ("mbb" if evidence.get("source") == "mbb.legacy"
                  else "cariad" if evidence.get("source") == "cariad.selectivestatus"
                  else "mbb" if candidate
                  else "cariad" if vehicle.context.auth == "auth0" and attr["paths"]
                  else "unknown")
        mapped_path = (evidence.get("path")
                       or (candidate["response_paths"][0] if candidate else None)
                       or (attr["paths"][0] if attr["paths"] else "-"))
        rows.append({
            "capability": attr["capability"], "aspect": "status",
            "attribute": attr["id"], "entity_key": attr["entity_key"],
            "api_family": family,
            "operation": selected or ("v2.attribute." + attr["id"]),
            "method": "GET" if known else "-",
            "path": mapped_path,
            "status": evidence.get(
                "status",
                ("not_observed" if attr["job"] in profile.job_discovery
                 and profile.job_discovery[attr["job"]] == "not_observed"
                 and known and attr["paths"]
                 else "not_tested" if known else "mapping_pending"),
            ),
            "route_result": evidence.get("status", "not_tested"),
            "source": "v3_live_evidence" if evidence else "v2_attribute_reference",
            "selected": selected is not None, "saved_candidate": False,
            "custom": False, "context_applicable": bool(candidate) if vehicle.context.auth == "legacy" else bool(attr["paths"]),
            "job": attr["job"],
        })
    for control in INVENTORY["controls"]:
        rows.append({
            "capability": control["capability"], "aspect": "control",
            "attribute": control["id"], "api_family": control["api_family"] or "unknown",
            "operation": "v2.control." + control["id"],
            "method": "POST" if control["path"] else "-", "path": control["path"] or "-",
            "status": "migration_pending", "route_result": "migration_pending",
            "source": "v2_control_reference", "selected": False,
            "saved_candidate": False, "custom": False, "context_applicable": None,
        })
    # The catalog is global; these are real scan results for the selected car.
    scan = discovery_summary(profile)
    controls_for_vehicle = []
    for capability, definition in profile.registry.capabilities.items():
        for action in (definition.get("control") or {}):
            available = profile.registry.resolve(
                capability, action, vehicle.context
            )["available_operations"]
            current = profile.active.get(f"{capability}.{action}")
            controls_for_vehicle.append({
                "capability": capability, "action": action,
                "api_family": "mbb" if vehicle.context.auth == "legacy" else "cariad",
                "candidate_count": len(available),
                "approval_groups": sorted({
                    approval_group(capability, action, profile.registry.operations[ident])
                    for ident in available
                }),
                "verified": current is not None and profile.control_results.get(current) == "worked",
                "status": "verified" if current and profile.control_results.get(current) == "worked"
                          else "not_tested" if available else "not_applicable_to_vehicle",
                "requires_manual_test": True,
            })
    counts = {
        **scan,
        "observed_attributes": sum(
            r["source"] == "v3_live_evidence" and
            r["status"] in ("verified", "readable_but_stale")
            for r in rows if r.get("entity_key")
        ),
        "pending_mappings": sum(
            bool(r.get("entity_key")) and r["status"] == "mapping_pending"
            for r in rows
        ),
        "total": len(rows),
        "v2_attribute_inventory": len(INVENTORY["attributes"]),
        "v2_unique_attributes": len(CANONICAL_ATTRIBUTES),
        "v2_alias_references": len(ALIAS_OF),
        "v2_control_inventory": len(INVENTORY["controls"]),
        "v3_verified_attributes": sum(r["source"] == "v3_live_evidence" and r["status"] == "verified" for r in rows),
        "v2_unmapped_attributes": sum(r["status"] == "mapping_pending" for r in rows),
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
        "control_actions": controls_for_vehicle,
        "rows": rows,
        "notes": (
            "V2 reference paths are only migration candidates: not discovered "
            "or validated by V3. A cloud response is not a physical command "
            "confirmation. No VIN, tokens or response data are included."
        ),
    }
