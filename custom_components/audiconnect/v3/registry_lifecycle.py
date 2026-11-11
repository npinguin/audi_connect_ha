"""Reversible visibility migration from historical V2 to minimal V3 entities.

Never delete a HA entity/device. Only restore entities that we disabled and
never rewrite user-disabled entries. One config entry owns its own record.
"""
from __future__ import annotations

from typing import Any
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

_KEEP = frozenset({
    "_climate_climatisation",
    "_sensor_cloud_last_successful_poll",
    "_sensor_vehicle_data_age",
    "_sensor_v3_climate_capability",
    "_sensor_v3_poll_status",
    "_button_v3_refresh_cloud",
})


async def async_apply_v3_entity_visibility(
    hass: Any, entry: Any, enabled: bool
) -> None:
    store = Store(hass, 1, f"audiconnect_v3_{entry.entry_id}_hidden_entities")
    data = await store.async_load() or {}
    if not isinstance(data, dict):
        data = {}
    recorded = set(data.get("entity_ids", []))
    registry = er.async_get(hass)

    if not enabled:
        for entity_id in recorded:
            current = registry.async_get(entity_id)
            if current is not None and current.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity_id, disabled_by=None)
        await store.async_save({"entity_ids": []})
        return

    # V3 may recover historical V2 unique IDs after per-vehicle discovery.
    # Keep only identifiers with verified read-only evidence; never expose unknowns.
    active_ids: set[str] = set()
    engine = getattr(getattr(entry, "runtime_data", None), "v3", None)
    if engine is not None and hasattr(engine, "profiles"):
        from .historical_catalog import ATTRIBUTES
        for vin, profile in engine.profiles.items():
            vehicle = engine.vehicles.get(vin)
            for ident in profile.attribute_routes:
                descriptor = ATTRIBUTES.get(ident)
                if vehicle is None or ident not in vehicle.readings or not descriptor:
                    continue
                if descriptor["platform"] in ("sensor", "binary_sensor"):
                    active_ids.add(f'{vin}_{descriptor["platform"]}_{descriptor["entity_key"]}')
            # Control entities are restored ONLY after real-car verification;
            # historical V2 registry entries remain hidden before that.
            from .entities import CONTROL_BUTTONS
            for button_key, _name, _icon, cap, action in CONTROL_BUTTONS:
                if engine.control_enabled(vehicle.vin, action, cap):
                    active_ids.add(f"{vin}_button_{button_key}")
            if (engine.control_enabled(vehicle.vin, "start") and
                engine.control_enabled(vehicle.vin, "stop")):
                active_ids.add(f"{vin}_switch_climate_quick_control")
            if (engine.control_enabled(vehicle.vin, "lock", "access") or
                engine.control_enabled(vehicle.vin, "unlock", "access")):
                active_ids.add(f"{vin}_lock_lock")
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id in active_ids or any(entity.unique_id.endswith(suffix) for suffix in _KEEP):
            # Previously hidden by this V3 migration? Restore only that.
            if entity.entity_id in recorded and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity.entity_id, disabled_by=None)
                recorded.discard(entity.entity_id)
            continue
        if entity.disabled_by is None:
            registry.async_update_entity(
                entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
            )
            recorded.add(entity.entity_id)
    await store.async_save({"entity_ids": sorted(recorded)})
