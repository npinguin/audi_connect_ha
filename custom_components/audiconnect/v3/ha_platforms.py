"""V3's nine Home Assistant platform entrypoints.

The root platform modules keep their original V2 behavior untouched apart
from one runtime-selector branch. This module and the V3 native entity
classes own every V3 platform; no V2 vehicle objects or business operations.
"""
from __future__ import annotations

from typing import Any

from .entities import (
    CONTROL_BUTTONS, V3ClimateEntity, V3ReadOnlyBinarySensor, V3TripSensor,
    V3ReadOnlySensor, V3StatusSensor, V3CloudRefreshButton,
    V3ControlButton, V3ClimateQuickSwitch, V3LockEntity,
    V3ParkedTracker, V3ChargeTargetNumber, V3ChargeModeSelect,
    V3LocationChargeTargetNumber, CLIMATE_SWITCHES, V3ClimateSettingSwitch,
)
from .historical_catalog import ATTRIBUTES


def setup(platform: str, entry: Any, async_add_entities: Any) -> None:
    """Forward exactly one V3 platform and watch new *proven* field discovery."""
    runtime = entry.runtime_data
    engine, coordinator = runtime.v3, runtime.coordinator
    if engine is None:
        raise ValueError("V3 platform forwarded without V3 engine")
    seen: set[str] = set()

    if platform == "sensor":
        async_add_entities([
            V3StatusSensor(coordinator, car, kind)
            for car in engine.vehicles.values()
            for kind in ("cloud", "age", "capability", "poll")
        ])
    elif platform == "button":
        async_add_entities([
            V3CloudRefreshButton(coordinator, car)
            for car in engine.vehicles.values()
        ])
    elif platform == "climate":
        async_add_entities([
            V3ClimateEntity(coordinator, car)
            for car in engine.vehicles.values()
        ])
        return
    elif platform == "device_tracker":
        # Keep the historical V2 tracker identifier. Location is only a
        # trusted last-parked sample; never imply active driving tracking.
        async_add_entities([
            V3ParkedTracker(coordinator, car)
            for car in engine.vehicles.values()
        ])
        return
    elif platform in ("number", "select"):
        for car in engine.vehicles.values():
            if platform == "number":
                async_add_entities([V3ChargeTargetNumber(coordinator, car)])
            else:
                async_add_entities([V3ChargeModeSelect(coordinator, car)])
        if platform == "select":
            return
    elif platform not in ("binary_sensor", "switch", "lock"):
        raise ValueError("Unknown Audi V3 Home Assistant platform")

    def add_verified() -> None:
        entities: list[Any] = []
        for car in engine.vehicles.values():
            vin = car.vin.lower()
            if platform in ("sensor", "binary_sensor"):
                if platform == "sensor":
                    for key in car.trips:
                        tag = f"{vin}:{key}"
                        if tag not in seen:
                            seen.add(tag)
                            entities.append(V3TripSensor(coordinator, car, key))
                for ident in car.readings:
                    descriptor = ATTRIBUTES.get(ident)
                    if not descriptor or descriptor["platform"] != platform:
                        continue
                    reading = car.readings.get(ident)
                    if not reading or not isinstance(
                        reading.get("value"), (str, int, float, bool)
                    ):
                        continue
                    tag = f'{vin}:{descriptor["entity_key"]}'
                    if tag in seen:
                        continue
                    seen.add(tag)
                    entity_type = (
                        V3ReadOnlySensor if platform == "sensor"
                        else V3ReadOnlyBinarySensor
                    )
                    entities.append(entity_type(coordinator, car, descriptor))
            elif platform == "button":
                for descriptor in CONTROL_BUTTONS:
                    key, _, _, capability, action = descriptor
                    tag = f"{vin}:{key}"
                    if tag not in seen and engine.control_enabled(
                        car.vin, action, capability
                    ):
                        seen.add(tag)
                        entities.append(V3ControlButton(coordinator, car, descriptor))
            elif platform == "number":
                for profile_id in [None, *[x["id"] for x in car.charging_profiles]]:
                    tag = f"{vin}:profile:{profile_id}"
                    if tag not in seen and car.charging_profiles:
                        seen.add(tag)
                        entities.append(V3LocationChargeTargetNumber(
                            coordinator, car, profile_id))
            elif platform == "switch":
                for descriptor in CLIMATE_SWITCHES:
                    key, reading, _ = descriptor
                    tag = f"{vin}:{key}"
                    if tag not in seen and reading in car.readings:
                        seen.add(tag)
                        entities.append(V3ClimateSettingSwitch(coordinator, car, descriptor))
                if (vin not in seen
                    and engine.control_enabled(car.vin, "start")
                    and engine.control_enabled(car.vin, "stop")):
                    seen.add(vin)
                    entities.append(V3ClimateQuickSwitch(coordinator, car))
            elif platform == "lock":
                if (vin not in seen and (
                    engine.control_enabled(car.vin, "lock", "access")
                    or engine.control_enabled(car.vin, "unlock", "access")
                )):
                    seen.add(vin)
                    entities.append(V3LockEntity(coordinator, car))
        if entities:
            async_add_entities(entities)

    add_verified()
    entry.async_on_unload(coordinator.async_add_listener(add_verified))
