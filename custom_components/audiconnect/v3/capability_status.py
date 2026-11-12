"""V3 Capability Status Dashboard — evidence, not inferred support.

A read-only inventory of known paths from the V3 catalog and carefully
copied V2 references.  The V2 references do NOT import or execute V2 code,
and MUST NEVER be reported as tested by V3 without actual V3 evidence.

Rows use placeholders instead of real VINs and never expose raw responses.
"""

from __future__ import annotations

from typing import Any
from datetime import UTC, datetime
from collections import Counter

from .attribute_contracts import semantic_value_issue, contract_for, binary_contract_for
from .freshness import timestamp_is_fresh

from .development_profiles import DevelopmentProfile
from .action_discovery import approval_group
from .vehicle import V3Vehicle
from .historical_catalog import INVENTORY, ALIAS_OF, CANONICAL_ATTRIBUTES
from .custom_attributes import attributes_for
from .legacy_read_mappings import variant_for as legacy_variant_for
from .read_discovery import summary as discovery_summary
from .transport import INVENTORY_OPERATION

# Source: V2 capability_jobs.BASE_SELECTIVE_JOBS and api_probe.py.
# This is a migration backlog, not 24 proven V3 capabilities.
_V2_SELECTIVE_JOBS = {row["id"]: row["capability"] for row in INVENTORY["jobs"]}
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
                        and path != (vehicle.climate_field if capability == "climate"
                                     else vehicle.capability_readings.get(capability, {}).get("path"))
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
    for attr in attributes_for(profile).values():
        if not attr.get("local"):
            continue
        ident = attr["id"]
        evidence = profile.attribute_evidence.get(ident, {})
        selected = profile.attribute_routes.get(ident)
        choices = [r for r in profile.attribute_custom.values() if r["attribute"] == ident]
        rows.append({"capability": attr["capability"], "aspect": "status",
                     "attribute": ident, "entity_key": attr["entity_key"], "api_family": "cariad",
                     "operation": selected or (choices[0]["id"] if choices else ident), "method": "GET",
                     "path": evidence.get("path") or (choices[0]["response_path"] if choices else "-"),
                     "status": evidence.get("status", "not_tested"), "route_result": evidence.get("status", "not_tested"),
                     "source": "v3_live_evidence" if evidence else "local_attribute_definition",
                     "selected": selected is not None, "saved_candidate": False, "custom": True,
                     "context_applicable": vehicle.context.auth != "legacy" or vehicle.legacy_cariad, "job": None})
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
    cockpit = _cockpit(vehicle, profile, rows, controls_for_vehicle)
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
        **cockpit,
        "vehicle": {
            "label": vehicle.name,
            "model": vehicle.model,
            "model_family": vehicle.model_family or "unknown",
            "region": vehicle.country,
            "authentication": vehicle.context.auth,
        },
        "counts": counts,
        "control_actions": controls_for_vehicle,
        "pending_control": profile.discovery._active.public() if profile.discovery._active else None,
        "rows": rows,
        "notes": (
            "V2 reference paths are only migration candidates: not discovered "
            "or validated by V3. A cloud response is not a physical command "
            "confirmation. No VIN, tokens or response data are included."
        ),
    }

