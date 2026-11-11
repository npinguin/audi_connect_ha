"""Fixed, privacy-safe capability catalogue, inspired by observed myAudi identifiers.

The presence of a capability is not proof that a remote command is authorized
or functional. Raw myAudi HAR data is never imported or persisted.
"""
from __future__ import annotations

from typing import Any

CAPABILITY_GROUPS: dict[str, tuple[str, ...]] = {
    "charging": ("charging", "chargingTimers", "chargingProfiles"),
    "climate": ("climatisation", "climatisationTimers", "auxiliaryHeating"),
    "vehicle_status": ("measurements", "fuelStatus", "vehicleHealthInspection",
                       "vehicleHealthWarnings", "oilLevelStatus"),
    "mobility": ("tripStatistics", "parkingPosition", "b2bVDATrip"),
    "service": ("dealerAppointment", "onlineCarCare", "onlineLogBook"),
    "remote": ("access", "honkAndFlash", "vehicleWakeUp", "vehicleWakeUpTrigger"),
}

def snapshot_capabilities(vehicle: Any) -> dict[str, Any]:
    """Return only predeclared identifiers and a conservative tri-state verdict."""
    checker = getattr(vehicle, "has_capability", None)
    impaired = getattr(vehicle, "impaired_capabilities", frozenset()) or frozenset()
    groups: dict[str, dict[str, str]] = {}
    for family, names in CAPABILITY_GROUPS.items():
        statuses = {}
        for name in names:
            result = checker(name) if callable(checker) else None
            if result is True:
                statuses[name] = "reported_impaired" if name in impaired else "reported"
            elif result is False:
                statuses[name] = "not_reported_for_this_vehicle"
            else:
                statuses[name] = "unknown"
        groups[family] = statuses
    count = getattr(vehicle, "capabilities", None)
    return {
        "source": "vehicle_poll_not_browser_session",
        "advertised_capability_count": len(count) if isinstance(count, (set, frozenset, list, tuple)) else None,
        "groups": groups,
        "command_authorization_confirmed": False,
    }



def describe_vehicle_context(vehicle: Any, uses_auth0: bool) -> dict[str, Any]:
    """Non-authorizing hints about vehicle type, model family and API generation.

    Never trust nicknames or model assumptions to authorize an actuator.
    No raw model name, identifiers or source measurements are exported.
    """
    kind = getattr(vehicle, "car_type", None)
    kind = kind.strip().lower() if isinstance(kind, str) else ""
    if kind in ("electric", "bev", "battery electric"):
        vehicle_type = "battery_electric"
    elif kind in ("phev", "plug-in hybrid", "plug_in_hybrid"):
        vehicle_type = "plug_in_hybrid"
    elif kind == "hybrid":
        vehicle_type = "hybrid_unspecified"
    elif kind in ("diesel", "gasoline", "petrol"):
        vehicle_type = "combustion"
    else:
        vehicle_type = "unknown"

    model_source = getattr(vehicle, "model_source", None)
    model_name = getattr(vehicle, "model", None)
    model_name = model_name.strip().lower() if isinstance(model_name, str) else ""
    trusted_model = model_source in ("audi_long_name", "audi_short_name")
    is_q8 = trusted_model and (
        model_name.startswith("q8") or model_name.startswith("audi q8")
    )
    return {
        "api_generation_hint": "auth0_cariad" if uses_auth0 else "legacy_or_other",
        "vehicle_type_hint": vehicle_type,
        "model_family_hint": "q8" if is_q8 else "unverified",
        "model_inference_authorizes_commands": False,
        "wake_policy": "manual_opt_in_only",
    }
