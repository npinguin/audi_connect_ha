"""Eligibility for historical CARIAD commands; no model-only permission."""
from __future__ import annotations


def eligible_operation(car, auth, capability, aspect):
    reported = car.advertised_capabilities
    impaired = car.impaired_capabilities
    def supports(*keys):
        return any(k in reported and k not in impaired for k in keys)
    def readable(key):
        return key in car.readings and car.readings[key].get("value") is not None
    if capability == "access" and aspect in ("lock", "unlock"):
        if (supports("access", "remoteLockUnlock") or
                (readable("doorLockStatus") and "access" not in impaired)):
            if getattr(auth.service, "_spin", None):
                return "cariad.access." + aspect
    if capability == "climate":
        if aspect.startswith("preheater_"):
            if supports("auxiliaryHeating", "hybridCarAuxiliaryHeating"):
                if aspect == "preheater_stop" or getattr(auth.service, "_spin", None):
                    return "cariad.climate." + aspect
        elif supports("climatisation") or (
            car.climate_state is not None and "climatisation" not in impaired
        ):
            return {
                "start": "cariad.climate.start.stored",
                "stop": "cariad.climate.stop",
                "start_with_settings": "cariad.climate.start.vehicle_settings",
                "set_settings": "cariad.climate.settings",
                "window_heating_start": "cariad.climate.window_heating_start",
                "window_heating_stop": "cariad.climate.window_heating_stop",
            }.get(aspect)
    if capability == "charging" and (supports("charging") or (
        readable("chargingState") and "charging" not in impaired
    )):
        return {
            "start": "cariad.charging.start", "stop": "cariad.charging.stop",
            "set_target_soc": "cariad.charging.settings",
            "set_charge_mode": "cariad.charging.mode",
            "set_location_charge_target": "cariad.charging.profiles",
        }.get(aspect)
    if capability == "remote":
        if aspect == "wake" and supports("vehicleWakeUp", "vehicleWakeUpTrigger"):
            return "cariad.remote.wake"
        if aspect == "refresh" and supports("vehicleWakeUp", "vehicleWakeUpTrigger", "vehicleStatus"):
            return "cariad.remote.refresh"
        if aspect == "flash" and supports("honkAndFlash") and car.position is not None:
            return "cariad.remote.flash"
    return None