def _cockpit(vehicle, profile, rows, controls):
    """Read-only projection of existing evidence; no network or state writes."""
    now = datetime.now(UTC)
    findings = []
    attributes = []
    catalog = profile.registry.operations
    records = profile.api_observations
    fast = profile.fast_bindings
    definitions = attributes_for(profile)
    mapped_paths = {}
    for descriptor in definitions.values():
        for path in descriptor["paths"]:
            mapped_paths.setdefault(path, set()).add(descriptor["id"])
    for route in profile.attribute_custom.values():
        path = route.get("response_path")
        if path:
            mapped_paths.setdefault(path, set()).add(route["attribute"])
    for row in rows:
        if not row.get("entity_key"):
            continue
        ident = row["attribute"]
        reading = vehicle.readings.get(ident, {})
        definition = definitions.get(ident, {})
        contract = (binary_contract_for(row["entity_key"])
                    if definition.get("platform") == "binary_sensor"
                    else contract_for(row["entity_key"]))
        contract = definition.get("contract") or contract
        issue = reading.get("reason")
        value = reading.get("value")
        if not issue and reading:
            issue = semantic_value_issue(row["entity_key"], value, contract)
        if reading:
            # Derived values can exist without a separately persisted GET route.
            if reading.get("status") == "invalid_value" or issue:
                row["status"] = "invalid_value"
            elif value is not None:
                row["status"] = ("verified" if timestamp_is_fresh(reading.get("captured"), now)
                                 else "readable_but_stale")
            row["path"] = reading.get("path") or row["path"]
            row["source"] = "v3_live_evidence"
            row["api_family"] = reading.get("family") or row["api_family"]
        row.update(platform=definition.get("platform"), metadata=contract,
                   observed=bool(reading), captured=reading.get("captured"),
                   observed_at=reading.get("observed"),
                   value_type=type(value).__name__ if value is not None else None,
                   semantic_issue=issue)
        if issue:
            findings.append({"id": "attribute:" + ident, "severity": "review",
                             "capability": row["capability"], "attribute": ident,
                             "reason": issue, "operation": row["operation"]})
        attributes.append(row)
    for item in controls:
        key = item["capability"] + "." + item["action"]
        binding = fast.get(key, {})
        item.update(binding_status=binding.get("status", "unknown"),
                    active_operation=binding.get("operation"),
                    enabled=bool(binding.get("operation")),
                    physical_evidence="local_verified" if binding.get("status") == "local_verified"
                    else "historical_worked" if item["verified"] else "not_verified")
        if binding.get("operation"):
            item["requires_manual_test"] = False

    # Historical references are not real V3 tests. Keep them visible but separate.
    references = {row["operation"]: row for row in rows if row["source"] == "v2_reference_only"}
    journal = {row.operation: row for row in profile.command_journal}
    operations = []
    for ident in sorted(set(catalog) | set(records) | set(references) | set(journal)):
        op = catalog.get(ident, {})
        record = records.get(ident, {})
        ref = references.get(ident, {})
        matching = [row for row in rows if row["operation"] == ident and not row.get("entity_key")]
        read = profile.read_results.get(ident, {})
        physical = profile.control_results.get(ident, "not_tested")
        command = journal.get(ident)
        method = op.get("method") or record.get("method") or ref.get("method")
        active = (any(row["selected"] for row in matching)
                  or any(item.get("operation") == ident for item in fast.values())
                  or ident in profile.attribute_routes.values())
        applicable = [row["context_applicable"] for row in matching
                      if row["context_applicable"] is not None]
        http = record.get("http_status")
        schema = ("valid" if read.get("schema_valid") is True
                  else "invalid" if read.get("schema_valid") is False else "unknown")
        tested = bool(read or record or command or physical != "not_tested")
        reasons = []
        if schema == "invalid":
            reasons.append("response_schema_mismatch")
        if physical in ("failed", "uncertain") or (command and command.state in ("uncertain", "physical_failed")):
            reasons.append("physical_control_" + (command.state if command else physical))
        if http is not None and not 200 <= http < 300:
            reasons.append("http_error")
        if (ident != INVENTORY_OPERATION and method in ("POST", "PUT") and http is not None and 200 <= http < 300
                and physical != "worked" and not (command and command.state == "verified")):
            reasons.append("accepted_not_physically_verified")
        caps = sorted({row["capability"] for row in matching}
                      | ({command.capability} if command else set()))
        if ident == INVENTORY_OPERATION:
            caps = ["vehicle_status"]
            active = True
            applicable = [True]
            schema = "valid" if http is not None and 200 <= http < 300 else schema
            physical = "not_applicable"
        operation = {"operation": ident, "family": op.get("family") or record.get("family") or ref.get("api_family"),
                     "method": method, "path": op.get("path") or ref.get("path"), "capabilities": caps,
                     "applicability": ("applicable" if any(applicable) else
                                       "not_applicable" if applicable else "unknown"),
                     "tested": tested, "http_status": http, "transport": record.get("result"),
                     "http_class": read.get("http_class"), "schema": schema,
                     "partial_http": http == 207, "physical": physical,
                     "last_command_state": command.state if command else None,
                     "backend_result": command.backend_result if command else None,
                     "active": active, "last_test": record.get("at"),
                     "attention": reasons, "catalog": ident in catalog,
                     "reference_only": ident in references}
        fields = []
        for field in record.get("fields", []):
            path = field["path"]
            matches = sorted(mapped_paths.get(path, set()))
            status = ("metadata" if path.rsplit(".", 1)[-1] in ("carCapturedTimestamp", "timestamp") else
                      "declared_mapping" if matches else
                      "container" if field["type"] in ("array", "object") else
                      "review_unmapped")
            if path == "oilLevel.oilLevelStatus.value.value" and field["type"] == "boolean":
                status = "derived_binary"
                matches = ["oil_level_binary"]
            fields.append({**field, "mapping": status, "attributes": matches})
        job = (op.get("path", "").split("jobs=", 1)[-1] if "jobs=" in op.get("path", "") else None)
        operation["job_evidence"] = profile.job_discovery.get(job) if job else None
        if ident == INVENTORY_OPERATION:
            operation["path"] = "/vgql/v1/graphql"
            operation["read_only"] = True
        operation["fields"] = fields
        operation["fields_truncated"] = record.get("fields_truncated")
        if any(field["mapping"] == "review_unmapped" for field in fields):
            reasons.append("unmapped_response_fields_review")
        operations.append(operation)
        for reason in reasons:
            findings.append({"id": "operation:" + ident + ":" + reason, "severity": "review",
                             "capability": caps[0] if caps else None,
                             "operation": ident, "reason": reason})
    summaries = []
    for name in sorted({r["capability"] for r in rows} | {c["capability"] for c in controls}):
        a = [r for r in attributes if r["capability"] == name]
        c = [r for r in controls if r["capability"] == name]
        o = [r for r in operations if name in r["capabilities"] and not r["reference_only"]]
        jobs = {job: profile.job_discovery.get(job, "not_scanned")
                for job, group in _V2_SELECTIVE_JOBS.items() if group == name}
        summaries.append({"capability": name, "attributes": len(a),
                          "read_status": dict(Counter(r["status"] for r in a)),
                          "controls": len(c), "enabled_controls": sum(r["enabled"] for r in c),
                          "locally_verified_controls": sum(r["physical_evidence"] == "local_verified" for r in c),
                          "operations": len(o), "tested_operations": sum(r["tested"] for r in o),
                          "job_status": jobs,
                          "advertised_jobs": sorted(set(jobs) & vehicle.advertised_capabilities),
                          "impaired_jobs": sorted(set(jobs) & vehicle.impaired_capabilities),
                          "attention": sum(r.get("capability") == name for r in findings)})
    if not vehicle.model_family:
        findings.append({"id": "vehicle:model_family", "severity": "review", "reason": "model_family_unknown"})
    from .freshness import capture_coverage
    return {"operations": operations, "capability_summary": summaries,
            "job_capture_coverage": capture_coverage(vehicle),
            "findings": findings,
            "api_job_status": {job: profile.job_discovery.get(job, "not_scanned") for job in _V2_SELECTIVE_JOBS},
            "operation_counts": {"total": len(operations), "tested": sum(r["tested"] for r in operations),
                                 "active": sum(r["active"] for r in operations),
                                 "attention": sum(bool(r["attention"]) for r in operations),
                                 "historical_references": len(references)}}


