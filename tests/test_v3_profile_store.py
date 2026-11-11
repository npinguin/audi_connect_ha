"""V3 development profile HA-storage roundtrips (no API calls)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.audiconnect.v3.development_profiles import (
    DevelopmentProfile, DevelopmentProfileError,
)
from custom_components.audiconnect.v3.profile_store import restore_profile
from custom_components.audiconnect.v3.registry import (
    CapabilityRegistry, VehicleContext,
)

PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/audiconnect/v3/climate.json"
)


def fresh():
    catalog = CapabilityRegistry(json.loads(PATH.read_text()))
    context = VehicleContext(auth="auth0", region="DE", model_family="q8")
    return catalog, context, DevelopmentProfile(catalog, context, cooldown_seconds=0)


def test_confirmed_route_is_recovered_without_dispatching_car_action():
    catalog, context, profile = fresh()
    route = "cariad.climate.start.stored"
    run = profile.begin_test("climate", "start", route, now=10)
    profile.observe_http(run.sequence, 200)
    profile.confirm(run.sequence, worked=True, inspected_vehicle=True, now=15)
    profile.choose_working("climate", "start", route)
    result = restore_profile(catalog, context, profile.snapshot(), cooldown_seconds=0)
    assert result.active["climate.start"] == route
    assert result.discovery._active is None
    assert result.discovery._sequence == 1


def test_unfinished_request_after_restart_blocks_new_action():
    catalog, context, profile = fresh()
    first = profile.begin_test(
        "climate", "start", "cariad.climate.start.stored", now=10
    )
    profile.observe_http(first.sequence, None)
    result = restore_profile(catalog, context, profile.snapshot(), cooldown_seconds=0)
    with pytest.raises(Exception, match="previous action"):
        result.begin_test("climate", "stop", "cariad.climate.stop", now=50)
    result.confirm(first.sequence, worked=False, inspected_vehicle=True, now=60)
    assert result.discovery._active is None


def test_unverified_selection_cannot_be_injected_via_storage():
    catalog, context, profile = fresh()
    data = profile.snapshot()
    data["active"] = {"climate.start": "cariad.climate.start.stored"}
    with pytest.raises(DevelopmentProfileError, match="confirm"):
        restore_profile(catalog, context, data)


def test_status_result_must_be_fresh_to_remain_selected():
    catalog, context, profile = fresh()
    operation = "cariad.climate.status.batch"
    profile.record_status(
        "climate", operation, http_status=200, schema_valid=True, fresh=True
    )
    profile.choose_working("climate", "status", operation)
    result = restore_profile(catalog, context, profile.snapshot())
    assert result.active["climate.status"] == operation
    data = profile.snapshot()
    data["read_evidence"][operation]["fresh"] = False
    with pytest.raises(DevelopmentProfileError, match="inconsistent"):
        restore_profile(catalog, context, data)


def test_custom_route_survives_snapshot_without_becoming_active():
    catalog, context, profile = fresh()
    ident = profile.add({
        "id": "user.climate.start.my_probe",
        "capability": "climate", "aspect": "start", "family": "cariad",
        "method": "POST",
        "path": "/vehicle/v1/vehicles/{VIN}/climatisation/start",
        "body": {"targetTemperature": 22},
    })
    result = restore_profile(catalog, context, profile.snapshot())
    assert ident in result.registry.operations
    assert not result.active


def test_disabled_start_is_restored_without_disabling_climate_status():
    catalog, context, profile = fresh()
    profile.disable("climate", "start")
    restored = restore_profile(catalog, context, profile.snapshot())
    assert "climate.start" in restored.discovery.disabled
    assert restored.registry.resolve(
        "climate", "status", context
    )["operation"] == "cariad.climate.status.batch"
