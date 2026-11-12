"""Simple V3 vehicle state, without importing the historical V2 models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import re

from .registry import VehicleContext

_INVALID = frozenset({"", "invalid", "unsupported", "unknown", "error", "unavailable"})
CLIMATE_OFF_STATES = ("off", "stopped", "inactive")
CLIMATE_ON_STATES = ("heating", "cooling", "ventilation", "on", "active")
CHARGING_ON_STATES = ("charging",)
CHARGING_OFF_STATES = ("off", "stopped", "notcharging", "not_charging", "notreadyforcharging", "readyforcharging")


def charging_active(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return True if value in CHARGING_ON_STATES else False if value in CHARGING_OFF_STATES else None


def window_heating_active(rows):
    """Actual window state only: a positive is conclusive; off requires both known."""
    if not isinstance(rows, list) or not rows:
        return None
    states = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        location, state = row.get("windowLocation"), row.get("windowHeatingState")
        if location not in ("front", "rear") or location in states:
            return None
        states[location] = state.strip().lower() if isinstance(state, str) else None
    if "on" in states.values():
        return True
    if set(states) == {"front", "rear"} and all(state == "off" for state in states.values()):
        return False
    return None


def model_family_from_name(value):
    """Only manufacturer model labels, never nickname or VIN inference."""
    if not isinstance(value, str):
        return ""
    label = re.sub(r"^audi\s+", "", value.strip(), flags=re.I)
    match = re.match(r"^(?:(?:rs|sq|s|q|a)\s*[1-9]|r8)(?=\b|[- ])", label, re.I)
    if match:
        return re.sub(r"\s+", "", match.group(0)).lower()
    return "e-tron" if re.match(r"^e[- ]tron\b", label, re.I) else ""


def normalize_powertrain(value):
    """Normalize explicit vendor enums, never infer from a model label."""
    if not isinstance(value, str):
        return None
    token = re.sub(r"[^a-z0-9]", "", value.lower())
    groups = {
        "phev": {"phev", "pluginhybrid", "pluginhybridelectricvehicle"},
        "hybrid": {"hybrid", "hev", "hybridelectricvehicle", "mhev", "mildhybrid"},
        "electric": {"electric", "bev", "batteryelectric", "batteryelectricvehicle"},
        "combustion": {"combustion", "ice", "internalcombustion", "internalcombustionengine",
                       "gasoline", "petrol", "diesel", "cng", "lpg"},
    }
    return next((key for key, values in groups.items() if token in values), None)


def powertrain_identity(vehicle):
    """Reconcile inventory, status and trips without granting control rights."""
    readings = getattr(vehicle, "readings", {})
    trips = getattr(vehicle, "trips", {})
    sources = {}
    def add(source, value):
        normalized = normalize_powertrain(value)
        if normalized is not None:
            sources[source] = normalized
    add("inventory", getattr(vehicle, "car_type", None))
    for ident, source in (("carType", "range_status"), ("measuredCarType", "fuel_level_status")):
        row = readings.get(ident, {})
        if row.get("status") in ("verified", "readable_but_stale"):
            add(source, row.get("value"))
    for key in ("last_trip", "shortterm_current", "longterm_current"):
        add(key, trips.get(key, {}).get("vehicleType"))
    roles = {normalize_powertrain(readings.get(key, {}).get("value"))
             for key in ("primary_engine_type", "secondary_engine_type")
             if readings.get(key, {}).get("status") in ("verified", "readable_but_stale")}
    if {"electric", "combustion"} <= roles:
        sources["engine_roles"] = "hybrid"
    families = {"hybrid" if value == "phev" else value for value in sources.values()}
    conflict = len(families) > 1
    value = None if conflict or not families else (
        "phev" if "phev" in sources.values() else next(iter(families)))
    return {"value": value, "sources": sources, "conflict": conflict}


@dataclass
class V3Vehicle:
    vin: str
    name: str
    model: str
    model_family: str
    country: str
    car_type: str = ""
    model_year: str = ""
    model_source: str = ""
    auth_family: str = "auth0"
    legacy_cariad: bool = False
    legacy_api_level: int = 0
    climate_state: str | None = None
    climate_captured: datetime | None = None
    last_status_observed: datetime | None = None
    climate_source: str | None = None
    climate_field: str | None = None
    climate_http_status: int | None = None
    last_command_result: str | None = None
    readings: dict[str, dict[str, Any]] = field(default_factory=dict)
    capability_readings: dict[str, dict[str, Any]] = field(default_factory=dict)
    position: dict[str, Any] | None = None  # V3-owned, in-memory parked GPS
    charging_profiles: list[dict[str, Any]] = field(default_factory=list)
    active_charging_profile_id: int | None = None
    charging_profiles_captured: str | None = None
    trips: dict[str, dict[str, Any]] = field(default_factory=dict)
    trip_history: list[dict[str, Any]] = field(default_factory=list)  # local normalized archive
    advertised_capabilities: set[str] = field(default_factory=set)
    impaired_capabilities: set[str] = field(default_factory=set)
    v2_initial_discovery_completed: bool = False
    inventory_present: bool = True
    inventory_misses: int = 0

    @classmethod
    def from_graphql(cls, item: dict[str, Any], country: str) -> "V3Vehicle":
        vin = item.get("vin")
        if not isinstance(vin, str) or len(vin) != 17 or not vin.isalnum():
            raise ValueError("Invalid Audi vehicle identifier")
        vehicle = item.get("vehicle") if isinstance(item.get("vehicle"), dict) else {}
        media = vehicle.get("media") if isinstance(vehicle.get("media"), dict) else {}
        def label(key):
            value = media.get(key)
            return value.strip() if isinstance(value, str) and value.strip().lower() not in _INVALID else ""
        long_name, short_name = label("longName"), label("shortName")
        model = long_name or short_name
        source = "audi_long_name" if long_name else "audi_short_name" if short_name else ""
        family = model_family_from_name(short_name) or model_family_from_name(long_name)
        core = vehicle.get("core") if isinstance(vehicle.get("core"), dict) else {}
        year = str(core.get("modelYear") or "")
        year = year if len(year) == 4 and year.isdigit() and 1980 <= int(year) <= 2100 else ""
        nickname = item.get("nickname")
        title = nickname if isinstance(nickname, str) and nickname.strip() else model
        classification = vehicle.get("classification")
        drive = (
            classification.get("driveTrain", "")
            if isinstance(classification, dict) else ""
        )
        return cls(
            vin=vin.upper(), name=title or "Audi vehicle", model=model,
            model_family=family, country=country,
            car_type=drive.strip().lower() if isinstance(drive, str) and drive.strip().lower() not in _INVALID else "",
            model_year=year, model_source=source,
        )

    @property
    def context(self) -> VehicleContext:
        return VehicleContext(
            auth=self.auth_family, region=self.country,
            vehicle_type=self.car_type, model_family=self.model_family,
            legacy_cariad=self.legacy_cariad, legacy_api_level=self.legacy_api_level,
        )

    @property
    def climate_supported(self) -> bool | None:
        """No hard unsupported verdict from merely missing cloud data."""
        return True if self.climate_state is not None else None

    def set_climate(
        self, value: Any, captured: Any, *,
        route: str, observed_at: datetime, http_status: int,
    ) -> bool:
        """Preserve previous readable data on partial or invalid responses."""
        self.climate_http_status = http_status
        if not isinstance(value, str) or value.strip().lower() in _INVALID:
            return False
        from .attribute_runtime import _capture_in_utc
        incoming = _capture_in_utc(captured)
        if self.climate_captured is not None and (
            incoming is None or incoming < self.climate_captured
        ):
            return False
        self.climate_state = value.strip().lower()
        self.climate_source = route
        self.last_status_observed = observed_at
        self.climate_captured = incoming
        return True

    @property
    def capture_age_minutes(self) -> int | None:
        if self.climate_captured is None:
            return None
        from .freshness import capture_age_minutes
        age = capture_age_minutes(self.climate_captured.isoformat())
        return int(age) if age is not None else None
