"""Only V3-owned Home Assistant entities. No V2 models or API adapters."""
from __future__ import annotations

from datetime import UTC, datetime
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
        return self.coordinator.last_update_success and (
            self.vehicle.climate_state is not None or bool(self.supported_features)
        )

    @property
    def hvac_mode(self) -> HVACMode | None:
        state = self.vehicle.climate_state
        if state is None:
            return None
        return HVACMode.OFF if state in ("off", "stopped", "inactive") else HVACMode.HEAT_COOL

    @property
    def hvac_action(self) -> HVACAction | None:
        state = self.vehicle.climate_state
        if state is None:
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
