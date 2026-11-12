"""Canonical HA product identity, source resolution and presentation policy."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from .historical_catalog import ATTRIBUTES, ALIAS_OF

CORE_STATUS_KINDS = ("cloud", "age", "freshness")
@lru_cache(maxsize=1)
def product_inventory():
    return json.loads(Path(__file__).with_name("product_entities.json").read_text())


def retired_sensor_keys():
    return frozenset(product_inventory()["retired_v3_sensors"])



def retired_pilot_entity(unique_id: str) -> bool:
    """Match exact retired pilot sensor identities."""
    if not isinstance(unique_id, str):
        return False
    vin, separator, suffix = unique_id.partition("_")
    if not separator or len(vin) != 17 or not vin.isalnum():
        return False
    if suffix.startswith("sensor_"):
        return suffix.removeprefix("sensor_") in retired_sensor_keys()
    if suffix.startswith("button_"):
        return suffix.removeprefix("button_") in product_inventory().get("retired_legacy_buttons", ())
    return False


def account_cloud_refresh_vin(vehicles):
    """Use one stable existing VIN identity per account, preserving single-car IDs."""
    return next((vin for vin in sorted(vehicles)
                 if getattr(vehicles[vin], "inventory_present", True)), None)


def projection_descriptor(attribute):
    """Only historical product properties and explicit local extensions project.

    Raw preferredChargeMode is a configuration source for select.charge_mode,
    not the actual in-progress chargeMode shown by sensor.charging_mode.
    """
    if attribute.get("local"):
        return attribute
    ident = attribute["id"]
    if ident in product_inventory()["raw_only_attributes"]:
        return None
    canonical = ATTRIBUTES.get(ALIAS_OF.get(ident, ident), attribute)
    key = f'{canonical["platform"]}.{canonical["entity_key"]}'
    return canonical if key in product_inventory()["entities"] else None


def projection_reading(vehicle, attribute):
    """Resolve only declared same-semantic historical aliases, never by order."""
    from .attribute_runtime import _capture_in_utc
    ident = attribute["id"]
    canonical = ALIAS_OF.get(ident, ident)
    sources = [canonical, *sorted(a for a, target in ALIAS_OF.items() if target == canonical)]
    key = attribute.get("entity_key") or ATTRIBUTES.get(canonical, {}).get("entity_key")
    if key == "range":
        sources.append("hybridRange")
    if key == "state_of_charge":
        sources.extend(electric_soc_sources(vehicle))
    if key == "tank_level":
        sources.extend(("fuelLevelFromEngine",))
    valid = [(a, vehicle.readings[a]) for a in sources
             if a in vehicle.readings and (vehicle.readings[a].get("value") is not None
                                         or vehicle.readings[a].get("status") == "invalid_value")]
    if not valid:
        return ident, vehicle.readings.get(ident)
    def score(item):
        stamp = _capture_in_utc(item[1].get("captured"))
        return (stamp.timestamp() if stamp is not None else -1,
                item[0] == canonical)
    return max(valid, key=score)


def entity_key(unique_id, entry_id):
    """Return a product contract key, never a raw VIN or user-defined name."""
    if unique_id == f"{entry_id}_api_requests_remaining":
        return "sensor.api_requests_remaining"
    if not isinstance(unique_id, str) or len(unique_id) < 20:
        return None
    vin, sep, suffix = unique_id.partition("_")
    if not sep or len(vin) != 17 or not vin.isalnum():
        return None
    for platform in ("binary_sensor", "device_tracker", "sensor", "button", "switch",
                     "number", "select", "climate", "lock"):
        prefix = platform + "_"
        if not suffix.startswith(prefix):
            continue
        key = suffix[len(prefix):]
        if platform in ("sensor", "binary_sensor") and key.startswith("v3_custom_"):
            return f"{platform}.custom_attribute"
        if platform == "number" and re.fullmatch(r"charge_profile_[0-9]+_target_soc", key):
            return "number.charge_profile_{profile_id}_target_soc"
        candidate = f"{platform}.{key}"
        if candidate in product_inventory()["entities"]:
            return candidate
        if platform == "sensor" and key in retired_sensor_keys():
            return candidate
        if platform == "button" and key in product_inventory().get("retired_legacy_buttons", ()):
            return candidate
        return None
    return None


def entity_projection_report(engine):
    """Separate registry records, offered entities and HA state availability.

    No entity IDs, unique IDs, VINs, names or state values leave this function.
    Unknown registry keys get a suffix fingerprint for a later exact migration.
    """
    from collections import Counter
    projected = {uid for group in engine.projected_entities.values() for uid in group}
    report = {"projected": len(projected), "registry_available": False, "rows": []}
    if not hasattr(engine.hass, "states") or not hasattr(engine.hass, "data"):
        return report
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(engine.hass)
    entries = er.async_entries_for_config_entry(registry, engine.entry.entry_id)
    counts = Counter()
    rows = []
    for entry in entries:
        uid = entry.unique_id
        key = entity_key(uid, engine.entry.entry_id)
        platform = entry.domain
        offered = uid in projected
        state = engine.hass.states.get(entry.entity_id)
        state_present = state is not None
        unavailable = state_present and state.state in ("unavailable", "unknown")
        disabled = entry.disabled_by
        status = ("disabled" if disabled is not None else
                  "projected" if offered and state_present and not unavailable else
                  "projected_unavailable" if offered else
                  "registered_not_projected")
        counts[status] += 1
        row = {"platform": platform, "contract_key": key or "unrecognized_registry_key",
               "status": status, "offered_by_runtime": offered, "state_present": state_present,
               "disabled_by": getattr(disabled, "value", None),
               "entity_category": getattr(getattr(entry, "entity_category", None), "value", None),
               "hidden_by": getattr(getattr(entry, "hidden_by", None), "value", None),
               "original_icon": getattr(entry, "original_icon", None),
               "expected_category": canonical_entity_category(key) if key in product_inventory()["entities"] else None,
               "category_drift": bool(key in product_inventory()["entities"] and
                   getattr(getattr(entry, "entity_category", None), "value", None) != canonical_entity_category(key))}
        if key is None:
            suffix = uid.split("_", 1)[-1] if isinstance(uid, str) else ""
            row["key_fingerprint"] = hashlib.sha256(suffix.encode()).hexdigest()[:16]
        rows.append(row)
    report.update(registry_available=True, registered=len(entries), counts=dict(counts),
                  rows=rows[:250], truncated=len(rows)>250)
    return report

def compatibility_hidden(vehicle, key):
    """Hide redundant representations only with supporting semantic evidence."""
    readings = getattr(vehicle, "readings", {})
    if key in product_inventory()["default_hidden_compatibility"]:
        if key == "sensor.hybrid_range":
            return any(readings.get(x, {}).get("value") is not None for x in ("TOTAL_RANGE", "range"))
        return True
    if key == "sensor.oil_level":
        return readings.get("OIL_LEVEL_DIPSTICKS_PERCENTAGE", {}).get("reason") == "boolean_oil_level_use_binary"
    for role in ("primary", "secondary"):
        if key != "sensor." + role + "_engine_range_percent":
            continue
        if engine_role(vehicle, role) == "electric":
            return readings.get("stateOfCharge", {}).get("value") is not None
        if engine_role(vehicle, role) == "fuel":
            # Never assume generic engine SOC means fuel; require explicit fuel value.
            engine_fuel = readings.get(role + "EngineFuelLevel", {}).get("value")
            engine_percent = readings.get(role + "EngineRangePercent", {}).get("value")
            return type(engine_fuel) in (int, float) and engine_fuel == engine_percent and any(
                readings.get(x, {}).get("value") is not None for x in ("TANK_LEVEL_IN_PERCENTAGE", "tank_level"))
    return False


def canonical_entity_category(key):
    """Resolve presentation from the authoritative product/metadata contracts."""
    from .attribute_contracts import binary_contract_for, contract_for

    definition = product_inventory()["entities"].get(key, {})
    platform, _, entity = key.partition(".")
    if definition.get("metadata_contract"):
        if platform == "binary_sensor":
            return binary_contract_for(entity).get("category")
        if platform == "sensor":
            return contract_for(entity).get("category")
    return definition.get("category")

def electric_soc_sources(vehicle):
    readings = vehicle.readings
    return [role + "EngineRangePercent" for role in ("primary", "secondary")
            if readings.get(role + "_engine_type", {}).get("value") == "electric"]


def engine_role(vehicle, role):
    value = vehicle.readings.get(role + "_engine_type", {}).get("value")
    return "electric" if value == "electric" else "fuel" if value in (
        "gasoline", "diesel", "petrol", "cng", "lpg"
    ) else None


def canonical_entity_name(key, vehicle=None):
    """Integration-owned product label; source, lifecycle and API family are metadata."""
    from .attribute_contracts import binary_contract_for, contract_for
    definition = product_inventory()["entities"].get(key)
    if definition is None:
        return None
    platform, _, entity = key.partition(".")
    if vehicle is not None and entity in ("primary_engine_range", "secondary_engine_range"):
        role = engine_role(vehicle, entity.split("_", 1)[0])
        if role:
            return "Electric range" if role == "electric" else "Fuel range"
    if definition.get("name"):
        return definition["name"]
    if platform == "sensor":
        return contract_for(entity).get("name")
    if platform == "binary_sensor":
        return binary_contract_for(entity).get("name")
    return None


def stateful_controls():
    return product_inventory()["stateful_controls"]


def stateful_reading(vehicle, key):
    """Shared operational state normalization, independent of write support."""
    from .vehicle import charging_active
    definition = stateful_controls()[key]
    row = vehicle.readings.get(definition["attribute"], {})
    value = row.get("value")
    state = charging_active(value) if key == "charging" else value if type(value) is bool else None
    return row, state if row.get("status") in ("verified", "readable_but_stale") else None


def stateful_control_supported(engine, vehicle, key):
    definition = stateful_controls()[key]
    _, value = stateful_reading(vehicle, key)
    return value is not None and all(engine.control_enabled(vehicle.vin, definition[action], definition["capability"])
                                     for action in ("on", "off"))


def superseded_control_button(engine, vehicle, key):
    return any(key == "button." + button and stateful_control_supported(engine, vehicle, control)
               for control, definition in stateful_controls().items()
               for button in definition["compatibility_buttons"])
