"""V3 capability dashboard: prove support is not invented from V2 routes."""

import json
from pathlib import Path

from custom_components.audiconnect.v3.capability_status import build_status_report
from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
from custom_components.audiconnect.v3.registry import CapabilityRegistry, VehicleContext
from custom_components.audiconnect.v3.vehicle import V3Vehicle

CATALOG = Path(__file__).resolve().parents[1] / "tests/fixtures/v3_climate_catalog.json"


def _fixture():
    registry = CapabilityRegistry(json.loads(CATALOG.read_text()))
    vehicle = V3Vehicle(
        vin="TESTVIN1234567890", name="My Audi", model="Audi Q8",
        model_family="q8", country="DE",
    )
    profile = DevelopmentProfile(
        registry, VehicleContext(auth="auth0", region="DE", model_family="q8"),
        cooldown_seconds=0,
    )
    return vehicle, profile


def test_all_v2_reference_routes_are_explicitly_unmigrated():
    car, profile = _fixture()
    report = build_status_report(car, profile)
    refs = [r for r in report["rows"] if r["source"] == "v2_reference_only"]
    assert len(refs) >= 20
    assert all(r["status"] == "known_v2_not_migrated" for r in refs)
    assert all(r["api_family"] == "cariad" and "{VIN}" in r["path"] for r in refs)
    assert report["counts"]["verified_working"] == 0
    assert "TESTVIN1234567890" not in json.dumps(report)


def test_discovery_status_and_path_are_independent_from_capability():
    car, profile = _fixture()
    route = "cariad.climate.status.batch"
    profile.record_status(
        "climate", route, http_status=200,
        schema_valid=True, fresh=False,
    )
    result = build_status_report(car, profile)
    matched = [x for x in result["rows"] if x["operation"] == route]
    assert matched and all(x["status"] == "readable_but_stale" for x in matched)
    assert all(x["api_family"] == "cariad" for x in matched)


def test_only_actual_extracted_attribute_counts_as_discovered():
    car, profile = _fixture()
    route = "cariad.climate.status.batch"
    profile.record_status(
        "climate", route, http_status=200,
        schema_valid=True, fresh=True,
    )
    car.climate_field = (
        "climatisation.climatisationStatus.value.climatisationState"
    )
    rows = [x for x in build_status_report(car, profile)["rows"]
            if x["operation"] == route]
    assert [r["status"] for r in rows].count("worked") == 1
    assert [r["status"] for r in rows].count("mapped_not_confirmed") == 1


def test_draft_selection_does_not_mark_control_as_working():
    car, profile = _fixture()
    route = "cariad.climate.start.stored"
    profile.save_candidate("climate", "start", route)
    report = build_status_report(car, profile)
    candidate = next(r for r in report["rows"] if r["operation"] == route)
    assert candidate["saved_candidate"] is True
    assert candidate["selected"] is False
    assert candidate["status"] == "not_tested"

def test_cockpit_does_not_confuse_http_success_with_physical_or_schema_proof():
    from custom_components.audiconnect.v3.api_observations import record_for, save_record
    car, profile = _fixture()
    route = "cariad.climate.start.stored"
    save_record(profile, route, record_for(family="cariad", method="POST", http_status=204,
                                          vin=car.vin, payload=None))
    profile.fast_bindings["climate.start"] = {"status": "catalog_matched", "operation": route}
    report = build_status_report(car, profile)
    item = next(o for o in report["operations"] if o["operation"] == route)
    assert item["tested"] and item["active"] and item["physical"] == "not_tested"
    assert "accepted_not_physically_verified" in item["attention"]
    action = next(c for c in report["control_actions"] if c["action"] == "start")
    assert action["enabled"] and action["physical_evidence"] == "not_verified"
    assert len(report["operations"]) == len({o["operation"] for o in report["operations"]})


def test_cockpit_exposes_oil_type_issue_and_schema_fields():
    from datetime import UTC, datetime
    from custom_components.audiconnect.v3.attribute_runtime import observe_read_only
    from custom_components.audiconnect.v3.api_observations import record_for, save_record
    car, profile = _fixture()
    now = datetime.now(UTC)
    payload = {"oilLevel": {"oilLevelStatus": {"value": {
        "value": True, "carCapturedTimestamp": now.isoformat()}}}}
    observe_read_only(car, profile, payload, now)
    route = "cariad.climate.status.batch"
    save_record(profile, route, record_for(family="cariad", method="GET", http_status=207,
                                          vin=car.vin, payload=payload))
    report = build_status_report(car, profile)
    assert any(f["reason"] == "boolean_oil_level_use_binary" for f in report["findings"])
    operation = next(o for o in report["operations"] if o["operation"] == route)
    assert operation["partial_http"]
    assert any(f["mapping"] == "derived_binary" for f in operation["fields"])


def test_diagnostic_jobs_follow_canonical_capability_ownership():
    from custom_components.audiconnect.v3.historical_catalog import INVENTORY
    from custom_components.audiconnect.v3.capability_status import _V2_SELECTIVE_JOBS
    assert _V2_SELECTIVE_JOBS == {row["id"]: row["capability"] for row in INVENTORY["jobs"]}
    assert _V2_SELECTIVE_JOBS["access"] == "access"
    assert _V2_SELECTIVE_JOBS["vehicleHealthInspection"] == "service"


def test_discovery_coverage_matches_dashboard_for_derived_and_invalid_attributes():
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from custom_components.audiconnect.v3.read_discovery import user_progress
    car, profile = _fixture()
    now = datetime.now(UTC).isoformat()
    # Runtime-derived data need not have a separate persisted GET observation.
    car.readings["stateOfCharge"] = {"value": 75, "captured": now}
    profile.attribute_evidence["stateOfCharge"] = {"status": "readable_but_stale"}
    car.readings["remainingClimatisationTime"] = {"value": -1, "captured": now}
    report = build_status_report(car, profile)
    auth = SimpleNamespace(uses_auth0=True, service=SimpleNamespace(_spin=None))
    progress = user_progress(car, profile, auth)
    summary = next(row for row in report["capability_summary"] if row["capability"] == "climate")
    assert progress["capabilities"]["climate"]["attribute_evidence"] == summary["read_status"]
    assert next(row for row in report["rows"] if row.get("attribute") == "stateOfCharge")["status"] == "verified"
