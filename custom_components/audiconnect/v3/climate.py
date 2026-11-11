"""One V3 climate entity with optional status and control.

The existing climate unique ID is reused. All network/auth stays in the
existing Audi account during migration; V3 never opens a second session.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.exceptions import HomeAssistantError

from ..audi_entity import AudiEntity, entity_unique_id
from ..coordinator import AudiDataUpdateCoordinator
from .registry import RegistryError
from .runtime import V3Runtime

_OFF = frozenset({"off", "inactive", "stopped"})
_UNKNOWN = frozenset({"", "unknown", "invalid", "unsupported", "unavailable", "error"})
_ACTIONS = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "ventilation": HVACAction.FAN,
}


class AudiV3Climate(AudiEntity, ClimateEntity):
    """Single climate capability; no speculative target-temperature slider."""

    _attr_name = "Climatisation"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _backing_attr = "climatisation_state"

    def __init__(
        self,
        coordinator: AudiDataUpdateCoordinator,
        vehicle: Any,
        runtime: V3Runtime,
    ) -> None:
        super().__init__(coordinator, vehicle)
        self.runtime = runtime
        # Existing unique ID, so the V2 climate entity is upgraded in place.
        self._attr_unique_id = entity_unique_id(vehicle, "climate", "climatisation")
        self._last_command_status: str | None = None

    @property
    def _reported_mode(self) -> str | None:
        value = getattr(self._vehicle, "climatisation_state", None)
        if not isinstance(value, str) or value.strip().lower() in _UNKNOWN:
            return None
        return value.strip().lower()

    @property
    def _may_control(self) -> bool:
        check = getattr(self._vehicle, "has_capability", None)
        # Explicitly reported denial always wins. For modern CARIAD we
        # require a positive feature permission to enable vehicle commands.
        if not callable(check) or check("climatisation") is not True:
            return False
        impaired = getattr(self._vehicle, "impaired_capabilities", ()) or ()
        if "climatisation" in impaired:
            return False
        try:
            return (
                self.runtime.resolve(self._vehicle, "start")["operation"] is not None
                and self.runtime.resolve(self._vehicle, "stop")["operation"] is not None
            )
        except RegistryError:
            return False

    @property
    def supported_features(self) -> ClimateEntityFeature:
        if not self._may_control:
            return ClimateEntityFeature(0)
        return ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

    @property
    def available(self) -> bool:
        # An entity with state but no control is valid, as is one with control
        # but temporarily missing telemetry. Offline coordinator stays offline.
        return bool(self.coordinator.last_update_success) and (
            self._reported_mode is not None or self._may_control
        )

    @property
    def hvac_mode(self) -> HVACMode | None:
        mode = self._reported_mode
        if mode is None:
            return None
        return HVACMode.OFF if mode in _OFF else HVACMode.HEAT_COOL

    @property
    def hvac_action(self) -> HVACAction | None:
        mode = self._reported_mode
        if mode is None:
            return None
        return HVACAction.OFF if mode in _OFF else _ACTIONS.get(
            mode, HVACAction.HEATING
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self.runtime.resolve(self._vehicle, "status")
        return {
            "v3_capability": "climate",
            "v3_status_path": status["operation"],
            "v3_status_selection": status["reason"],
            "v3_control_supported": self._may_control,
            "v3_last_command_outcome": self._last_command_status,
            "vehicle_climate_reported_state": self._reported_mode,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.HEAT_COOL:
            await self.async_turn_on()
        else:
            raise HomeAssistantError("Unsupported Audi V3 climate mode")

    async def async_turn_on(self) -> None:
        if not self._may_control:
            raise HomeAssistantError("Climate control is not authorized for this vehicle")
        try:
            operation = self.runtime.resolve(self._vehicle, "start")["operation"]
        except RegistryError as exc:
            raise HomeAssistantError("Invalid V3 start selection") from exc
        if operation == "cariad.climate.start.stored":
            result = await self.coordinator.account.connection.start_climate_control(
                self._vehicle.vin
            )
        elif operation == "cariad.climate.start.vehicle_settings":
            # A different command payload is NEVER an automatic fallback.
            # This must be explicitly selected in the integration options.
            target = getattr(self._vehicle, "climatisation_target_temperature", None)
            if (
                isinstance(target, bool)
                or not isinstance(target, (int, float))
                or not 15 <= target <= 30
            ):
                raise HomeAssistantError(
                    "Vehicle did not confirm a safe stored target temperature"
                )
            result = await self.coordinator.account.connection.start_climate_control(
                self._vehicle.vin, temp_c=int(target)
            )
        else:
            raise HomeAssistantError("No reviewed V3 climate start adapter selected")
        if result is not True:
            self._last_command_status = "request_failed"
            raise HomeAssistantError("Audi climate start request failed")
        self._last_command_status = (
            "confirmed_by_cloud_readback"
            if self._reported_mode is not None and self._reported_mode not in _OFF
            else "accepted_unconfirmed"
        )
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        if not self._may_control:
            raise HomeAssistantError("Climate control is not authorized for this vehicle")
        try:
            operation = self.runtime.resolve(self._vehicle, "stop")["operation"]
        except RegistryError as exc:
            raise HomeAssistantError("Invalid V3 stop selection") from exc
        if operation != "cariad.climate.stop":
            raise HomeAssistantError("No reviewed V3 climate stop adapter selected")
        result = await self.coordinator.account.connection.set_vehicle_climatisation(
            self._vehicle.vin, False
        )
        if result is not True:
            self._last_command_status = "request_failed"
            raise HomeAssistantError("Audi climate stop request failed")
        self._last_command_status = (
            "confirmed_by_cloud_readback" if self._reported_mode in _OFF
            else "accepted_unconfirmed"
        )
        self.async_write_ha_state()


__all__ = ["AudiV3Climate"]
