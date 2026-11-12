"""Preserve Home Assistant entity identity when switching Audi runtimes.

V2 and V3 own the SAME config entry and HA devices. Never disable historical
V2 entity-registry entries merely because a V3 API value is missing or old.
The entity may be temporarily unavailable until V3 provides a compatible
implementation, but its entity_id, unique_id, automations and history survive.

Undo only recorded V2 disablement. Explicit retired V3-only pilot identities
and duplicate account cloud actions are the sole retirement exceptions.
Preserve registry history, user choices and account ownership.
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
    primary = None
    duplicate_ids = set(data.get("retired_duplicate_cloud_refresh", []))
    if engine is not None:
        # Retain the account anchor over reload and inventory reordering. If
        # the anchor disappears, choose a present vehicle only during setup.
        primary = getattr(engine, "cloud_refresh_vin", None)
        if primary is None:
            saved = data.get("cloud_refresh_anchor")
            primary = (saved if saved in engine.vehicles and
                       engine.vehicles[saved].inventory_present else
                       account_cloud_refresh_vin(engine.vehicles))
            engine.cloud_refresh_vin = primary

    for entity_id in owned:
        current = registry.async_get(entity_id)
        unique_id = getattr(current, "unique_id", "")
        suffix = "_button_v3_refresh_cloud"
        old_vin = unique_id[:-len(suffix)] if unique_id.endswith(suffix) else ""
        duplicate_refresh = bool(primary and len(old_vin) == 17 and old_vin.isalnum()
                                 and old_vin != primary)
        if current is not None and (retired_pilot_entity(unique_id) or duplicate_refresh):
            if current.disabled_by is None:
                registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
                if duplicate_refresh:
                    duplicate_ids.add(unique_id)
        elif (primary and unique_id == f"{primary}{suffix}" and unique_id in duplicate_ids
              and current.disabled_by == er.RegistryEntryDisabler.INTEGRATION):
            registry.async_update_entity(entity_id, disabled_by=None)
            duplicate_ids.discard(unique_id)

    # Historical V2 disable records are cleared; the cloud anchor is local
    # account metadata. Never save pilot retirement as a V2 restore candidate.
    result = {"entity_ids": []}
    if primary or data.get("cloud_refresh_anchor"):
        result["cloud_refresh_anchor"] = primary or data["cloud_refresh_anchor"]
    if duplicate_ids:
        result["retired_duplicate_cloud_refresh"] = sorted(duplicate_ids)
    await store.async_save(result)
