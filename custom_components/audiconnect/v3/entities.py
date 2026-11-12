"""Only V3-owned Home Assistant entities. No V2 models or API adapters."""
from __future__ import annotations

from datetime import UTC, datetime
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.number import NumberEntity, NumberDeviceClass, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.lock import LockEntity
from homeassistant.components.switch import SwitchEntity
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass, RestoreSensor
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime, PERCENTAGE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from .coordinator_clean import V3CleanCoordinator
from .vehicle import V3Vehicle
from .attribute_contracts import contract_for, binary_contract_for, semantic_value_issue
from .product_contract import projection_reading, compatibility_hidden


def _binding_status(profile, key):
    return (getattr(profile, "fast_bindings", {}).get(key, {}).get("status", "unknown")
            if profile is not None else "unknown")


class V3BaseEntity(CoordinatorEntity[V3CleanCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator)
        self.vehicle = vehicle

    @property
    def available(self) -> bool:
        return getattr(self.vehicle, "inventory_present", True) and super().available

    @property
    def device_info(self) -> DeviceInfo:
        name = self.vehicle.model.removeprefix("Audi ").strip() or "Audi"
        if self.vehicle.model_year:
            name = f"{name} ({self.vehicle.model_year})"
        return DeviceInfo(
            identifiers={(DOMAIN, self.vehicle.vin.lower())},
            manufacturer="Audi",
            name=self.vehicle.name,
            model=name,
        )


class V3ClimateEntity(V3BaseEntity, ClimateEntity, RestoreEntity):
    _attr_name = "Climate"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 15
    _attr_max_temp = 30
    _attr_target_temperature_step = 1.0

    @property
    def native_target_temperature(self):
        row = self.vehicle.readings.get("climatisationTargetTemperatureC", {})
        value = row.get("value")
        return self._requested_temperature if self._requested_temperature is not None else (
            value if type(value) in (int, float) and 15 <= value <= 30 else self._restored_temperature
        )

    @property
    def target_temperature(self):
        return self.native_target_temperature

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                value = float(last.attributes.get("temperature"))
                if 15 <= value <= 30:
                    self._restored_temperature = value
            except (TypeError, ValueError):
                pass

    async def async_set_temperature(self, **kwargs):
        value = kwargs.get("temperature")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 15 <= value <= 30:
            raise HomeAssistantError("Climate temperature must be 15..30 C")
        # V2 contract: changing a setpoint while off never starts the car.
        self._requested_temperature = float(value)
        self.async_write_ha_state()
        if self.hvac_mode == HVACMode.HEAT_COOL:
            try:
                await self.coordinator.engine.send_control(
                    self.vehicle.vin, "start_with_settings", "climate",
                    params={"temp_c": value},
                )
            except (RuntimeError, ValueError) as err:
                raise HomeAssistantError(str(err)) from err

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        # Keep original unique ID and HA automations.
        self._attr_unique_id = f"{vehicle.vin.lower()}_climate_climatisation"
        self._requested_temperature = None
        self._restored_temperature = 21.0

    @property
    def supported_features(self) -> ClimateEntityFeature:
        value = ClimateEntityFeature(0)
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "start_with_settings"):
            value |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "start"):
            value |= ClimateEntityFeature.TURN_ON
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "stop"):
            value |= ClimateEntityFeature.TURN_OFF
        return value

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        age = self.vehicle.capture_age_minutes
        status_current = (
            self.vehicle.climate_state is not None
            and age is not None and age <= 60
        )
        return self.coordinator.last_update_success and (
            status_current or bool(self.supported_features)
        )

    def _recent_legacy_status(self):
        return self.vehicle.context.auth == "legacy" and _reading_available(
            self.vehicle.readings.get("climatisationState"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        state = self.vehicle.climate_state
        age = self.vehicle.capture_age_minutes
        if state is None or (age is None and not self._recent_legacy_status()) or (age is not None and age > 60):
            return None
        if state in ("off", "stopped", "inactive"):
            return HVACMode.OFF
        if state in ("heating", "cooling", "ventilation", "on", "active"):
            return HVACMode.HEAT_COOL
        return None

    @property
    def hvac_action(self) -> HVACAction | None:
        state = self.vehicle.climate_state
        age = self.vehicle.capture_age_minutes
        if state is None or (age is None and not self._recent_legacy_status()) or (age is not None and age > 60):
            return None
        return {
            "off": HVACAction.OFF, "stopped": HVACAction.OFF,
            "inactive": HVACAction.OFF, "heating": HVACAction.HEATING,
            "cooling": HVACAction.COOLING, "ventilation": HVACAction.FAN,
        }.get(state)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        engine = self.coordinator.engine
        profile = engine.profiles.get(self.vehicle.vin.lower())
        return {
            "v3_capability": "climate",
            "api_route": self.vehicle.climate_source,
            "vehicle_captured": self.vehicle.climate_captured.isoformat()
            if self.vehicle.climate_captured else None,
            "age_minutes": self.vehicle.capture_age_minutes,
            "start_enabled": engine.control_enabled(self.vehicle.vin, "start"),
            "stop_enabled": engine.control_enabled(self.vehicle.vin, "stop"),
            "start_evidence": _binding_status(profile, "climate.start"),
            "stop_evidence": _binding_status(profile, "climate.stop"),
            "last_command": self.vehicle.last_command_result,
            "active_paths": len(profile.active) if profile else 0,
        }

    async def async_set_hvac_mode(self, mode: HVACMode) -> None:
        if mode == HVACMode.OFF:
            await self.async_turn_off()
        elif mode == HVACMode.HEAT_COOL:
            await self.async_turn_on()
        else:
            raise HomeAssistantError("Unsupported climate mode")

    async def async_turn_on(self) -> None:
        if not self.coordinator.engine.control_enabled(self.vehicle.vin, "start"):
            raise HomeAssistantError("Climate Start must be tested and enabled in V3 Development")
        try:
            if self.coordinator.engine.control_enabled(self.vehicle.vin, "start_with_settings"):
                await self.coordinator.engine.send_control(
                    self.vehicle.vin, "start_with_settings", "climate",
                    params={"temp_c": self.native_target_temperature},
                )
            elif self._requested_temperature is not None:
                raise HomeAssistantError("Temperature-bearing start is not enabled")
            else:
                await self.coordinator.engine.send_control(self.vehicle.vin, "start")
        except (RuntimeError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        if not self.coordinator.engine.control_enabled(self.vehicle.vin, "stop"):
            raise HomeAssistantError("Climate Stop must be tested and enabled in V3 Development")
        try:
            await self.coordinator.engine.send_control(self.vehicle.vin, "stop")
        except (RuntimeError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()


class V3StatusSensor(V3BaseEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle, kind: str):
        super().__init__(coordinator, vehicle)
        self.kind = kind
        identifiers = {
            "cloud": "cloud_last_successful_poll",
            "age": "vehicle_data_age",
            "freshness": "vehicle_data_freshness",
        }
        self._attr_unique_id = f"{vehicle.vin.lower()}_sensor_{identifiers[kind]}"
        self._attr_name = {
            "cloud": "Cloud last successful poll",
            "age": "Vehicle data age",
            "freshness": "Vehicle data freshness",
        }[kind]

    @property
    def device_class(self):
        return (SensorDeviceClass.TIMESTAMP if self.kind == "cloud"
                else SensorDeviceClass.ENUM if self.kind == "freshness" else None)

    @property
    def options(self):
        return ["fresh", "delayed", "stale", "unknown"] if self.kind == "freshness" else None

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT if self.kind == "age" else None

    def _vehicle_age(self):
        # Match historical HA age semantics; ignore future and sentinel clocks.
        ages = [_reading_age_minutes(x.get("captured")) for x in self.vehicle.readings.values()]
        return min((int(x) for x in ages if x is not None), default=None)

    @property
    def native_unit_of_measurement(self):
        return UnitOfTime.MINUTES if self.kind == "age" else None

    @property
    def available(self) -> bool:
        return True  # Diagnostic sensors stay visible during outages.

    @property
    def native_value(self):
        if self.kind == "cloud":
            return self.coordinator.engine.last_cloud_poll_success
        if self.kind in ("age", "freshness"):
            age = self._vehicle_age()
            if self.kind == "age":
                return age
            return ("unknown" if age is None else "fresh" if age <= 30
                    else "delayed" if age <= 120 else "stale")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        engine = self.coordinator.engine
        if self.kind == "freshness":
            last = self.vehicle.readings.get("last_update_time", {}).get("value")
            return {
                "vehicle_last_update": last,
                "vehicle_age_minutes": self._vehicle_age(),
                "cloud_last_successful_poll": (
                    engine.last_cloud_poll_success.isoformat()
                    if engine.last_cloud_poll_success else None),
                "cloud_last_attempt": (
                    engine.last_cloud_poll_attempt.isoformat()
                    if engine.last_cloud_poll_attempt else None),
                "last_cloud_poll_succeeded": getattr(engine, "last_cloud_poll_succeeded",
                                                        self.coordinator.last_update_success),
                "freshness_basis": "newest_vehicle_timestamp_not_all_fields",
            }
        if self.kind == "cloud":
            return {
                "cloud_poll_succeeded": getattr(engine, "last_cloud_poll_succeeded",
                                                 self.coordinator.last_update_success),
                "last_attempt": engine.last_cloud_poll_attempt.isoformat()
                if engine.last_cloud_poll_attempt else None,
                "requests": engine.transport.request_count if hasattr(engine.transport, "request_count") else None,
            }
        return {}


class V3LocalServiceSensor(V3BaseEntity, SensorEntity):
    """Historical local dealer/service entities, not Audi cloud diagnostics."""

    def __init__(self, coordinator, vehicle, kind):
        super().__init__(coordinator, vehicle)
        self.kind = kind
        self._attr_unique_id = f"{vehicle.vin.lower()}_sensor_{kind}"
        self._attr_name = "Dealer (local)" if kind == "local_dealer" else "Service overview"
        self._attr_icon = "mdi:store" if kind == "local_dealer" else "mdi:car-wrench"

    @property
    def available(self):
        return True

    def _local(self):
        # Shared config-only helper; no V2 model or business API.
        from ..local_extensions import get_local_dealer
        return get_local_dealer(self.coordinator.engine.entry.options, self.vehicle.vin)

    def _value(self, ident):
        row = self.vehicle.readings.get(ident)
        return row.get("value") if _reading_available(row, allow_last_known=True) else None

    @property
    def native_value(self):
        if self.kind == "local_dealer":
            return self._local().get("dealer_name", "Not configured")
        numbers = [x for x in (
            self._value("MAINTENANCE_INTERVAL_TIME_TO_INSPECTION"),
            self._value("MAINTENANCE_INTERVAL_TIME_TO_OIL_CHANGE"),
        ) if type(x) in (int, float)]
        if any(x <= 0 for x in numbers):
            return "overdue"
        if any(x <= 30 for x in numbers):
            return "due_soon"
        if numbers:
            return "scheduled"
        return "appointment_recorded" if self._local().get("next_service_date") else "unknown"

    @property
    def extra_state_attributes(self):
        data = self._local()
        if self.kind == "local_dealer":
            return {
                "source": "Home Assistant local configuration (not Audi)",
                "configured": bool(data),
                "configuration_path": "Audi Connect > Configure > Edit dealer and local service details",
                **{k: v for k, v in data.items() if k != "dealer_name"},
            }
        return {
            "inspection_due_days": self._value("MAINTENANCE_INTERVAL_TIME_TO_INSPECTION"),
            "inspection_due_km": self._value("MAINTENANCE_INTERVAL_DISTANCE_TO_INSPECTION"),
            "oil_service_due_days": self._value("MAINTENANCE_INTERVAL_TIME_TO_OIL_CHANGE"),
            "oil_service_due_km": self._value("MAINTENANCE_INTERVAL_DISTANCE_TO_OIL_CHANGE"),
            "next_appointment_local": data.get("next_service_date"),
            "warranty_expiry_local": data.get("warranty_expiry"),
            "maintenance_source": "Audi vehicleHealthInspection when reported",
            "appointment_source": "Home Assistant local configuration, not Audi",
        }


class V3ApiQuotaSensor(V3BaseEntity, RestoreSensor):
    """One account-level HA entity; never multiply quota sensors per VIN."""
    _attr_name = "API requests remaining"
    _attr_icon = "mdi:api"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, vehicle, entry_id):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{entry_id}_api_requests_remaining"
        self._restored_native_value: int | None = None
        self._restored_last_observed: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator.engine.transport.remaining_calls is not None:
            return
        restored = await self.async_get_last_sensor_data()
        if restored is not None and type(restored.native_value) is int and restored.native_value >= 0:
            self._restored_native_value = restored.native_value
        last_state = await self.async_get_last_state()
        if last_state is not None:
            if self._restored_native_value is None and last_state.state.isdigit():
                self._restored_native_value = int(last_state.state)
            stamp = last_state.attributes.get("last_observed")
            if isinstance(stamp, str):
                self._restored_last_observed = stamp

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        # Restored quota is display-only; never seed V3 transport budgeting.
        current = self.coordinator.engine.transport.remaining_calls
        return current if current is not None else self._restored_native_value

    @property
    def extra_state_attributes(self):
        transport = self.coordinator.engine.transport
        stamp = getattr(transport, "remaining_calls_observed_at", None)
        if transport.remaining_calls is not None:
            return {"last_observed": stamp.isoformat() if stamp else None,
                    "value_restored": False, "value_source": "live_header",
                    "value_is_current": True}
        return {"last_observed": self._restored_last_observed,
                "value_restored": self._restored_native_value is not None,
                "value_source": "last_known" if self._restored_native_value is not None else "unknown",
                "value_is_current": False, "current_remaining": None}


class V3CloudRefreshButton(V3BaseEntity, ButtonEntity):
    _attr_name = "Refresh cloud data"
    _attr_icon = "mdi:cloud-refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_button_v3_refresh_cloud"

    @property
    def available(self) -> bool:
        # An account refresh is independent of one VIN or a failed cloud poll.
        return True

    async def async_press(self) -> None:
        # GET refresh; not a vehicle-wake POST. Polling budget stays enforced.
        await self.coordinator.async_request_refresh()

def _reading_age_minutes(captured: str | None) -> float | None:
    if not captured:
        return None
    try:
        point = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None
    if point.tzinfo is None or point.year < 2020:
        return None
    delta = (datetime.now(UTC) - point.astimezone(UTC)).total_seconds()
    if delta < -300:
        return None
    return max(0.0, delta / 60)


def _reading_available(
    reading: dict[str, Any] | None, *, allow_last_known: bool = False,
) -> bool:
    if not reading or reading.get("value") is None:
        return False
    if allow_last_known:
        # V2 compatibility: retain passive vehicle readings from a sleeping
        # car. Their *actual* capture age is exposed separately. Safety-critical
        # binary statuses and controls still require timely vehicle evidence.
        return reading.get("status") in ("verified", "readable_but_stale")
    captured_age = _reading_age_minutes(reading.get("captured"))
    if captured_age is not None:
        return captured_age <= 60
    # MBB legacy responses may not include a vehicle capture timestamp.
    # Expose only *recently observed cloud values*, with explicitly unknown
    # vehicle freshness; never call them verified-fresh vehicle data.
    observed_age = _reading_age_minutes(reading.get("observed"))
    return bool(reading.get("family") == "mbb"
                and reading.get("status") == "readable_but_stale"
                and observed_age is not None and observed_age <= 60)


class V3ReadOnlySensor(V3BaseEntity, SensorEntity):
    """Read-only V3 entity reusing a historical V2 unique ID where mapped."""

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle, attribute: dict[str, Any]):
        super().__init__(coordinator, vehicle)
        self.attribute = attribute
        self._attr_unique_id = f'{vehicle.vin.lower()}_sensor_{attribute["entity_key"]}'
        contract = attribute.get("contract") or contract_for(attribute["entity_key"])
        self._attr_entity_registry_visible_default = not compatibility_hidden(vehicle, "sensor." + attribute["entity_key"])
        self._semantic_contract = contract
        self._allow_last_known = contract.get("display_last_known", False) is True
        self._attr_name = contract.get("name") or attribute["entity_key"].replace("_", " ").capitalize()
        self._attr_native_unit_of_measurement = contract.get("unit")
        self._attr_icon = contract.get("icon")
        if contract.get("device_class"):
            self._attr_device_class = SensorDeviceClass(contract["device_class"])
        if contract.get("state_class"):
            self._attr_state_class = SensorStateClass(contract["state_class"])
        if contract.get("precision") is not None:
            self._attr_suggested_display_precision = contract["precision"]
        if contract.get("category") == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        if self.attribute.get("local") and self.attribute["id"] not in self.coordinator.engine.profiles[self.vehicle.vin.lower()].attribute_routes:
            return False
        reading = projection_reading(self.vehicle, self.attribute)[1]
        return (_reading_available(reading, allow_last_known=self._allow_last_known)
                and not semantic_value_issue(self.attribute["entity_key"], reading.get("value"),
                                             self._semantic_contract))

    @property
    def native_value(self):
        reading = projection_reading(self.vehicle, self.attribute)[1]
        value = reading.get("value") if reading else None
        if semantic_value_issue(self.attribute["entity_key"], value, self._semantic_contract):
            return None
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            from .attribute_runtime import _capture_in_utc
            return _capture_in_utc(value)
        if self.attribute["id"] in ("vehicleReportedOnline", "vehicleReportedActive") and type(value) is bool:
            return ("online" if value else "offline") if self.attribute["id"] == "vehicleReportedOnline" else ("active" if value else "inactive")
        if self.attribute["id"] == "externalPower":
            return {"ready": "Ready", "unavailable": "Not Ready"}.get(value, value)
        if self.attribute["id"] == "chargingPlugAutoUnlock":
            return {"on": "enabled", "off": "disabled"}.get(value, value)
        return value if isinstance(value, (str, int, float, bool)) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source, reading = projection_reading(self.vehicle, self.attribute)
        reading = reading or {}
        captured_age = _reading_age_minutes(reading.get("captured"))
        freshness = (
            "unknown" if captured_age is None
            else "fresh" if captured_age <= 60
            else "stale_last_known" if self._allow_last_known else "stale"
        )
        return {
            "v3_capability": self.attribute["capability"],
            "v2_attribute": self.attribute["id"],
            "observed_source": source,
            "api_family": reading.get("family", "cariad"),
            "vehicle_freshness": freshness,
            "cloud_age_minutes": _reading_age_minutes(reading.get("observed")),
            "response_mapping": reading.get("path"),
            "vehicle_captured": reading.get("captured"),
            "age_minutes": _reading_age_minutes(reading.get("captured")),
            "verification": reading.get("status", "unknown"),
        }


class V3TripSensor(V3BaseEntity, SensorEntity):
    """Historical V2 trip timestamp plus normalized, unit-explicit attributes."""
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, vehicle, key):
        super().__init__(coordinator, vehicle)
        self.key = key
        self._attr_unique_id = f"{vehicle.vin.lower()}_sensor_{key}"
        self._attr_name = {
            "shortterm_current": "ShortTerm Trip Data",
            "shortterm_reset": "ShortTerm Trip User Reset",
            "longterm_current": "LongTerm Trip Data",
            "longterm_reset": "LongTerm Trip User Reset",
            "last_trip": "Last trip (CARIAD)",
        }[key]

    @property
    def native_value(self):
        from .attribute_runtime import _capture_in_utc
        return _capture_in_utc(self.vehicle.trips.get(self.key, {}).get("timestamp"))

    @property
    def available(self):
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return self.native_value is not None

    @property
    def extra_state_attributes(self):
        return {k: v for k, v in self.vehicle.trips.get(self.key, {}).items()
                if k not in ("tripID", "timestamp") and v is not None}


class V3ReadOnlyBinarySensor(V3BaseEntity, BinarySensorEntity):
    """Mirror V2's binary conversion for fields with an actual known mapping."""
    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle, attribute: dict[str, Any]):
        super().__init__(coordinator, vehicle)
        self.attribute = attribute
        self._attr_unique_id = f'{vehicle.vin.lower()}_binary_sensor_{attribute["entity_key"]}'
        contract = attribute.get("contract") or binary_contract_for(attribute["entity_key"])
        self._attr_name = contract.get("name") or attribute["entity_key"].replace("_", " ").capitalize()
        if contract.get("device_class"):
            self._attr_device_class = BinarySensorDeviceClass(contract["device_class"])
        self._attr_icon = contract.get("icon")
        if contract.get("category") == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        if self.attribute.get("local") and self.attribute["id"] not in self.coordinator.engine.profiles[self.vehicle.vin.lower()].attribute_routes:
            return False
        reading = self.vehicle.readings.get(self.attribute["id"])
        if self.attribute["id"] == "is_moving" and reading:
            # Historical parking endpoint indication, not a live GPS fix.
            age = _reading_age_minutes(reading.get("observed"))
            return (reading.get("path") in ("parkingposition HTTP 204", "parkingposition parked sample")
                    and type(reading.get("value")) is bool and age is not None and age <= 60)
        return _reading_available(reading)

    @property
    def is_on(self) -> bool | None:
        reading = self.vehicle.readings.get(self.attribute["id"])
        if not reading:
            return None
        value = reading.get("value")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            key = self.attribute["entity_key"]
            # V2 accessors normalize these raw Audi status enums before the
            # legacy binary platform sees them. V3 must do the same.
            if key == "plug_state":
                return {"connected": True, "disconnected": False}.get(normalized)
            if key == "plug_lock_state":
                return {"locked": False, "unlocked": True}.get(normalized)
            if normalized in ("normal", "false", "off", "inactive", "closed", "locked"):
                return False
            if normalized in ("true", "on", "active", "open", "unlocked"):
                return True
            return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reading = self.vehicle.readings.get(self.attribute["id"]) or {}
        return {
            "v3_capability": self.attribute["capability"],
            "response_mapping": reading.get("path"),
            "vehicle_captured": reading.get("captured"),
            "verification": reading.get("status", "unknown"),
        }


