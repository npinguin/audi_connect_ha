"""V3 Climate uses one HA entity and the shared V2 cloud/auth adapter."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.exceptions import HomeAssistantError

from custom_components.audiconnect.v3.climate import AudiV3Climate
from custom_components.audiconnect.v3.coordinator import AudiV3Coordinator
from custom_components.audiconnect.v3.registry import CapabilityRegistry
from custom_components.audiconnect.v3.runtime import V3Runtime, context_for

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "audiconnect" / "v3" / "climate.json"
VIN = "TESTVIN00000000001"


class FakeConnection:
    def __init__(self, succeed=True):
        self.calls = []
        self.succeed = succeed

    async def start_climate_control(self, vin, **kwargs):
        self.calls.append(("start", vin, kwargs))
        return self.succeed

    async def set_vehicle_climatisation(self, vin, active):
        self.calls.append(("stop", vin, active))
        return self.succeed


class FakeCoordinator:
    last_update_success = True

    def __init__(self, conn):
        self.account = NS(connection=conn)
        self.refresh_calls = 0

    async def async_request_refresh(self):
        self.refresh_calls += 1


def build(*, state="off", authorized=True, opts=None, stored_temp=22):
    car = NS(
        vin=VIN,
        _audi_service=NS(uses_auth0=True),
        has_capability=lambda cap: authorized if cap == "climatisation" else False,
        impaired_capabilities=frozenset(),
        climatisation_state=state,
        climatisation_target_temperature=stored_temp,
        car_type="hybrid",
        model_family="Q8",
        model_source="audi_long_name",
    )
    entry = NS(
        options=opts or {"runtime_version": "v3_climate"},
        data={"region": "EU"},
    )
    runtime = V3Runtime(CapabilityRegistry(json.loads(CATALOG.read_text())), entry)
    conn = FakeConnection()
    coordinator = FakeCoordinator(conn)
    entity = AudiV3Climate(coordinator, car, runtime)
    entity.async_write_ha_state = lambda: None
    return entity, conn, runtime, car, coordinator


def test_v3_climate_has_the_same_historic_entity_id_but_no_temp_slider():
    entity, _, _, _, _ = build()
    assert entity.unique_id == f"{VIN.lower()}_climate_climatisation"
    assert entity.supported_features & ClimateEntityFeature.TURN_ON
    assert entity.supported_features & ClimateEntityFeature.TURN_OFF
    assert not entity.supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert entity.current_temperature is None
    assert entity.hvac_mode is HVACMode.OFF


def test_readback_changes_mode_without_any_network_request():
    entity, conn, _, car, _ = build()
    assert entity.hvac_action is HVACAction.OFF
    car.climatisation_state = "cooling"
    assert entity.hvac_mode is HVACMode.HEAT_COOL
    assert entity.hvac_action is HVACAction.COOLING
    assert conn.calls == []


def test_unknown_cloud_readback_is_not_falsely_marked_off():
    entity, _, _, car, _ = build(state="error")
    assert entity.hvac_mode is None
    assert entity.hvac_action is None
    car.climatisation_state = None
    assert entity.hvac_mode is None


def test_climate_control_requires_reported_permission():
    entity, conn, _, _, _ = build(authorized=False)
    assert entity.supported_features == 0
    with pytest.raises(HomeAssistantError, match="not authorized"):
        asyncio.run(entity.async_turn_on())
    assert conn.calls == []


def test_default_start_calls_the_one_bodyless_existing_adapter():
    entity, conn, _, _, coordinator = build()
    asyncio.run(entity.async_turn_on())
    assert conn.calls == [("start", VIN, {})]
    assert coordinator.refresh_calls == 0  # Connection owns post-action notify.
    assert entity.extra_state_attributes["v3_last_command_outcome"] == "accepted_unconfirmed"


def test_explicit_vehicle_settings_passes_only_vehicle_reported_target():
    entity, conn, _, _, _ = build(
        opts={"v3_climate_start_route": "cariad.climate.start.vehicle_settings"}
    )
    asyncio.run(entity.async_turn_on())
    assert conn.calls == [("start", VIN, {"temp_c": 22})]


def test_vehicle_settings_rejects_unverified_target_before_network():
    entity, conn, _, _, _ = build(
        stored_temp=None,
        opts={"v3_climate_start_route": "cariad.climate.start.vehicle_settings"}
    )
    with pytest.raises(HomeAssistantError, match="stored target"):
        asyncio.run(entity.async_turn_on())
    assert conn.calls == []


def test_stop_calls_only_one_existing_adapter():
    entity, conn, _, car, coordinator = build(state="heating")
    asyncio.run(entity.async_turn_off())
    assert conn.calls == [("stop", VIN, False)]
    assert coordinator.refresh_calls == 0
    car.climatisation_state = "off"
    assert entity.hvac_mode is HVACMode.OFF


@pytest.mark.parametrize("method", ["async_turn_on", "async_turn_off"])
def test_command_failure_is_not_claimed_as_success(method):
    entity, conn, _, car, _ = build(state="heating" if method == "async_turn_off" else "off")
    conn.succeed = False
    with pytest.raises(HomeAssistantError, match="request failed"):
        asyncio.run(getattr(entity, method)())
    assert entity.extra_state_attributes["v3_last_command_outcome"] == "request_failed"
    assert len(conn.calls) == 1


def test_legacy_context_cannot_be_mistaken_for_modern_auth0():
    entity, _, runtime, car, _ = build()
    car._audi_service.uses_auth0 = False
    assert context_for(car, runtime.config_entry).auth == "legacy"
    assert runtime.resolve(car, "start")["operation"] == "mbb.climate.start"
    assert not entity._may_control  # V3 climate refuses an unreviewed legacy adapter.


def test_v3_coordinator_extends_existing_coordinator_not_parallel_polling():
    from custom_components.audiconnect.coordinator import AudiDataUpdateCoordinator
    assert issubclass(AudiV3Coordinator, AudiDataUpdateCoordinator)


def test_cached_reading_not_claimed_as_fresh_http_response():
    entity, _, runtime, car, _ = build()
    runtime.observe([NS(vehicle=car)])
    report = runtime.diagnostics([car])
    assert report[0]["read_evidence"]["cariad.climate.status.batch"][
        "cached_present"
    ] == 1
    assert report[0]["read_evidence"]["cariad.climate.status.batch"][
        "readable_observations"
    ] == 0
    assert VIN not in str(report)


def test_integration_option_does_not_replace_account_or_runtime_identity():
    from custom_components.audiconnect.v3.runtime import V3_DEFAULT, V3_ENABLED
    assert V3_DEFAULT == "v2" and V3_ENABLED == "v3_climate"
