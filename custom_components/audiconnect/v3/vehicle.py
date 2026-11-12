"""Simple V3 vehicle state, without importing the historical V2 models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .registry import VehicleContext

_INVALID = frozenset({"", "invalid", "unsupported", "unknown", "error", "unavailable"})


@dataclass
class V3Vehicle:
    vin: str
    name: str
    model: str
    model_family: str
    country: str
    car_type: str = ""
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
        model = media.get("longName") or media.get("shortName") or ""
        if not isinstance(model, str):
            model = ""
        family = "q8" if model.strip().lower().startswith(("audi q8", "q8")) else ""
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
            car_type=str(drive).lower() if drive is not None else "",
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
        return max(0, int((datetime.now(UTC) - self.climate_captured).total_seconds() / 60))