# Native HA controls are created only for personally verified route mappings.
# The workbench always shows unverified candidates without injecting unusable
# lock/button/switch entities into a customer's HA device.
CONTROL_BUTTONS = (
    ("refresh_vehicle_data", "Request fresh vehicle data", "mdi:cloud-refresh", "remote", "refresh"),
    ("flash_lights", "Flash lights", "mdi:car-light-high", "remote", "flash"),
    ("start_engine", "Start engine", "mdi:car-key", "remote", "engine_start"),
    ("stop_engine", "Stop engine", "mdi:car-off", "remote", "engine_stop"),
    ("wake_vehicle_modern", "Wake vehicle", "mdi:car-connected", "remote", "wake"),
    ("start_charging_modern", "Start charging", "mdi:ev-station", "charging", "start"),
    ("stop_charging_modern", "Stop charging", "mdi:ev-station", "charging", "stop"),
    ("start_window_heating_modern", "Start window heating", "mdi:car-defrost-rear", "climate", "window_heating_start"),
    ("stop_window_heating_modern", "Stop window heating", "mdi:car-defrost-rear", "climate", "window_heating_stop"),
)


class V3ControlButton(V3BaseEntity, ButtonEntity):
    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle,
                 descriptor: tuple[str, str, str, str, str]):
        super().__init__(coordinator, vehicle)
        self.key, self._attr_name, self._attr_icon, self.capability, self.action = descriptor
        self._attr_unique_id = f"{vehicle.vin.lower()}_button_{self.key}"
        if self.key == "refresh_vehicle_data":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if self.key == "wake_vehicle_modern":
            self._attr_entity_registry_enabled_default = False

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return (
            self.coordinator.last_update_success and
            self.coordinator.engine.control_enabled(
                self.vehicle.vin, self.action, self.capability
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        profile = self.coordinator.engine.profiles.get(self.vehicle.vin.lower())
        return {
            "v3_capability": self.capability,
            "api_route": (getattr(profile, "fast_bindings", {}).get(f"{self.capability}.{self.action}", {}).get("operation")
                          if profile else None),
            "binding_evidence": _binding_status(profile, f"{self.capability}.{self.action}"),
            "last_command": self.vehicle.last_command_result,
        }

    async def async_press(self) -> None:
        if not self.available:
            raise HomeAssistantError("Control must be tested and activated in Audi V3 first")
        try:
            await self.coordinator.engine.send_control(
                self.vehicle.vin, self.action, self.capability
            )
        except (ValueError, RuntimeError) as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()


class V3ClimateQuickSwitch(V3BaseEntity, SwitchEntity):
    _attr_name = "Climate ON/OFF (compatibility)"
    _attr_entity_registry_visible_default = False
    _attr_icon = "mdi:car-air-conditioner"

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_switch_climate_quick_control"

    @property
    def is_on(self) -> bool | None:
        state = self.vehicle.climate_state
        age = self.vehicle.capture_age_minutes
        if state is None or age is None or age > 60:
            return None
        if state in ("off", "inactive", "stopped"):
            return False
        if state in ("heating", "cooling", "ventilation", "on", "active"):
            return True
        return None

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        engine = self.coordinator.engine
        # A stale vehicle state is unknown, not a disabled explicit action.
        return (self.coordinator.last_update_success and
                engine.control_enabled(self.vehicle.vin, "start") and
                engine.control_enabled(self.vehicle.vin, "stop"))

    async def async_turn_on(self, **kwargs) -> None:
        if not self.available:
            raise HomeAssistantError("Climate ON/OFF requires available verified controls")
        if self.is_on is not True:
            await self.coordinator.engine.send_control(self.vehicle.vin, "start")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        if not self.available:
            raise HomeAssistantError("Climate ON/OFF requires available verified controls")
        if self.is_on is not False:
            await self.coordinator.engine.send_control(self.vehicle.vin, "stop")
        self.async_write_ha_state()


class V3LockEntity(V3BaseEntity, LockEntity):
    _attr_name = "Door lock"
    _attr_icon = "mdi:car-door-lock"

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_lock_lock"

    @property
    def is_locked(self) -> bool | None:
        # No silent assumption that an unavailable lock status means unlocked.
        row = self.vehicle.readings.get("doorLockStatus")
        if not _reading_available(row):
            return None
        raw = row.get("value")
        if not isinstance(raw, str):
            return None
        value = raw.strip().lower()
        if value == "locked":
            return True
        if value == "unlocked":
            return False
        return None

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        engine = self.coordinator.engine
        pin = getattr(getattr(engine.auth, "service", None), "_spin", None)
        # Do not hide an authorized explicit command just because the car
        # is sleeping. is_locked still returns None for stale/unknown status.
        return (self.coordinator.last_update_success
                and bool(pin) and (
                    engine.control_enabled(self.vehicle.vin, "lock", "access") or
                    engine.control_enabled(self.vehicle.vin, "unlock", "access")
                ))

    async def async_lock(self, **kwargs) -> None:
        if not self.available or not self.coordinator.engine.control_enabled(
            self.vehicle.vin, "lock", "access"
        ):
            raise HomeAssistantError("Lock route or authorization not available")
        if self.is_locked is not True:
            await self.coordinator.engine.send_control(self.vehicle.vin, "lock", "access")
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs) -> None:
        if not self.available or not self.coordinator.engine.control_enabled(
            self.vehicle.vin, "unlock", "access"
        ):
            raise HomeAssistantError("Unlock route or authorization not available")
        if self.is_locked is not False:
            await self.coordinator.engine.send_control(self.vehicle.vin, "unlock", "access")
        self.async_write_ha_state()


class V3ParkedTracker(V3BaseEntity, TrackerEntity):
    """V2-compatible GPS entity for the car's last PARKED position, not live GPS."""

    _attr_name = "Position"
    _attr_icon = "mdi:car"
    _attr_should_poll = False
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_device_tracker_position"

    def _coordinates(self) -> tuple[float, float] | None:
        position = self.vehicle.position
        if not isinstance(position, dict):
            return None
        lat, lon = position.get("latitude"), position.get("longitude")
        if isinstance(lat, bool) or isinstance(lon, bool):
            return None
        try:
            latitude, longitude = float(lat), float(lon)
        except (ValueError, TypeError):
            return None
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None
        return latitude, longitude

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return self._coordinates() is not None

    @property
    def latitude(self) -> float | None:
        coords = self._coordinates()
        return coords[0] if coords else None

    @property
    def longitude(self) -> float | None:
        coords = self._coordinates()
        return coords[1] if coords else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        position = self.vehicle.position or {}
        captured = position.get("timestamp")
        return {
            "position_source": "Audi last-known parked location, not live driving GPS",
            "position_captured_at": captured,
            "position_age_minutes": _reading_age_minutes(captured),
            "position_freshness": (
                "unknown" if captured is None else
                "stale" if (_reading_age_minutes(captured) or 0) > 60 else
                "fresh"
            ),
        }


class V3ChargeTargetNumber(V3BaseEntity, NumberEntity):
    """V2 global charge-target identity; command gated by V3 route evidence."""

    _attr_name = "Target state of charge"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 20
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_number_target_state_of_charge"

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return (
            _reading_available(self.vehicle.readings.get("targetstateOfCharge"),
                               allow_last_known=True)
            and self.coordinator.engine.control_enabled(
                self.vehicle.vin, "set_target_soc", "charging"
            )
        )

    @property
    def native_value(self) -> float | None:
        reading = self.vehicle.readings.get("targetstateOfCharge") or {}
        value = reading.get("value")
        return float(value) if (isinstance(value, (int, float))
                                and not isinstance(value, bool)) else None

    async def async_set_native_value(self, value: float) -> None:
        if not self.available:
            raise HomeAssistantError(
                "V3 charging target write not yet verified for this vehicle"
            )
        await self.coordinator.engine.send_setting(
            self.vehicle.vin, "set_target_soc", int(value)
        )


class V3LocationChargeTargetNumber(V3ChargeTargetNumber):
    """V2 active or named charging profile target, using immutable profile ID."""

    def __init__(self, coordinator, vehicle, profile_id=None):
        super().__init__(coordinator, vehicle)
        self.profile_id = profile_id
        key = ("active_charging_profile_target_soc" if profile_id is None
               else f"charge_profile_{profile_id}_target_soc")
        self._attr_unique_id = f"{vehicle.vin.lower()}_number_{key}"
        self._attr_name = ("Current location charge target" if profile_id is None
                           else f"Profile {profile_id} charge target")

    @property
    def native_value(self):
        profile_id = (self.vehicle.active_charging_profile_id
                      if self.profile_id is None else self.profile_id)
        profile = next((x for x in self.vehicle.charging_profiles
                        if x["id"] == profile_id), None)
        value = profile.get("targetSOC_pct") if profile else None
        return float(value) if type(value) in (int, float) else None

    @property
    def available(self):
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return self.native_value is not None and self.coordinator.engine.control_enabled(
            self.vehicle.vin, "set_location_charge_target", "charging")

    async def async_set_native_value(self, value):
        if not self.available or not float(value).is_integer():
            raise HomeAssistantError("Audi charge profile not available")
        await self.coordinator.engine.send_control(
            self.vehicle.vin, "set_location_charge_target", "charging",
            params={"value": int(value), "profile_id": self.profile_id},
        )


CLIMATE_SWITCHES = (
    ("climatisation_window_heating", "climatisationWindowHeatingEnabled", "windowHeatingEnabled"),
    ("climatisation_at_unlock", "climatisationAtUnlock", "climatizationAtUnlock"),
    ("climatisation_zone_front_left", "climatisationZoneFrontLeft", "zoneFrontLeftEnabled"),
    ("climatisation_zone_front_right", "climatisationZoneFrontRight", "zoneFrontRightEnabled"),
    ("climatisation_zone_rear_left", "climatisationZoneRearLeft", "zoneRearLeftEnabled"),
    ("climatisation_zone_rear_right", "climatisationZoneRearRight", "zoneRearRightEnabled"),
)


class V3PreheaterSwitch(V3BaseEntity, SwitchEntity):
    """Historical preheater control, never infer state from cabin climate."""
    _attr_name = "Preheater"
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator, vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_switch_preheater_active"

    @property
    def is_on(self):
        row = self.vehicle.readings.get("preheater_active")
        if not _reading_available(row):
            return None
        value = row.get("value")
        return value if type(value) is bool else None

    @property
    def available(self):
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        engine = self.coordinator.engine
        return self.coordinator.last_update_success and any(
            engine.control_enabled(self.vehicle.vin, aspect, "climate")
            for aspect in ("preheater_start", "preheater_stop")
        )

    async def _send(self, aspect):
        try:
            await self.coordinator.engine.send_control(
                self.vehicle.vin, aspect, "climate"
            )
        except (RuntimeError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._send("preheater_start")

    async def async_turn_off(self, **kwargs):
        await self._send("preheater_stop")


class V3ClimateSettingSwitch(V3BaseEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, vehicle, descriptor):
        super().__init__(coordinator, vehicle)
        key, self.reading, self.field = descriptor
        self._attr_unique_id = f"{vehicle.vin.lower()}_switch_{key}"
        self._attr_name = key.replace("_", " ").capitalize()

    @property
    def is_on(self):
        value = self.vehicle.readings.get(self.reading, {}).get("value")
        return value if type(value) is bool else None

    @property
    def available(self):
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return self.is_on is not None and self.coordinator.engine.control_enabled(
            self.vehicle.vin, "set_settings", "climate")

    async def _write(self, value):
        if not self.available:
            raise HomeAssistantError("Audi climate setting unavailable")
        await self.coordinator.engine.send_control(
            self.vehicle.vin, "set_settings", "climate",
            params={self.field: value},
        )

    async def async_turn_on(self, **kwargs):
        await self._write(True)

    async def async_turn_off(self, **kwargs):
        await self._write(False)


class V3ChargeModeSelect(V3BaseEntity, SelectEntity):
    """V2 select identity, independent preferred-mode source and command gate."""

    _attr_name = "Preferred charge mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:battery-clock"

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_select_charge_mode"

    @property
    def available(self) -> bool:
        if not getattr(self.vehicle, "inventory_present", True):
            return False
        return (
            _reading_available(self.vehicle.readings.get("preferredChargeMode"),
                               allow_last_known=True)
            and bool(self.options) and self.current_option in self.options
            and self.coordinator.engine.control_enabled(
                self.vehicle.vin, "set_charge_mode", "charging"
            )
        )

    @property
    def options(self) -> list[str]:
        observed = self.vehicle.readings.get("availableChargeModes") or {}
        values = observed.get("value")
        modes = [
            x for x in values
            if isinstance(x, str) and x.lower() not in
            {"", "invalid", "unsupported", "unknown"}
        ] if isinstance(values, list) else []
        # Only the vehicle-advertised choices may be written.
        # A reported current option is not evidence of other supported choices.
        return modes

    @property
    def current_option(self) -> str | None:
        reading = self.vehicle.readings.get("preferredChargeMode") or {}
        value = reading.get("value")
        if (not isinstance(value, str) or value.lower() in
                {"", "invalid", "unknown", "unsupported"}):
            return None
        return value

    async def async_select_option(self, option: str) -> None:
        if not self.available or option not in self.options:
            raise HomeAssistantError(
                "V3 preferred charge mode is not verified for this vehicle"
            )
        await self.coordinator.engine.send_setting(
            self.vehicle.vin, "set_charge_mode", option
        )
