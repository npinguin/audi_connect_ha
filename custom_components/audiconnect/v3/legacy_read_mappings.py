"""Historical MBB read-only response mappings from the original V2 adapter.

MBB may omit vehicle capture clocks. A successful GET proves that a field is
readable, not that the car has recently refreshed it. Controls are excluded.
"""
from __future__ import annotations

ROUTES = {
    "charger": "/fs-car/bs/batterycharge/v1/{TYPE}/{COUNTRY}/vehicles/{VIN}/charger",
    "climater": "/fs-car/bs/climatisation/v1/{TYPE}/{COUNTRY}/vehicles/{VIN}/climater",
}
FIELDS: dict[str, tuple[str, str]] = {
    "stateOfCharge": ("charger", "charger.status.batteryStatusData.stateOfCharge.content"),
    "chargingState": ("charger", "charger.status.chargingStatusData.chargingState.content"),
    "actualChargeRate": ("charger", "charger.status.chargingStatusData.actualChargeRate.content"),
    "chargingPower": ("charger", "charger.status.chargingStatusData.chargingPower.content"),
    "chargeMode": ("charger", "charger.status.chargingStatusData.chargingMode.content"),
    "plugState": ("charger", "charger.status.plugStatusData.plugState.content"),
    "plugLockState": ("charger", "charger.status.plugStatusData.plugLockState.content"),
    "externalPower": ("charger", "charger.status.plugStatusData.externalPower.content"),
    "plugledColor": ("charger", "charger.status.plugStatusData.plugledColor.content"),
    "remainingChargingTime": ("charger", "charger.status.batteryStatusData.remainingChargingTime.content"),
    "hybridRange": ("charger", "charger.status.cruisingRangeStatusData.hybridRange.content"),
    "primaryEngineRange": ("charger", "charger.status.cruisingRangeStatusData.primaryEngineRange.content"),
    "secondaryEngineRange": ("charger", "charger.status.cruisingRangeStatusData.secondaryEngineRange.content"),
    "engineTypeFirstEngine": ("charger", "charger.status.cruisingRangeStatusData.engineTypeFirstEngine.content"),
    "engineTypeSecondEngine": ("charger", "charger.status.cruisingRangeStatusData.engineTypeSecondEngine.content"),
    "climatisationState": ("climater", "climater.status.climatisationStatusData.climatisationState.content"),
    "remainingClimatisationTime": ("climater", "climater.status.climatisationStatusData.remainingClimatisationTime.content"),
}


def variant_for(attribute: str) -> dict | None:
    item = FIELDS.get(attribute)
    if item is None:
        return None
    name, mapping = item
    return {
        "id": "mbb." + name + ".readonly",
        "family": "mbb", "method": "GET", "path": ROUTES[name],
        "response_paths": [mapping], "kind": "legacy",
    }
