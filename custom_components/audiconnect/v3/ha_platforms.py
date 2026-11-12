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
    V3PreheaterSwitch, V3LocalServiceSensor, V3ApiQuotaSensor,
)
from .custom_attributes import attributes_for
from .attribute_contracts import semantic_value_issue
from .product_contract import (CORE_STATUS_KINDS, account_cloud_refresh_vin,
                               projection_descriptor, projection_reading, entity_key)


def setup(platform: str, entry: Any, async_add_entities: Any) -> None:
    """Forward exactly one V3 platform and watch new *proven* field discovery."""
    runtime = entry.runtime_data
    engine, coordinator = runtime.v3, runtime.coordinator
    if engine is None:
        raise ValueError("V3 platform forwarded without V3 engine")
    seen: set[str] = set()
    if not hasattr(engine, "projected_entities"):
        engine.projected_entities = {}
    projected = engine.projected_entities.setdefault(platform, set())

    if platform not in ("sensor", "binary_sensor", "button", "switch", "lock",
                         "climate", "device_tracker", "number", "select"):
        raise ValueError("Unknown Audi V3 Home Assistant platform")

    def add_verified() -> None:
        entities: list[Any] = []
        if platform == "button":
            anchor = getattr(engine, "cloud_refresh_vin", None) or account_cloud_refresh_vin(engine.vehicles)
            if anchor and anchor in engine.vehicles and "account:cloud_refresh" not in seen:
                seen.add("account:cloud_refresh")
                engine.cloud_refresh_vin = anchor
                entities.append(V3CloudRefreshButton(coordinator, engine.vehicles[anchor]))
        for car in engine.vehicles.values():
            if not car.inventory_present:
                continue
            vin = car.vin.lower()
            def add_once(tag: str, factory, *args) -> None:
                if tag not in seen:
                    seen.add(tag)
                    entities.append(factory(coordinator, car, *args))

            if platform == "sensor":
                for kind in CORE_STATUS_KINDS:
                    add_once(f"{vin}:core:{kind}", V3StatusSensor, kind)
                for kind in ("local_dealer", "service_overview"):
                    add_once(f"{vin}:local:{kind}", V3LocalServiceSensor, kind)
                if "account:quota" not in seen:
                    add_once("account:quota", V3ApiQuotaSensor, entry.entry_id)
            elif platform == "climate":
                if car.climate_state is not None or any(engine.control_enabled(car.vin, action)
                    for action in ("start", "stop", "start_with_settings")):
                    add_once(f"{vin}:climate", V3ClimateEntity)
            elif platform == "device_tracker":
                add_once(f"{vin}:tracker", V3ParkedTracker)
            elif platform == "number":
                if engine.control_enabled(car.vin, "set_target_soc", "charging") and type(car.readings.get("targetstateOfCharge", {}).get("value")) in (int, float):
                    add_once(f"{vin}:target_soc", V3ChargeTargetNumber)
            elif platform == "select":
                if engine.control_enabled(car.vin, "set_charge_mode", "charging") and car.readings.get("availableChargeModes", {}).get("value"):
                    add_once(f"{vin}:charge_mode", V3ChargeModeSelect)

            if platform in ("sensor", "binary_sensor"):
                if platform == "sensor":
                    for key in car.trips:
                        tag = f"{vin}:{key}"
                        if tag not in seen:
                            seen.add(tag)
                            entities.append(V3TripSensor(coordinator, car, key))
                profile = getattr(engine, "profiles", {}).get(vin)
                attributes = attributes_for(profile)
                for ident in car.readings:
                    descriptor = attributes.get(ident)
                    if descriptor and descriptor.get("local") and ident not in profile.attribute_routes:
                        continue
                    if not descriptor or descriptor["platform"] != platform:
                        continue
                    descriptor = projection_descriptor(descriptor)
                    if descriptor is None:
                        continue
                    _source, reading = projection_reading(car, descriptor)
                    if not reading or not isinstance(
                        reading.get("value"), (str, int, float, bool)
                    ):
                        continue
                    if platform == "sensor" and semantic_value_issue(
                        descriptor["entity_key"], reading["value"], descriptor.get("contract")
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
                preheater = f"{vin}:preheater_active"
                if preheater not in seen and any(
                    engine.control_enabled(car.vin, aspect, "climate")
                    for aspect in ("preheater_start", "preheater_stop")
                ):
                    seen.add(preheater)
                    entities.append(V3PreheaterSwitch(coordinator, car))
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
            for entity in entities:
                if entity_key(entity.unique_id, entry.entry_id) is None:
                    raise ValueError("V3 entity missing a product identity contract")
            projected.update(entity.unique_id for entity in entities)
            async_add_entities(entities)

    add_verified()
    entry.async_on_unload(coordinator.async_add_listener(add_verified))
