"""Preserve Home Assistant entity identity when switching Audi runtimes.

V2 and V3 own the SAME config entry and HA devices. Never disable historical
V2 entity-registry entries merely because a V3 API value is missing or old.
The entity may be temporarily unavailable until V3 provides a compatible
implementation, but its entity_id, unique_id, automations and history survive.

Undo only disablement previously recorded by this integration. Preserve user
disabled entities and never touch entities belonging to another config entry.
"""
from __future__ import annotations

from typing import Any
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from .product_contract import retired_pilot_entity, account_cloud_refresh_vin


async def async_apply_v3_entity_visibility(
    hass: Any, entry: Any, enabled: bool
) -> None:
    """Restore legacy V3-hidden entries; never hide them on runtime changes.

    The `enabled` argument remains for compatible callers (V2 and V3 setup).
    This migration is intentionally idempotent in either direction.
    """
    store = Store(hass, 1, f"audiconnect_v3_{entry.entry_id}_hidden_entities")
    data = await store.async_load() or {}
    if not isinstance(data, dict):
        data = {}

    recorded = set(data.get("entity_ids", []))
    registry = er.async_get(hass)
    owned = {
        entity.entity_id
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    for entity_id in recorded & owned:
        current = registry.async_get(entity_id)
        if (current is not None
                and current.disabled_by == er.RegistryEntryDisabler.INTEGRATION):
            registry.async_update_entity(entity_id, disabled_by=None)

    # Retire only source-proven V3 pilot IDs, never a historical V2 entity.
    # Keep registry records and user choices for rollback and manual recovery.
    runtime = getattr(entry, "runtime_data", None)
    engine = getattr(runtime, "v3", None)
    primary = account_cloud_refresh_vin(engine.vehicles) if engine is not None else None
    for entity_id in owned:
        current = registry.async_get(entity_id)
        unique_id = getattr(current, "unique_id", "")
        duplicate_refresh = bool(primary and unique_id.endswith("_button_v3_refresh_cloud")
                                 and unique_id[:-len("_button_v3_refresh_cloud")] in engine.vehicles
                                 and unique_id != f"{primary}_button_v3_refresh_cloud")
        if current is not None and (retired_pilot_entity(unique_id) or duplicate_refresh):
            if current.disabled_by is None:
                registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)

    # Once existing migration changes have been restored, never create fresh
    # disable records again. An unavailable entity is not a missing registry ID.
    await store.async_save({"entity_ids": []})
