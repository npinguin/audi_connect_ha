"""Canonical diagnostic projection and explicitly retired pilot entity identities."""
from __future__ import annotations

CORE_STATUS_KINDS = ("cloud", "age", "freshness")
RETIRED_SENSOR_KEYS = frozenset({"v3_climate_capability", "v3_poll_status"})


def retired_pilot_entity(unique_id: str) -> bool:
    """Match exact historical V3-only identity suffix and a valid VIN prefix."""
    if not isinstance(unique_id, str):
        return False
    vin, separator, key = unique_id.partition("_sensor_")
    return bool(separator and len(vin) == 17 and vin.isalnum() and key in RETIRED_SENSOR_KEYS)


def account_cloud_refresh_vin(vehicles):
    """Use one stable existing VIN identity per account, preserving single-car IDs."""
    return next((vin for vin in sorted(vehicles)
                 if getattr(vehicles[vin], "inventory_present", True)), None)
