"""Regression tests for the clean V3 engine, independent of V2 polling.

Only synthetic Audi API responses are used. Never contact a real vehicle.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.audiconnect.coordinator import AudiDataUpdateCoordinator
from custom_components.audiconnect.v3.coordinator_clean import V3CleanCoordinator
from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
from custom_components.audiconnect.v3.engine import V3Engine
from custom_components.audiconnect.v3.registry import CapabilityRegistry, VehicleContext
from custom_components.audiconnect.v3.transport import V3Response
from custom_components.audiconnect.v3.profile_store import restore_profile
from custom_components.audiconnect.v3.vehicle import V3Vehicle

CATALOG = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3/climate.json"
VIN = "WAUZZZ4M0MD123456"


class FakeAuth:
    country = "DE"
    uses_auth0 = True


class FakeTransport:
    def __init__(self, response_list):
        self._responses = list(response_list)
        self.calls = []
        self.request_count = 0
        self.remaining_calls = 100

    async def discover_vehicles(self):
        self.calls.append(("inventory",))
        return [{
            "vin": VIN,
            "nickname": "Test Audi",
            "vehicle": {
                "media": {"longName": "Audi Q8 TFSI e"},
                "classification": {"driveTrain": "PHEV"},
            },
        }]

    async def request(self, family, method, path, **kwargs):
        self.calls.append((family, method, path, kwargs))
        self.request_count += 1
        return self._responses.pop(0)


class FakeStore:
    def __init__(self):
        self.writes = []
        self.loads = 0
        self.records = {}

    async def async_load(self, catalog, contexts):
        self.loads += 1
        return {
            vin: (restore_profile(catalog, context, self.records[vin],
                                  cooldown_seconds=0)
                  if vin in self.records else
                  DevelopmentProfile(catalog, context, cooldown_seconds=0))
            for vin, context in contexts.items()
        }

    async def async_save(self, profiles):
        snapshot = {key: val.snapshot() for key, val in profiles.items()}
        self.writes.append(snapshot)
        self.records.update(snapshot)


def engine_for(*response_list):
    registry = CapabilityRegistry(json.loads(CATALOG.read_text()))
    transport = FakeTransport(response_list)
    storage = FakeStore()
    engine = V3Engine(
        SimpleNamespace(), SimpleNamespace(entry_id="example"),
        registry, auth=FakeAuth(), transport=transport, storage=storage,
    )
    return engine, transport, storage


def status(*, http=200, value="off", captured=True):
    payload = {
        "climatisation": {
            "climatisationStatus": {
                "value": {"climatisationState": value}
            }
        }
    }
    if captured:
        payload["climatisation"]["climatisationStatus"]["value"][
            "carCapturedTimestamp"
        ] = datetime.now(UTC).isoformat()
    return V3Response(http, payload, datetime.now(UTC), 100)


def test_no_v2_coordinator_inheritance():
    assert not issubclass(V3CleanCoordinator, AudiDataUpdateCoordinator)


@pytest.mark.asyncio
async def test_first_v3_poll_discovers_one_car_and_learns_climate_get():
    engine, transport, store = engine_for(status())
    cars = await engine.poll()
    assert len(cars) == 1
    assert cars[0].vin == VIN
    assert cars[0].model_family == "q8"
    assert cars[0].climate_state == "off"
    assert store.loads == 1
    assert len(store.writes) == 1
    assert transport.calls[0] == ("inventory",)
    assert len([c for c in transport.calls if len(c) > 1]) == 1
    assert all(c[1] == "GET" for c in transport.calls if len(c) > 1)
    assert engine.profiles[VIN.lower()].active["climate.status"] == (
        "cariad.climate.status.batch"
    )
    assert "AudiAccount" not in type(engine).__name__


@pytest.mark.asyncio
async def test_stale_status_is_readable_but_not_proven_fresh():
    engine, _, _ = engine_for(status(captured=False))
    await engine.poll()
    profile = engine.profiles[VIN.lower()]
    assert profile.read_results["cariad.climate.status.batch"]["outcome"] == (
        "readable_but_stale"
    )
    assert "climate.status" not in profile.active


@pytest.mark.asyncio
async def test_rate_limit_is_inconclusive_and_no_auto_retry_post():
    engine, transport, _ = engine_for(status(http=429, value="invalid"))
    await engine.poll()
    assert transport.request_count == 1
    assert engine.profiles[VIN.lower()].read_results[
        "cariad.climate.status.batch"
    ]["outcome"] == "inconclusive"
    assert all(c[1] == "GET" for c in transport.calls if len(c) > 1)


@pytest.mark.asyncio
async def test_start_test_requires_human_result_before_normal_control():
    engine, transport, store = engine_for(
        status(),
        V3Response(202, {"data": {"requestID": "synthetic"}}, datetime.now(UTC)),
    )
    await engine.poll()
    assert not engine.control_enabled(VIN, "start")
    attempt = await engine.test_action(
        VIN, "start", "cariad.climate.start.stored"
    )
    assert attempt["transport"] == "accepted_unconfirmed"
    assert not engine.control_enabled(VIN, "start")
    assert transport.request_count == 2
    assert transport.calls[-1][1] == "POST"
    assert transport.calls[-1][3]["explicit_action"] is True
    await engine.review_action(VIN, attempt["sequence"], "worked")
    assert engine.control_enabled(VIN, "start")
    assert len(store.writes) >= 3


@pytest.mark.asyncio
async def test_unreviewed_vehicle_settings_control_never_substitutes_bodyless():
    engine, transport, _ = engine_for(status())
    await engine.poll()
    with pytest.raises(ValueError, match="not implemented"):
        await engine.test_action(
            VIN, "start", "cariad.climate.start.vehicle_settings"
        )
    assert transport.request_count == 1
    assert engine.profiles[VIN.lower()].discovery._active is None


@pytest.mark.asyncio
async def test_import_diagnostics_isolated_and_contains_no_vehicle_identity():
    engine, _, _ = engine_for(status())
    await engine.poll()
    exported = json.dumps(engine.diagnostics())
    assert VIN not in exported
    assert "Bearer" not in exported
    assert "requestID" not in exported


def test_nickname_cannot_spoof_manufacturer_q8_context():
    car = V3Vehicle.from_graphql({
        "vin": VIN, "nickname": "Q8",
        "vehicle": {"media": {"longName": "Audi A5"}},
    }, "DE")
    assert car.model_family == ""
    assert car.climate_supported is None


@pytest.mark.asyncio
async def test_later_vehicle_restores_saved_candidate():
    engine, transport, store = engine_for(status())
    await engine.poll()
    late = "WAUZZZ4M0MD123457"
    old = DevelopmentProfile(engine.registry, VehicleContext(
        auth="auth0", region="DE", vehicle_type="phev", model_family="q8",
    ), cooldown_seconds=0)
    old.save_candidate("climate", "start", "cariad.climate.start.stored")
    store.records[late.lower()] = old.snapshot()
    async def later():
        return [{"vin": late, "vehicle": {
            "media": {"longName": "Audi Q8 TFSI e"},
            "classification": {"driveTrain": "PHEV"},
        }}]
    transport.discover_vehicles = later
    await engine.discover()
    assert engine.profiles[late.lower()].draft_selected["climate.start"] == (
        "cariad.climate.start.stored"
    )


@pytest.mark.asyncio
async def test_stale_status_can_try_distinct_get_candidate():
    engine, transport, _ = engine_for(
        status(captured=False), status(value="heating"),
    )
    engine.registry.operations["cariad.climate.status.probe"]["path"] += "&detail=1"
    await engine.poll()
    assert len([c for c in transport.calls if len(c) > 1]) == 2
    assert engine.profiles[VIN.lower()].active["climate.status"] == (
        "cariad.climate.status.probe"
    )
