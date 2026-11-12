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
