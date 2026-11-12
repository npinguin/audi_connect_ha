"""Canonical diagnostic projection and explicitly retired pilot entity identities."""
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
    """Match exact historical V3-only identity suffix and a valid VIN prefix."""
    if not isinstance(unique_id, str):
        return False
    vin, separator, key = unique_id.partition("_sensor_")
    return bool(separator and len(vin) == 17 and vin.isalnum() and key in retired_sensor_keys())


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
    valid = [(a, vehicle.readings[a]) for a in sources
             if a in vehicle.readings and vehicle.readings[a].get("value") is not None]
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
               "disabled_by": getattr(disabled, "value", None)}
        if key is None:
            suffix = uid.split("_", 1)[-1] if isinstance(uid, str) else ""
            row["key_fingerprint"] = hashlib.sha256(suffix.encode()).hexdigest()[:16]
        rows.append(row)
    report.update(registry_available=True, registered=len(entries), counts=dict(counts),
                  rows=rows[:250], truncated=len(rows)>250)
    return report
