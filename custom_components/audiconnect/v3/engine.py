"""V3-only discovery, polling and guided climate command owner.

No V2 account, vehicle model, legacy service calls, or V2 coordinator imports.
The auth facade is the only bridge to existing Audi credential code.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import time
from typing import Any

from .auth import V3Auth
from .development_profiles import DevelopmentProfile, DevelopmentProfileError
from .profile_store import V3ProfileStorage
from .registry import CapabilityRegistry
from .transport import V3Response, V3Transport
from .vehicle import V3Vehicle


def _captured(data: Any, path: str | None) -> str | None:
    """A status field's own timestamp, not HTTP receipt time."""
    if not path or not isinstance(data, dict):
        return None
    prefix = path.rsplit(".", 1)[0]
    value = data
    for key in prefix.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if not isinstance(value, dict):
        return None
    for key in ("carCapturedTimestamp", "timestamp"):
        if isinstance(value.get(key), str):
            return value[key]
    return None


class V3Engine:
    """One entry, one V3 session, one poller and independently editable profiles."""

    def __init__(
        self, hass: Any, entry: Any, registry: CapabilityRegistry,
        *, auth: V3Auth | None = None, transport: V3Transport | None = None,
        storage: V3ProfileStorage | None = None,
    ):
        self.hass, self.entry, self.registry = hass, entry, registry
        self.auth = auth or V3Auth(hass, entry)
        self.transport = transport or V3Transport(hass, self.auth)
        self.storage = storage or V3ProfileStorage(hass, entry.entry_id)
        self.vehicles: dict[str, V3Vehicle] = {}
        self.profiles: dict[str, DevelopmentProfile] = {}
        self.last_cloud_poll_success: datetime | None = None
        self.last_cloud_poll_attempt: datetime | None = None
        self._actions = asyncio.Lock()
        self._known_vehicle_inventory = False

    async def discover(self) -> None:
        """Own vehicle discovery. No V2 vehicle updates or extra poll task."""
        found = await self.transport.discover_vehicles()
        known: dict[str, V3Vehicle] = {}
        for item in found:
            try:
                parsed = V3Vehicle.from_graphql(item, self.auth.country)
            except ValueError:
                continue
            known[parsed.vin.lower()] = self.vehicles.get(parsed.vin.lower(), parsed)
        if not known:
            # Empty response might be a cloud bug or loss of scopes. Never
            # delete HA devices or learned API profiles based on an empty poll.
            if not self._known_vehicle_inventory:
                raise RuntimeError("V3 did not receive a usable vehicle inventory")
            return
        if not self.profiles:
            self.profiles = await self.storage.async_load(
                self.registry, {vin: vehicle.context for vin, vehicle in known.items()}
            )
        else:
            for vin, car in known.items():
                self.profiles.setdefault(
                    vin, DevelopmentProfile(self.registry, car.context)
                )
        self.vehicles.update(known)
        self._known_vehicle_inventory = True

    def _operation_request(
        self, vehicle: V3Vehicle, ident: str,
        params: dict[str, Any] | None = None,
    ) -> tuple[str, str, str, Any]:
        profile = self.profiles[vehicle.vin.lower()]
        if ident in profile.custom:
            preview = profile.preview_request(
                ident, vehicle_values={
                    "VIN": vehicle.vin, "COUNTRY": vehicle.country,
                    "TYPE": "Audi", "JOBS": "climatisation",
                }, user_values=params or {},
            )
            return (
                preview["family"], preview["method"],
                preview["relative_path"], preview["json_body"],
            )
        op = profile.registry.operations[ident]
        # This historical CARIAD variant is a read-modify-write settings
        # operation, not a bodyless command. Do not silently alias it to the
        # Q8 bodyless start. Developers can test explicit custom JSON routes.
        if ident == "cariad.climate.start.vehicle_settings":
            raise ValueError(
                "The stored-settings start adapter is not implemented in clean V3; "
                "add an explicit development route and test its payload first"
            )
        path = op["path"].format(
            VIN=vehicle.vin, COUNTRY=vehicle.country,
            TYPE="Audi", JOBS="climatisation",
        )
        return op["family"], op["method"], path, None

    async def poll(self) -> list[V3Vehicle]:
        self.last_cloud_poll_attempt = datetime.now(UTC)
        if not self._known_vehicle_inventory:
            await self.discover()
        for key, vehicle in self.vehicles.items():
            profile = self.profiles[key]
            routes = profile.registry.resolve(
                "climate", "status", vehicle.context
            )["available_operations"]
            chosen = profile.active.get("climate.status")
            if chosen in routes:
                routes.remove(chosen)
                routes.insert(0, chosen)
            attempted_paths: set[str] = set()
            # Bounded GET discovery, no auto wake and no repeated duplicate URL.
            for ident in routes[:3]:
                # A custom route with user parameters has no safe background
                # default until its input is explicitly persisted.
                if profile.custom.get(ident, {}).get("variables"):
                    continue
                op = profile.registry.operations[ident]
                if op["method"] != "GET" or op["family"] != "cariad":
                    continue
                family, method, path, _body = self._operation_request(vehicle, ident)
                if path in attempted_paths:
                    continue
                attempted_paths.add(path)
                try:
                    response = await self.transport.request(family, method, path)
                except (TimeoutError, OSError, RuntimeError):
                    break  # Network outage is not evidence of unsupported capability
                value, field = profile.registry.extract(ident, response.data)
                captured = _captured(response.data, field)
                valid = vehicle.set_climate(
                    value, captured, route=ident, observed_at=response.observed_at,
                    http_status=response.status,
                )
                if valid and 200 <= response.status < 300:
                    fresh = bool(captured)
                    profile.record_status(
                        "climate", ident, http_status=response.status,
                        schema_valid=True, fresh=fresh,
                    )
                    if fresh:
                        profile.choose_working("climate", "status", ident)
                    break
                profile.record_status(
                    "climate", ident, http_status=response.status,
                    schema_valid=False, fresh=False,
                )
                if response.status in (401, 403, 429) or response.status >= 500:
                    break
        self.last_cloud_poll_success = datetime.now(UTC)
        # One local write per scheduled discovery cycle; keep learned routes
        # and evidence across HA restarts without touching integration options.
        await self.storage.async_save(self.profiles)
        return list(self.vehicles.values())

    def require_vehicle(self, vin: str) -> V3Vehicle:
        vehicle = self.vehicles.get(vin.lower())
        if vehicle is None:
            raise ValueError("Vehicle is not part of this account")
        return vehicle

    def control_enabled(self, vin: str, aspect: str) -> bool:
        self.require_vehicle(vin)
        p = self.profiles[vin.lower()]
        return (
            f"climate.{aspect}" not in p.discovery.disabled
            and p.active.get(f"climate.{aspect}") is not None
            and p.control_results.get(p.active[f"climate.{aspect}"]) == "worked"
            and not p.custom.get(p.active[f"climate.{aspect}"], {}).get("variables")
        )

    async def test_action(
        self, vin: str, aspect: str, operation: str,
        *, params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """One user-triggered request; cannot automatically test next POST."""
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vin.lower()]
        if aspect not in ("start", "stop"):
            raise ValueError("Unsupported climate control")
        if not self.auth.uses_auth0:
            raise ValueError("V3 climate actions need Auth0")
        async with self._actions:
            # Reject invalid templates/parameters BEFORE reserving a pending
            # physical action, otherwise a mere validation error locks the car.
            family, method, path, body = self._operation_request(
                vehicle, operation, params
            )
            attempt = profile.begin_test(
                "climate", aspect, operation, now=time.time()
            )
            await self.storage.async_save(self.profiles)
            try:
                response = await self.transport.request(
                    family, method, path, body=body, explicit_action=True,
                )
                profile.observe_http(attempt.sequence, response.status)
            except (TimeoutError, OSError, RuntimeError):
                profile.observe_http(attempt.sequence, None)
                response = None
            await self.storage.async_save(self.profiles)
            return {
                "sequence": attempt.sequence, "operation": operation,
                "transport": attempt.transport,
                "status": response.status if response else None,
                "physical_result": "requires_user_confirmation",
            }

    async def review_action(
        self, vin: str, sequence: int, outcome: str,
    ) -> dict[str, Any]:
        profile = self.profiles[self.require_vehicle(vin).vin.lower()]
        if outcome not in ("worked", "failed", "uncertain"):
            raise ValueError("Unsupported outcome")
        profile.confirm(
            sequence,
            worked=None if outcome == "uncertain" else outcome == "worked",
            inspected_vehicle=outcome != "uncertain",
            now=time.time(),
        )
        if outcome == "worked":
            attempt = profile.discovery.history[-1]
            if not profile.custom.get(attempt.operation, {}).get("variables"):
                profile.choose_working(
                    "climate", attempt.action, attempt.operation
                )
        await self.storage.async_save(self.profiles)
        return {"confirmed": outcome, "active": dict(profile.active)}

    async def add_route(self, vin: str, route: dict[str, Any]) -> str:
        profile = self.profiles[self.require_vehicle(vin).vin.lower()]
        op = profile.add(route)
        await self.storage.async_save(self.profiles)
        return op


    async def test_status_route(
        self, vin: str, operation: str, *, params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """On-demand read-only GET test, with explicit response classification."""
        car = self.require_vehicle(vin)
        p = self.profiles[car.vin.lower()]
        allowed = p.registry.resolve(
            "climate", "status", car.context
        )["available_operations"]
        if operation not in allowed:
            raise ValueError("Status route not applicable to selected vehicle")
        family, method, path, body = self._operation_request(
            car, operation, params
        )
        if method != "GET" or family != "cariad" or body is not None:
            raise ValueError("Only reviewed CARIAD GET discovery is available")
        response = await self.transport.request(family, method, path)
        field_value, field = p.registry.extract(operation, response.data)
        timestamp = _captured(response.data, field)
        valid = car.set_climate(
            field_value, timestamp, route=operation,
            observed_at=response.observed_at, http_status=response.status,
        )
        fresh = bool(timestamp and valid)
        verdict = p.record_status(
            "climate", operation, http_status=response.status,
            schema_valid=valid, fresh=fresh,
        )
        if verdict == "worked" and not p.custom.get(operation, {}).get("variables"):
            p.choose_working("climate", "status", operation)
        await self.storage.async_save(self.profiles)
        return {
            "http_status": response.status,
            "field": field,
            "value": car.climate_state if valid else None,
            "captured": car.climate_captured.isoformat()
            if car.climate_captured and timestamp else None,
            "result": verdict,
            "schema_keys": sorted(response.data.keys())[:20]
            if isinstance(response.data, dict) else [],
        }

    async def select_working(self, vin: str, aspect: str, operation: str) -> None:
        """Admin selects another previously verified route; no request."""
        car = self.require_vehicle(vin)
        p = self.profiles[car.vin.lower()]
        if p.custom.get(operation, {}).get("variables"):
            raise DevelopmentProfileError(
                "Dynamic parameters are test-only until V3 can save the input profile"
            )
        p.choose_working("climate", aspect, operation)
        await self.storage.async_save(self.profiles)

    async def disable_action(self, vin: str, aspect: str) -> None:
        p = self.profiles[self.require_vehicle(vin).vin.lower()]
        p.disable("climate", aspect)
        await self.storage.async_save(self.profiles)

    async def send_control(self, vin: str, aspect: str) -> None:
        """Normal climate UI sends only a previously verified selected route."""
        car = self.require_vehicle(vin)
        if self.profiles[vin.lower()].discovery._active is not None:
            raise RuntimeError(
                "A climate experiment is awaiting physical confirmation"
            )
        if not self.control_enabled(vin, aspect):
            raise RuntimeError("Climate command has not been tested and activated")
        p = self.profiles[vin.lower()]
        ident = p.active[f"climate.{aspect}"]
        # Never retry or switch routes on unconfirmed physical action.
        _family, _method, _path, _body = self._operation_request(car, ident)
        response = await self.transport.request(
            _family, _method, _path, body=_body, explicit_action=True,
        )
        car.last_command_result = (
            "accepted_unconfirmed" if 200 <= response.status < 300
            else f"request_failed_{response.status}"
        )
        if not 200 <= response.status < 300:
            raise RuntimeError("Audi rejected the selected climate command")

    def diagnostics(self) -> dict[str, Any]:
        """No VIN, tokens, literal user routes, response bodies or coordinates."""
        vehicles = []
        for index, car in enumerate(self.vehicles.values(), 1):
            p = self.profiles.get(car.vin.lower())
            vehicles.append({
                "vehicle_slot": index,
                "context": {
                    "auth": "auth0" if self.auth.uses_auth0 else "legacy",
                    "region": car.country, "model_family": car.model_family,
                },
                "climate": {
                    "readable": car.climate_state is not None,
                    "capture_age_minutes": car.capture_age_minutes,
                    "selected_status": p.active.get("climate.status") if p else None,
                    "start_enabled": self.control_enabled(car.vin, "start") if p else False,
                    "stop_enabled": self.control_enabled(car.vin, "stop") if p else False,
                    "candidate_count": len(p.registry.operations_for("climate", "status"))
                    if p else 0,
                },
            })
        return {
            "mode": "v3", "polling_owner": "independent_v3_discovery_engine",
            "requests": self.transport.request_count,
            "last_poll_success": self.last_cloud_poll_success.isoformat()
            if self.last_cloud_poll_success else None,
            "quota_remaining": self.transport.remaining_calls,
            "vehicles": vehicles,
        }
