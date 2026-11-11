"""Audi V2/V3 runtime switches preserve entity identity and HA presentation.

Only the migration's OWN previously disabled integration entities are restored.
Unimplemented V3 values may be unavailable, never given new identifiers.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace as NS

from homeassistant.helpers import entity_registry as er

from custom_components.audiconnect.audi_entity import entity_unique_id
from custom_components.audiconnect.v3.attribute_contracts import contract_for
from custom_components.audiconnect.v3.entities import V3ReadOnlySensor
from custom_components.audiconnect.v3.vehicle import V3Vehicle
from custom_components.audiconnect.v3 import registry_lifecycle as lifecycle


class MemoryStore:
    state = {}

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        return dict(self.state.get(self.key, {}))

    async def async_save(self, data):
        self.state[self.key] = dict(data)


def test_registry_switch_never_disables_existing_entities(monkeypatch):
    MemoryStore.state = {
        "audiconnect_v3_abc_hidden_entities": {
            "entity_ids": [
                "sensor.old_v2_mileage", "sensor.user_disabled",
                "sensor.other_account"
            ],
        },
    }
    registry = NS(entries={
        "sensor.old_v2_mileage": NS(
            entity_id="sensor.old_v2_mileage",
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        ),
        "sensor.user_disabled": NS(
            entity_id="sensor.user_disabled",
            disabled_by=er.RegistryEntryDisabler.USER,
        ),
        "sensor.still_working": NS(
            entity_id="sensor.still_working", disabled_by=None,
        ),
        "sensor.other_account": NS(
            entity_id="sensor.other_account",
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        ),
    }, updates=[])

    def get(entity_id):
        return registry.entries.get(entity_id)

    def update(entity_id, *, disabled_by):
        assert disabled_by is None, "V3 must never disable a historical V2 entity"
        registry.entries[entity_id].disabled_by = disabled_by
        registry.updates.append(entity_id)

    registry.async_get = get
    registry.async_update_entity = update
    monkeypatch.setattr(lifecycle, "Store", MemoryStore)
    monkeypatch.setattr(lifecycle.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(lifecycle.er, "async_entries_for_config_entry",
                        lambda _registry, _entry: [
                            registry.entries[k] for k in (
                                "sensor.old_v2_mileage", "sensor.user_disabled",
                                "sensor.still_working",
                            )
                        ])
    entry = NS(entry_id="abc")
    asyncio.run(lifecycle.async_apply_v3_entity_visibility(None, entry, True))
    asyncio.run(lifecycle.async_apply_v3_entity_visibility(None, entry, False))
    assert registry.updates == ["sensor.old_v2_mileage"]
    assert registry.entries["sensor.old_v2_mileage"].disabled_by is None
    assert registry.entries["sensor.user_disabled"].disabled_by == er.RegistryEntryDisabler.USER
    assert registry.entries["sensor.other_account"].disabled_by == er.RegistryEntryDisabler.INTEGRATION
    assert MemoryStore.state["audiconnect_v3_abc_hidden_entities"] == {"entity_ids": []}


def test_ha_entity_ids_survive_v2_to_v3_for_same_vehicle():
    car = V3Vehicle(vin="WAUZZZ4M0MD123456", name="Audi",
                    model="Q8", model_family="", country="DE")
    coordinator = NS(async_add_listener=lambda callback: None)
    for attr_id, entity_key in (
        ("stateOfCharge", "state_of_charge"),
        ("TOTAL_RANGE", "range"),
        ("UTC_TIME_AND_KILOMETER_STATUS", "mileage"),
    ):
        entity = V3ReadOnlySensor(
            coordinator, car,
            {"id": attr_id, "entity_key": entity_key, "capability": "vehicle_status"},
        )
        assert entity.unique_id == entity_unique_id(car, "sensor", entity_key)


def test_vehicle_telemetry_not_classified_as_integration_diagnostics():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"
    sensor = (root / "sensor.py").read_text().split("async def async_setup_entry", 1)[0]
    binary = (root / "binary_sensor.py").read_text().split("async def async_setup_entry", 1)[0]
    assert "entity_category=EntityCategory.DIAGNOSTIC" not in sensor
    assert "entity_category=EntityCategory.DIAGNOSTIC" not in binary
    assert "_attr_entity_category = EntityCategory.DIAGNOSTIC" in (
        root / "v3" / "entities.py"
    ).read_text()
    for key in ("mileage", "service_inspection_time", "service_inspection_distance",
                "oil_change_time", "oil_change_distance", "car_type",
                "active_charging_profile_name", "charging_timer_enabled_count"):
        assert contract_for(key).get("category") != "diagnostic"
    # Technical quota info remains in the HA Diagnostics section.
    assert "_attr_entity_category = EntityCategory.DIAGNOSTIC" in (
        root / "sensor.py"
    ).read_text()
