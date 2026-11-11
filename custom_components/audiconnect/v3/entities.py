"""Only V3-owned Home Assistant entities. No V2 models or API adapters."""
from __future__ import annotations

from datetime import UTC, datetime
from homeassistant.components.binary_sensor import BinarySensorEntity
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from .coordinator_clean import V3CleanCoordinator
from .vehicle import V3Vehicle


class V3BaseEntity(CoordinatorEntity[V3CleanCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator)
        self.vehicle = vehicle

    @property
    def device_info(self) -> DeviceInfo:
        name = self.vehicle.model.removeprefix("Audi ").strip() or "Audi"
        return DeviceInfo(
            identifiers={(DOMAIN, self.vehicle.vin.lower())},
            manufacturer="Audi",
            name=self.vehicle.name,
            model=name,
        )


class V3ClimateEntity(V3BaseEntity, ClimateEntity):
    _attr_name = "Climatisation"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        # Keep original unique ID and HA automations.
        self._attr_unique_id = f"{vehicle.vin.lower()}_climate_climatisation"

    @property
    def supported_features(self) -> ClimateEntityFeature:
        value = ClimateEntityFeature(0)
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "start"):
            value |= ClimateEntityFeature.TURN_ON
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "stop"):
            value |= ClimateEntityFeature.TURN_OFF
        return value

    @property
    def available(self) -> bool:
        age = self.vehicle.capture_age_minutes
        status_current = (
            self.vehicle.climate_state is not None
            and age is not None and age <= 60
        )
        return self.coordinator.last_update_success and (
            status_current or bool(self.supported_features)
        )

    @property
    def hvac_mode(self) -> HVACMode | None:
        state = self.vehicle.climate_state
        age = self.vehicle.capture_age_minutes
        if state is None or age is None or age > 60:
            return None
        return HVACMode.OFF if state in ("off", "stopped", "inactive") else HVACMode.HEAT_COOL

    @property
    def hvac_action(self) -> HVACAction | None:
        state = self.vehicle.climate_state
        age = self.vehicle.capture_age_minutes
        if state is None or age is None or age > 60:
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
            "start_tested": engine.control_enabled(self.vehicle.vin, "start"),
            "stop_tested": engine.control_enabled(self.vehicle.vin, "stop"),
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
            "capability": "v3_climate_capability",
            "poll": "v3_poll_status",
        }
        self._attr_unique_id = f"{vehicle.vin.lower()}_sensor_{identifiers[kind]}"
        self._attr_name = {
            "cloud": "Cloud last successful poll",
            "age": "Vehicle data age",
            "capability": "Climate capability",
            "poll": "V3 cloud polling",
        }[kind]

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP if self.kind == "cloud" else None

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
        if self.kind == "age":
            return self.vehicle.capture_age_minutes
        if self.kind == "poll":
            return "online" if self.coordinator.last_update_success else "failed"
        if self.vehicle.climate_state is None:
            return "unknown"
        age = self.vehicle.capture_age_minutes
        if age is None or age > 60:
            return "stale_status"
        if self.coordinator.engine.control_enabled(self.vehicle.vin, "start"):
            return "status_and_control"
        return "status_only"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        engine = self.coordinator.engine
        if self.kind == "poll":
            return {
                "requests": engine.transport.request_count,
                "remaining_api_calls": engine.transport.remaining_calls,
                "last_attempt": engine.last_cloud_poll_attempt.isoformat()
                if engine.last_cloud_poll_attempt else None,
                "last_success": engine.last_cloud_poll_success.isoformat()
                if engine.last_cloud_poll_success else None,
            }
        if self.kind == "capability":
            return {
                "start_enabled": engine.control_enabled(self.vehicle.vin, "start"),
                "stop_enabled": engine.control_enabled(self.vehicle.vin, "stop"),
                "status_api": self.vehicle.climate_source,
            }
        return {}


class V3CloudRefreshButton(V3BaseEntity, ButtonEntity):
    _attr_name = "Refresh Audi cloud"
    _attr_icon = "mdi:cloud-refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle):
        super().__init__(coordinator, vehicle)
        self._attr_unique_id = f"{vehicle.vin.lower()}_button_v3_refresh_cloud"

    async def async_press(self) -> None:
        # GET refresh; not a vehicle-wake POST. Polling budget stays enforced.
        await self.coordinator.async_request_refresh()

def _reading_age_minutes(captured: str | None) -> float | None:
    if not captured:
        return None
    try:
        point = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except ValueError:
        return None
    if point.tzinfo is None:
        return None
    return max(0.0, (datetime.now(UTC) - point.astimezone(UTC)).total_seconds() / 60)


def _reading_available(reading: dict[str, Any] | None) -> bool:
    if not reading:
        return False
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
        self._attr_name = attribute["entity_key"].replace("_", " ").capitalize()

    @property
    def available(self) -> bool:
        reading = self.vehicle.readings.get(self.attribute["id"])
        return _reading_available(reading)

    @property
    def native_value(self):
        reading = self.vehicle.readings.get(self.attribute["id"])
        value = reading.get("value") if reading else None
        return value if isinstance(value, (str, int, float, bool)) else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        name = self.attribute["entity_key"]
        if name in ("state_of_charge", "target_state_of_charge", "tank_level"):
            return "%"
        if name in ("range", "hybrid_range", "mileage", "service_inspection_distance",
                    "oil_change_distance", "service_adblue_distance"):
            return "km"
        if name in ("remaining_charging_time", "remaining_climatisation_time",
                    "service_inspection_time", "oil_change_time"):
            return "min" if name.startswith("remaining_") else "d"
        if name == "charging_power":
            return "kW"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reading = self.vehicle.readings.get(self.attribute["id"]) or {}
        return {
            "v3_capability": self.attribute["capability"],
            "v2_attribute": self.attribute["id"],
            "api_family": reading.get("family", "cariad"),
            "vehicle_freshness": "unknown" if not reading.get("captured") else reading.get("status"),
            "cloud_age_minutes": _reading_age_minutes(reading.get("observed")),
            "response_mapping": reading.get("path"),
            "vehicle_captured": reading.get("captured"),
            "age_minutes": _reading_age_minutes(reading.get("captured")),
            "verification": reading.get("status", "unknown"),
        }


class V3ReadOnlyBinarySensor(V3BaseEntity, BinarySensorEntity):
    """Mirror V2's binary conversion for fields with an actual known mapping."""
    def __init__(self, coordinator: V3CleanCoordinator, vehicle: V3Vehicle, attribute: dict[str, Any]):
        super().__init__(coordinator, vehicle)
        self.attribute = attribute
        self._attr_unique_id = f'{vehicle.vin.lower()}_binary_sensor_{attribute["entity_key"]}'
        self._attr_name = attribute["entity_key"].replace("_", " ").capitalize()

    @property
    def available(self) -> bool:
        reading = self.vehicle.readings.get(self.attribute["id"])
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
                return None if normalized in ("", "invalid", "unsupported", "unknown") else normalized != "disconnected"
            if key == "plug_lock_state":
                return None if normalized in ("", "invalid", "unsupported", "unknown") else normalized != "locked"
            if normalized in ("normal", "false", "off", "inactive", "closed", "locked"):
                return False
            if normalized in ("true", "on", "active", "open", "unlocked"):
                return True
            return None
        return bool(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reading = self.vehicle.readings.get(self.attribute["id"]) or {}
        return {
            "v3_capability": self.attribute["capability"],
            "response_mapping": reading.get("path"),
            "vehicle_captured": reading.get("captured"),
            "verification": reading.get("status", "unknown"),
        }
