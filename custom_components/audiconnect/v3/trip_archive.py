"""Private, bounded per-entry archive of normalized completed CARIAD trips.

Never store raw OEM payloads, coordinates, trip IDs or credentials here.
The archive survives restart and rollback; it is not HA Recorder history.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping

from .trips import MAX_TRIP_HISTORY, _timestamp, _number

_NUMERIC = {
    "mileage": 2000000, "startMileage": 2000000, "overallMileage": 2000000,
    "averageSpeed": 350, "traveltime": 100000,
    "averageFuelConsumption": 100, "averageElectricEngineConsumption": 150,
    "totalElectricConsumption": 3000000, "totalFuelConsumption": 1000000,
    "zeroEmissionDistance": 2000000,
}
_UNITS = {
    "mileage": "km", "averageSpeed": "km/h", "traveltime": "min",
    "averageFuelConsumption": "L/100km", "averageElectricEngineConsumption": "kWh/100km",
    "totalElectricConsumption": "kWh", "totalFuelConsumption": "L",
    "zeroEmissionDistance": "km",
}


def clean_trip(row):
    """Revalidate stored and incoming rows; only completed modern trips."""
    if not isinstance(row, Mapping) or row.get("source") != "cariad_modern":
        return None
    if row.get("tripType") not in (None, "shortTerm"):
        return None
    stamp = _timestamp(row.get("timestamp"))
    if stamp is None:
        return None
    values = {key: _number(row, (key,), 0, limit) for key, limit in _NUMERIC.items()}
    if all(value is None for value in values.values()):
        return None
    vehicle_type = row.get("vehicleType")
    return {
        "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "tripType": "shortTerm", "vehicleType": vehicle_type if vehicle_type in
        ("hybrid", "phev", "electric", "combustion") else None,
        "source": "cariad_modern", "tripID": None, "units": dict(_UNITS), **values,
    }


def merge_history(*groups):
    """Prefer newer non-null fields on exact identity, never sum trip windows."""
    records = {}
    for group in groups:
        if not isinstance(group, list):
            continue
        for raw in group:
            row = clean_trip(raw)
            if row is None:
                continue
            key = (row["timestamp"], row["startMileage"], row["overallMileage"])
            previous = records.get(key, {})
            records[key] = {**row, **previous, **{k: v for k, v in row.items() if v is not None}}
    return sorted(records.values(), key=lambda row: row["timestamp"], reverse=True)[:MAX_TRIP_HISTORY]


class V3TripArchive:
    """Private HA storage, separate from evidence and configuration."""

    def __init__(self, hass, entry_id):
        from homeassistant.helpers.storage import Store
        self._store = Store(hass, 1, f"audiconnect_v3_{entry_id}_trips", private=True)
        self._lock = asyncio.Lock()

    async def _load(self):
        data = await self._store.async_load()
        if data is None:
            return {}
        if not isinstance(data, dict) or not isinstance(data.get("vehicles"), dict):
            raise ValueError("Invalid Audi trip archive")
        return data["vehicles"]

    async def restore(self, vehicles):
        async with self._lock:
            records = await self._load()
            for key, car in vehicles.items():
                car.trip_history = merge_history(records.get(key, []), car.trip_history)

    async def save(self, vehicles):
        async with self._lock:
            records = await self._load()
            updated = dict(records)
            for key, car in vehicles.items():
                if car.inventory_present and car.trip_history:
                    updated[key] = merge_history(records.get(key, []), car.trip_history)
            if updated != records:
                await self._store.async_save({"vehicles": updated})