def diagnostic_route_label(ident, registry):
    """Keep known discovery identifiers, never export custom route names."""
    if ident in registry.operations or ident in ("cariad.discovery.full", "cariad.selectivestatus.batch", INVENTORY_OPERATION):
        return ident
    if ident.startswith("cariad.discovery."):
        jobs = ident.removeprefix("cariad.discovery.").split("_")
        if jobs and all(job in _V2_SELECTIVE_JOBS for job in jobs):
            return ident
    if ident.startswith("mbb.discovery."):
        from .legacy_read_mappings import ROUTES
        if ident.removeprefix("mbb.discovery.") in ROUTES:
            return ident
    return "custom_or_discovery_route"


def diagnostic_capability_summary(vehicle, profile, base_registry, auth):
    """Safe diagnostic projection of the same capability model as the dashboard.

    No nickname, user route, VIN, payload, setting values or custom identifiers.
    Catalog compatibility, current command eligibility and physical evidence
    remain independent. This is a read-only computation from current state.
    """
    from .control_resolution import control_decision
    report = build_status_report(vehicle, profile)
    known = base_registry.capabilities
    summaries = [row for row in report["capability_summary"] if row["capability"] in known]
    controls = []
    for capability, definition in known.items():
        for action in definition.get("control", {}):
            decision = control_decision(vehicle, profile, auth, capability, action)
            operation = decision["operation"]
            controls.append({
                "capability": capability, "action": action,
                "binding_status": decision["status"], "reason": decision.get("reason"),
                "eligible": operation is not None,
                "operation": diagnostic_route_label(operation, base_registry) if operation else None,
                "physical_evidence": profile.control_results.get(operation, "not_tested") if operation else "not_tested",
            })
    for row in summaries:
        actions = [item for item in controls if item["capability"] == row["capability"]]
        row["enabled_controls"] = sum(item["eligible"] for item in actions)
        row["locally_verified_controls"] = sum(item["binding_status"] == "local_verified" for item in actions)
    operations = [
        {key: item.get(key) for key in ("operation", "family", "method", "applicability",
            "tested", "http_status", "schema", "physical", "last_command_state",
            "active", "job_evidence", "fields_truncated")}
        for item in report["operations"] if item["operation"] in base_registry.operations or item["operation"] == INVENTORY_OPERATION
    ]
    return {
        "capabilities": summaries,
        "controls": controls,
        "operations": operations,
        "job_capture_coverage": {
            job: data for job, data in report["job_capture_coverage"].items()
            if job in _V2_SELECTIVE_JOBS or job == "unclassified"
        },
        "operation_counts": {"total": len(operations),
                             "tested": sum(bool(row["tested"]) for row in operations),
                             "active": sum(bool(row["active"]) for row in operations),
                             "scope": "built_in_operations_and_inventory"},
        "engineering_operation_counts": report["operation_counts"],
    }
