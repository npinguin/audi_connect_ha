"""V3 integration runtime. One shared Audi account and one shared coordinator.

This is a migration seam: V3 owns routing/evidence and will own more domains
over time, while V2 adapters continue supplying other stable HA capabilities.
No second authentication or polling task is created.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .registry import CapabilityRegistry, RouteEvidence, VehicleContext

V3_RUNTIME_OPTION = "runtime_version"
V3_CLIMATE_START_OPTION = "v3_climate_start_route"
V3_CLIMATE_STATUS_OPTION = "v3_climate_status_route"
V3_ENABLED = "v3_climate"
V3_DEFAULT = "v2"

# Explicit selectors are bounded to previously reviewed adapters; they cannot
# redirect bearer tokens to an arbitrary host or execute custom code.
START_OPTIONS = (
    "auto",
    "cariad.climate.start.stored",
    "cariad.climate.start.vehicle_settings",
)
STATUS_OPTIONS = ("auto", "cariad.climate.status.batch")


def catalog_path() -> Path:
    return Path(__file__).with_name("climate.json")


def context_for(vehicle: Any, config_entry: Any) -> VehicleContext:
    service = getattr(vehicle, "_audi_service", None)
    auth = "auth0" if getattr(service, "uses_auth0", False) else "legacy"
    car_type = getattr(vehicle, "car_type", None)
    if not isinstance(car_type, str):
        car_type = ""
    source = getattr(vehicle, "model_source", None)
    family = getattr(vehicle, "model_family", None)
    if source not in ("audi_long_name", "audi_short_name") or not isinstance(family, str):
        family = ""
    return VehicleContext(
        auth=auth,
        region=str(config_entry.data.get("region") or "").upper(),
        vehicle_type=car_type.strip().lower(),
        model_family=family.strip().lower(),
    )


class V3Runtime:
    """Vehicle-scoped route selection with local, non-identifying diagnostics."""

    def __init__(self, registry: CapabilityRegistry, config_entry: Any) -> None:
        self.registry = registry
        self.config_entry = config_entry
        # VIN is an INTERNAL lookup key and never appears in exported diagnostics.
        self._evidence: dict[str, dict[str, RouteEvidence]] = {}

    def _evidence_for(self, vehicle: Any) -> dict[str, RouteEvidence]:
        return self._evidence.setdefault(vehicle.vin.lower(), {})

    def resolve(self, vehicle: Any, aspect: str) -> dict[str, Any]:
        context = context_for(vehicle, self.config_entry)
        setting = (
            V3_CLIMATE_STATUS_OPTION if aspect == "status"
            else V3_CLIMATE_START_OPTION
        )
        preferred = self.config_entry.options.get(setting, "auto")
        if aspect == "stop":
            preferred = "auto"
        if preferred == "auto":
            preferred = None
        return self.registry.resolve(
            "climate", aspect, context, self._evidence_for(vehicle),
            preferred=preferred, now=time.monotonic(),
        )

    def observe(self, data: list[Any]) -> None:
        """Called by the one HA cloud coordinator after its ordinary V2 poll.

        A normalized non-empty climate state proves the passive route was
        readable. No evidence is recorded for missing data or a cloud outage.
        """
        now = time.monotonic()
        for item in data:
            vehicle = getattr(item, "vehicle", None)
            if vehicle is None:
                continue
            state = getattr(vehicle, "climatisation_state", None)
            if not isinstance(state, str) or state.lower() in (
                "", "invalid", "error", "unsupported", "unknown", "unavailable"
            ):
                continue
            resolution = self.resolve(vehicle, "status")
            ident = resolution["operation"]
            if ident is not None:
                evidence = self._evidence_for(vehicle).setdefault(
                    ident, RouteEvidence()
                )
                evidence.record(200, usable=True, now=now)

    def diagnostics(self, vehicles: list[Any]) -> list[dict[str, Any]]:
        """Bounded redacted results; no VIN/model string/API response payload."""
        result = []
        for idx, vehicle in enumerate(vehicles[:10], 1):
            context = context_for(vehicle, self.config_entry)
            evidence = self._evidence_for(vehicle)
            result.append({
                "vehicle_slot": idx,
                "auth_family": context.auth,
                "region": context.region,
                "climate": {
                    aspect: self.resolve(vehicle, aspect)
                    for aspect in ("status", "start", "stop")
                },
                "read_evidence": {
                    ident: {
                        "readable_observations": item.readable,
                        "last_result": item.last_result,
                        "quarantined": item.suspended(time.monotonic()),
                    }
                    for ident, item in evidence.items()
                    if ident in self.registry.operations
                },
                "polling_owner": "single_v3_coordinator_v2_api_adapter",
            })
        return result
