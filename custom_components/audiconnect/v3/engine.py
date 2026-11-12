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
from .response_preview import safe_response_preview
from .api_observations import record_for, save_record
from .registry import CapabilityRegistry
from .transport import V3Response, V3Transport
from .vehicle import V3Vehicle
from .freshness import timestamp_is_fresh
from .attribute_runtime import planned_jobs, observe_read_only, _accept_observation
from .attribute_routes import get_read_variant, read_variants, validate_custom_read_route
from .historical_catalog import ATTRIBUTES, capture_time, read_path
from .legacy_read_mappings import FIELDS as MBB_FIELDS
from .legacy_read_mappings import ROUTES as MBB_ROUTES
from .api_value_mappings import normalize_api_value
from .historical_catalog import V2_JOBS
from .read_discovery import record_jobs, pending_groups, reserve_group, summary as discovery_summary
from ..const import CONF_FILTER_VINS


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
        self._normal_action_at: dict[str, float] = {}
        self._wake_attempts: dict[str, list[float]] = {}
        self._known_vehicle_inventory = False
        self._poll_cycles = 0

    async def discover(self) -> None:
        """Own vehicle discovery. No V2 vehicle updates or extra poll task."""
        found = await self.transport.discover_vehicles()
        options = getattr(self.entry, "options", {})
        data = getattr(self.entry, "data", {})
        excluded = {x.strip().lower() for x in str(options.get(
            CONF_FILTER_VINS, data.get(CONF_FILTER_VINS, "")
        )).split(",") if x.strip()}
        known: dict[str, V3Vehicle] = {}
        for item in found:
            try:
                parsed = V3Vehicle.from_graphql(item, self.auth.country)
            except ValueError:
                continue
            if parsed.vin.lower() in excluded:
                continue
            vehicle = self.vehicles.get(parsed.vin.lower(), parsed)
            vehicle.auth_family = "auth0" if self.auth.uses_auth0 else "legacy"
            known[parsed.vin.lower()] = vehicle
        if not known:
            if found and excluded:
                self._known_vehicle_inventory = True
                return
            # Empty response might be a cloud bug or loss of scopes. Never
            # delete HA devices or learned API profiles based on an empty poll.
            if not self._known_vehicle_inventory:
                raise RuntimeError("V3 did not receive a usable vehicle inventory")
            return
        # Returning/new cars must restore saved evidence, not start blank.
        missing = {vin: car.context for vin, car in known.items()
                   if vin not in self.profiles}
        if missing:
            self.profiles.update(
                await self.storage.async_load(self.registry, missing)
            )
        self.vehicles.update(known)
        self._known_vehicle_inventory = True

    def _resolve_secure_body(
        self, vehicle: V3Vehicle, ident: str, family: str,
        method: str, path: str, body: Any,
    ) -> Any:
        """Resolve credentials last, exclusively for reviewed door controls.

        Secret values are never part of route definitions, local profiles,
        response previews or WebSocket payloads. No URL substitutions.
        """
        if "{SPIN}" not in str(body):
            return body
        profile = self.profiles[vehicle.vin.lower()]
        built_in = ident in ("cariad.access.lock", "cariad.access.unlock")
        custom = profile.custom.get(ident)
        is_reviewed = built_in or (
            custom is not None
            and custom["capability"] == "access"
            and custom["aspect"] in ("lock", "unlock")
        )
        allowed_paths = {
            f"/vehicle/v1/vehicles/{vehicle.vin}/access/lock",
            f"/vehicle/v1/vehicles/{vehicle.vin}/access/unlock",
        }
        if (not is_reviewed or family != "cariad" or method != "POST"
                or path not in allowed_paths or body != {"spin": "{SPIN}"}):
            raise ValueError("Secure S-PIN template is not permitted for this command")
        spin = getattr(getattr(self.auth, "service", None), "_spin", None)
        if not isinstance(spin, str) or not spin:
            raise ValueError("Configure an Audi S-PIN to use remote door controls")
        return {"spin": spin}

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
                preview["relative_path"], self._resolve_secure_body(
                    vehicle, ident, preview["family"], preview["method"],
                    preview["relative_path"], preview["json_body"],
                ),
            )
        op = profile.registry.operations[ident]
        if op.get("request_mode") == "verified_vehicle_target":
            raise ValueError("Pilot stored-settings adapter not implemented; use the full V3 catalog")
        path = op["path"].format(
            VIN=vehicle.vin, COUNTRY=vehicle.country,
            TYPE="Audi", JOBS=",".join(planned_jobs(vehicle, profile)),
        )
        body = op.get("request_body")
        if op.get("request_mode") == "secure_spin" and body is None:
            body = {"spin": "{SPIN}"}  # Support older immutable catalogs.
        return op["family"], op["method"], path, self._resolve_secure_body(
            vehicle, ident, op["family"], op["method"], path, body
        )

    async def _command_request(self, car: V3Vehicle, ident: str,
                               params: dict[str, Any] | None = None):
        family, method, path, body = self._operation_request(car, ident, params)
        op = self.profiles[car.vin.lower()].registry.operations[ident]
        mode = op.get("request_mode")
        if mode in {"charging_settings_update", "charge_mode",
                    "charging_profile_update", "climate_settings_update",
                    "climate_start_settings", "flash", "auxiliary_start"}:
            from .command_payloads import build
            body = await build(self, car, mode, params or {})
        return family, method, path, body

    def _api_record(self, profile: DevelopmentProfile, operation: str,
                    family: str, method: str, response: V3Response | None,
                    vin: str) -> None:
        save_record(profile, operation, record_for(
            family=family, method=method,
            http_status=response.status if response else None,
            payload=response.data if response else None, vin=vin,
            at=response.observed_at if response else None,
        ))

    async def test_family_reads(self, vin: str, family: str) -> dict[str, Any]:
        """Explicit, bounded read-only API-family sweep, never remote commands.

        CARIAD: one 23-job GET plus at most two targeted mapped GET groups.
        Legacy MBB: at most charger and climater GETs, only for legacy auth.
        The API cloud budget remains enforced by V3Transport.
        """
        vehicle = self.require_vehicle(vin)
        expected = "mbb" if vehicle.context.auth == "legacy" else "cariad"
        if family != expected:
            raise ValueError("API family is not applicable to this vehicle")
        profile = self.profiles[vehicle.vin.lower()]
        outcomes: list[dict[str, Any]] = []
        if self.transport.remaining_calls is not None and self.transport.remaining_calls <= 12:
            raise RuntimeError("Audi quota is low; read-only scan has been suspended")
        if family == "cariad":
            plans = [("cariad.discovery.full",
                      "/vehicle/v1/vehicles/" + vehicle.vin
                      + "/selectivestatus?jobs=" + ",".join(V2_JOBS),
                      tuple(V2_JOBS))]
        else:
            plans = [(f"mbb.discovery.{kind}",
                      template.format(VIN=vehicle.vin, TYPE="Audi", COUNTRY=vehicle.country),
                      ()) for kind, template in MBB_ROUTES.items()]
        async def run_one(route_id: str, path: str, jobs: tuple[str, ...]) -> bool:
            if self.transport.remaining_calls is not None and self.transport.remaining_calls <= 12:
                return False
            try:
                response = await self.transport.request(family, "GET", path)
            except (TimeoutError, OSError, RuntimeError, ValueError):
                self._api_record(profile, route_id, family, "GET", None, vehicle.vin)
                outcomes.append({"operation": route_id, "http_status": None,
                                 "result": "transport_uncertain"})
                return False
            self._api_record(profile, route_id, family, "GET", response, vehicle.vin)
            outcome = "http_ok" if 200 <= response.status < 300 else "http_error"
            if family == "cariad":
                record_jobs(profile, jobs, status=response.status, payload=response.data)
                if outcome == "http_ok":
                    observe_read_only(vehicle, profile, response.data, response.observed_at)
            elif outcome == "http_ok":
                kind = route_id.rsplit(".", 1)[-1]
                for attribute, (mapped_kind, field) in MBB_FIELDS.items():
                    if kind == mapped_kind:
                        self._record_attribute_response(
                            vehicle, profile, attribute, f"mbb.{kind}.readonly",
                            [field], response,
                        )
            outcomes.append({"operation": route_id, "http_status": response.status,
                             "result": outcome})
            return outcome == "http_ok"
        for ident, path, jobs in plans:
            if not await run_one(ident, path, jobs):
                break
        if family == "cariad" and outcomes and outcomes[0]["result"] == "http_ok":
            for group in pending_groups(profile, max_groups=2):
                path = (f"/vehicle/v1/vehicles/{vehicle.vin}/selectivestatus?jobs="
                        + ",".join(group))
                if not await run_one("cariad.discovery." + "_".join(group), path, group):
                    break
                reserve_group(profile, group)
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()
        return {
            "family": family, "request_count": len(outcomes),
            "results": outcomes, "readable_attributes": len(vehicle.readings),
            "note": "Only safe GET requests were sent. Stale cloud data is not current vehicle data.",
        }

    def api_results_for(self, vin: str, family: str = "all") -> list[dict[str, Any]]:
        car = self.require_vehicle(vin)
        if family not in ("all", "cariad", "mbb", "graphql"):
            raise ValueError("Unknown API family")
        profile = self.profiles[car.vin.lower()]
        return [
            {"operation": ident, **record}
            for ident, record in reversed(list(profile.api_observations.items()))
            if family == "all" or record["family"] == family
        ]

    async def poll(self) -> list[V3Vehicle]:
        self.last_cloud_poll_attempt = datetime.now(UTC)
        self._poll_cycles += 1
        if not self._known_vehicle_inventory or self._poll_cycles % 24 == 0:
            await self.discover()
        cloud_reachable = False
        # Reuse identical GET responses across capabilities on the same car.
        # API family + VIN + exact path is the request identity; a route change
        # must never trigger a second call for a response already in this poll.
        polled_responses: dict[tuple[str, str, str], V3Response] = {}
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
            attempted_operations: set[str] = set()
            # Bounded GET discovery, no auto wake and no repeated duplicate URL.
            for ident in routes[:3]:
                # A custom route with user parameters has no safe background
                # default until its input is explicitly persisted.
                if profile.custom.get(ident, {}).get("variables"):
                    continue
                op = profile.registry.operations[ident]
                if op["method"] != "GET" or op["family"] not in ("cariad", "mbb"):
                    continue
                # MBB legacy variants have distinct semantics and may cost a
                # request each. Never try manual-only endpoints on every poll.
                if (op["family"] == "mbb" and op.get("delivery") == "manual"
                    and profile.active.get("climate.status") != ident):
                    continue
                family, method, path, _body = self._operation_request(vehicle, ident)
                # The default targeted climate probe repeats a job already
                # included in the shared batch. Do not double-poll it merely
                # because the URL spells the same job list differently.
                if (ident == "cariad.climate.status.probe"
                    and op["path"].endswith("?jobs=climatisation")
                    and "cariad.climate.status.batch" in attempted_operations
                    and vehicle.climate_state is not None):
                    continue
                if path in attempted_paths:
                    continue
                attempted_paths.add(path)
                attempted_operations.add(ident)
                try:
                    response = await self.transport.request(family, method, path)
                except (TimeoutError, OSError, RuntimeError, ValueError):
                    break  # Auth/transport failure is not proof of unsupported vehicle
                polled_responses[(key, family, path)] = response
                self._api_record(profile, ident, family, method, response, vehicle.vin)
                if 200 <= response.status < 300:
                    cloud_reachable = True
                    if ident == 'cariad.climate.status.batch':
                        requested = tuple(path.rsplit("jobs=", 1)[-1].split(","))
                        observe_read_only(vehicle, profile, response.data, response.observed_at)
                        record_jobs(profile, requested, status=response.status, payload=response.data)
                    elif ident == 'mbb.climate.status':
                        # Parse only proven V2 paths; per-attribute activation
                        # remains explicit because MBB timestamps may be absent.
                        for attr, (kind, _field) in MBB_FIELDS.items():
                            if kind == "climater":
                                self._record_attribute_response(
                                    vehicle, profile, attr, "mbb.climater.readonly",
                                    [_field], response,
                                )
                value, field = profile.registry.extract(ident, response.data)
                captured = _captured(response.data, field)
                valid = (
                    200 <= response.status < 300
                    and vehicle.set_climate(
                        value, captured, route=ident,
                        observed_at=response.observed_at, http_status=response.status,
                    )
                )
                if valid:
                    vehicle.climate_field = field
                    fresh = timestamp_is_fresh(captured, response.observed_at)
                    profile.record_status(
                        "climate", ident, http_status=response.status,
                        schema_valid=True, fresh=fresh,
                    )
                    if fresh:
                        profile.choose_working("climate", "status", ident)
                        break
                    # A stale value can lead to another distinct bounded GET.
                    continue
                profile.record_status(
                    "climate", ident, http_status=response.status,
                    schema_valid=False, fresh=False,
                )
                if response.status in (401, 403, 429) or response.status >= 500:
                    break
        # Automatic initial CARIAD discovery: the existing 23-job GET handles
        # most fields. If that response missed known mappings, probe at most
        # two small job groups immediately and one group on later polls.
        # No POST, no wake, no parking coordinates, no unbounded API probing.
        for key, car in self.vehicles.items():
            profile = self.profiles[key]
            if car.context.auth != "auth0" or len(profile.registry.capabilities) <= 1:
                continue  # Pilot-only synthetic tests and legacy cars are unaffected.
            if not profile.job_discovery:
                continue  # No successful bulk GET yet; don't spray blind requests.
            initial = not profile.job_probe_attempts
            if not initial and self._poll_cycles % 6 != 0:
                continue  # Subsequent evidence refresh is deliberately slow.
            max_extra = 2 if initial else 1
            for jobs in pending_groups(profile, max_groups=max_extra):
                if self.transport.remaining_calls is not None and self.transport.remaining_calls <= 12:
                    break
                path = f"/vehicle/v1/vehicles/{car.vin}/selectivestatus?jobs={','.join(jobs)}"
                try:
                    response = await self.transport.request("cariad", "GET", path)
                except (TimeoutError, OSError, RuntimeError, ValueError):
                    break
                if response.status in (401, 403, 429) or response.status >= 500:
                    record_jobs(profile, jobs, status=response.status, payload=response.data)
                    break
                reserve_group(profile, jobs)
                self._api_record(profile, "cariad.discovery." + "_".join(jobs),
                                 "cariad", "GET", response, car.vin)
                if 200 <= response.status < 300:
                    cloud_reachable = True
                    observe_read_only(car, profile, response.data, response.observed_at)
                record_jobs(profile, jobs, status=response.status, payload=response.data)
                polled_responses[(key, "cariad", path)] = response

        # Explicitly selected targeted/custom GET routes are executed separately
        # from the default shared batch, deduplicated across attributes.
        for key, car in self.vehicles.items():
            profile = self.profiles[key]
            unique: dict[tuple[str, str], list[tuple[str, str, list[str]]]] = {}
            for ident, route in profile.attribute_routes.items():
                if route == "cariad.selectivestatus.batch":
                    continue
                family, path, mappings = self._attribute_request(car, profile, ident, route)
                unique.setdefault((family, path), []).append((ident, route, mappings))
            # Refuse an unbounded per-attribute request explosion.
            for (family, path), selected in list(unique.items())[:4]:
                if family not in ("cariad", "mbb"):
                    continue
                response = polled_responses.get((key, family, path))
                if response is None:
                    try:
                        response = await self.transport.request(family, "GET", path)
                    except (TimeoutError, OSError, RuntimeError, ValueError):
                        break
                    polled_responses[(key, family, path)] = response
                for ident, route, mappings in selected:
                    self._api_record(profile, route, family, "GET", response, car.vin)
                for ident, route, mappings in selected:
                    self._record_attribute_response(car, profile, ident, route, mappings, response)
                if 200 <= response.status < 300:
                    cloud_reachable = True
        # Retain the V2 GPS tracker contract without adding a new cloud poller.
        if self._poll_cycles == 1 or self._poll_cycles % 12 == 0:
            await self._poll_parked_positions()
        if cloud_reachable:
            self.last_cloud_poll_success = datetime.now(UTC)
        # One local write per scheduled discovery cycle; keep learned routes
        # and evidence across HA restarts without touching integration options.
        await self.storage.async_save(self.profiles)
        return list(self.vehicles.values())

    async def _poll_parked_positions(self) -> None:
        """Infrequent GET for the user's existing Audi parked GPS tracker.

        No coordinates in API evidence, diagnostics or profile storage.
        """
        if not hasattr(self.hass, "data"):
            return  # synthetic test engines without the HA registry
        from homeassistant.helpers import entity_registry as er
        from .parking import parse_parked_position, keep_newest_position

        registry = er.async_get(self.hass)
        permitted = {
            entity.unique_id
            for entity in er.async_entries_for_config_entry(
                registry, self.entry.entry_id
            )
            if entity.domain == "device_tracker"
            and entity.disabled_by is None
        }
        for car in self.vehicles.values():
            if (car.context.auth != "auth0"
                    or f"{car.vin.lower()}_device_tracker_position" not in permitted):
                continue
            if (self.transport.remaining_calls is not None
                    and self.transport.remaining_calls <= 12):
                return
            try:
                reply = await self.transport.request(
                    "cariad", "GET",
                    f"/vehicle/v1/vehicles/{car.vin}/parkingposition",
                )
            except (TimeoutError, OSError, RuntimeError, ValueError):
                return
            if reply.status in (401, 403, 429) or reply.status >= 500:
                return
            if not 200 <= reply.status < 300:
                continue
            point = parse_parked_position(reply.data)
            if point and keep_newest_position(car.position, point):
                car.position = point

    def require_vehicle(self, vin: str) -> V3Vehicle:
        vehicle = self.vehicles.get(vin.lower())
        if vehicle is None:
            raise ValueError("Vehicle is not part of this account")
        return vehicle

    def control_routes_for(self, vin: str, capability: str, action: str) -> dict[str, Any]:
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        applicable = profile.registry.resolve(capability, action, vehicle.context)["available_operations"]
        routes = [
            {
                "id": op, "family": profile.registry.operations[op]["family"],
                "method": "POST", "path": profile.registry.operations[op]["path"],
                "status": profile.control_results.get(op, "not_tested"),
                "active": profile.active.get(f"{capability}.{action}") == op,
            }
            for op in applicable if profile.registry.operations[op]["method"] == "POST"
        ]
        in_progress = profile.discovery._active
        return {
            "capability": capability, "action": action,
            "routes": routes, "active": profile.active.get(f"{capability}.{action}"),
            "pending": in_progress.public() if in_progress else None,
            "requires": "S-PIN and physical verification" if capability == "access"
                        else "Physical verification of the car",
        }

    async def disable_control(self, vin: str, capability: str, action: str) -> None:
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        profile.disable(capability, action)
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()

    def _command_route(self, vin: str, aspect: str, capability: str) -> str | None:
        car = self.require_vehicle(vin)
        p = self.profiles[vin.lower()]
        key = f"{capability}.{aspect}"
        if key in p.discovery.disabled or p.discovery._active is not None:
            return None
        ident = p.active.get(key)
        if ident and p.control_results.get(ident) == "worked" and not p.custom.get(ident, {}).get("variables"):
            return ident
        if car.context.auth != "auth0" or len(p.registry.capabilities) <= 1:
            return None
        # Historical V2 routes, not exploratory alternatives, are selectable
        # on the vehicle's own declared capability or reviewed status shape.
        # A previous failed physical experiment overrides defaults.
        from .command_policy import eligible_operation
        ident = eligible_operation(car, self.auth, capability, aspect)
        if not ident or p.control_results.get(ident) == "failed":
            return None
        try:
            if ident in p.registry.resolve(capability, aspect, car.context)["available_operations"]:
                return ident
        except ValueError:
            pass
        return None

    def control_enabled(self, vin: str, aspect: str, capability: str = "climate") -> bool:
        return self._command_route(vin, aspect, capability) is not None

    def _reserve_wake(self, vin: str, operation: str) -> None:
        if operation not in ("cariad.remote.wake", "cariad.remote.refresh"):
            return
        remaining = getattr(self.transport, "remaining_calls", None)
        if remaining is not None and remaining <= 12:
            raise RuntimeError("Audi wake quota reserve reached")
        now = time.monotonic()
        attempts = self._wake_attempts.setdefault(vin.lower(), [])
        attempts[:] = [x for x in attempts if now - x < 86400]
        if len(attempts) >= 4 or (attempts and now - attempts[-1] < 1800):
            raise RuntimeError("Audi wake budget: 30 minutes and four attempts per 24 hours")
        attempts.append(now)

    async def test_action(
        self, vin: str, aspect: str, operation: str,
        *, params: dict[str, Any] | None = None, capability: str = "climate",
    ) -> dict[str, Any]:
        """One user-triggered control request, never automatic POST discovery."""
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vin.lower()]
        if not self.auth.uses_auth0:
            raise ValueError("CARIAD vehicle controls need Auth0")
        if operation not in profile.registry.resolve(
            capability, aspect, vehicle.context
        )["available_operations"]:
            raise ValueError("Control not applicable to this car")
        if profile.registry.operations[operation]["method"] not in ("POST", "PUT"):
            raise ValueError("Read-only operation cannot be a control")
        async with self._actions:
            # Reject invalid templates/parameters BEFORE reserving a pending
            # physical action, otherwise a mere validation error locks the car.
            family, method, path, body = await self._command_request(
                vehicle, operation, params
            )
            self._reserve_wake(vehicle.vin, operation)
            attempt = profile.begin_test(
                capability, aspect, operation, now=time.time()
            )
            await self.storage.async_save(self.profiles)
            try:
                response = await self.transport.request(
                    family, method, path, body=body, explicit_action=True,
                )
                profile.observe_http(attempt.sequence, response.status)
                self._api_record(profile, operation, family, method, response, vehicle.vin)
            except (TimeoutError, OSError, RuntimeError):
                profile.observe_http(attempt.sequence, None)
                response = None
                self._api_record(profile, operation, family, method, None, vehicle.vin)
            await self.storage.async_save(self.profiles)
            return {
                "sequence": attempt.sequence, "operation": operation,
                "transport": attempt.transport,
                "status": response.status if response else None,
                "response_preview": None if capability == "access" else safe_response_preview(
                    response.data if response else None,
                    vehicle_vin=vehicle.vin,
                ),
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
                    attempt.capability, attempt.action, attempt.operation
                )
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()
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
        self._api_record(p, operation, family, "GET", response, car.vin)
        field_value, field = p.registry.extract(operation, response.data)
        timestamp = _captured(response.data, field)
        valid = (
            200 <= response.status < 300
            and car.set_climate(
                field_value, timestamp, route=operation,
                observed_at=response.observed_at, http_status=response.status,
            )
        )
        if valid:
            car.climate_field = field
        fresh = bool(valid and timestamp_is_fresh(timestamp, response.observed_at))
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
            "response_preview": safe_response_preview(
                response.data, vehicle_vin=car.vin
            ),
        }

    async def save_candidate(
        self, vin: str, aspect: str, operation: str,
    ) -> None:
        """Save a planned test route without exposing unproven vehicle controls."""
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        profile.save_candidate("climate", aspect, operation)
        await self.storage.async_save(self.profiles)

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

    async def send_control(
        self, vin: str, aspect: str, capability: str = "climate",
        *, params: dict[str, Any] | None = None,
    ) -> None:
        """Normal climate UI sends ONE verified request, never retries.

        A per-vehicle cooldown limits duplicate climate requests while the car
        synchronizes with Audi. HTTP acceptance is not physical confirmation.
        """
        car = self.require_vehicle(vin)
        p = self.profiles[vin.lower()]
        async with self._actions:
            if p.discovery._active is not None:
                raise RuntimeError(
                    "A vehicle control experiment is awaiting physical confirmation"
                )
            if not self.control_enabled(vin, aspect, capability):
                raise RuntimeError(
                    "Vehicle command has not been tested and activated"
                )
            now = time.monotonic()
            if now - self._normal_action_at.get(vin.lower(), -1e12) < 90:
                raise RuntimeError(
                    "Vehicle command cooldown active; verify vehicle state"
                )
            ident = self._command_route(vin, aspect, capability)
            if ident is None:
                raise RuntimeError("No eligible Audi command route")
            family, method, path, body = await self._command_request(car, ident, params)
            self._reserve_wake(vin, ident)
            self._normal_action_at[vin.lower()] = now
            try:
                response = await self.transport.request(
                    family, method, path, body=body, explicit_action=True
                )
            except (TimeoutError, OSError, RuntimeError) as err:
                self._api_record(p, ident, family, method, None, car.vin)
                await self.storage.async_save(self.profiles)
                car.last_command_result = "transport_uncertain"
                raise RuntimeError(
                    "Audi command outcome uncertain; check the car"
                ) from err
            self._api_record(p, ident, family, method, response, car.vin)
            await self.storage.async_save(self.profiles)
            if not 200 <= response.status < 300:
                car.last_command_result = f"request_failed_{response.status}"
                raise RuntimeError("Audi rejected the selected vehicle command")
            car.last_command_result = "accepted_unconfirmed"
            if family == "cariad":
                from .request_status import confirm, request_id_of
                request_id = request_id_of(response.data)
                if request_id is not None:
                    outcome = await confirm(self.transport, car.vin, request_id)
                    car.last_command_result = outcome
                    if outcome == "rejected":
                        raise RuntimeError(
                            "Audi vehicle rejected the command; no automatic retry"
                        )
            # Even 'backend_completed' means command execution confirmed by
            # Audi's backend, not proof of actual vehicle state. Scheduled
            # V3 read-only polling remains the physical state source.


    async def send_setting(self, vin: str, kind: str, value: Any) -> None:
        """Typed V3-owned write through an explicitly verified route.

        This method cannot invoke V2. OEM method, path and body are owned by
        the active declarative V3 operation.
        """
        if kind == "set_target_soc":
            if (isinstance(value, bool) or not isinstance(value, int)
                    or value not in range(20, 101, 5)):
                raise ValueError("Audi target SoC must be 20..100 in steps of 5")
        elif kind == "set_charge_mode":
            if value not in ("manual", "timer"):
                raise ValueError("Audi charge mode must be manual or timer")
        else:
            raise ValueError("Unsupported V3 setting")
        await self.send_control(vin, kind, "charging", params={"value": value})

    def attribute_routes_for(self, vin: str, attribute: str) -> dict[str, Any]:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        alternatives = [r for r in read_variants(attribute, profile.attribute_custom)
                        if r["family"] == ("mbb" if car.context.auth == "legacy" else "cariad")]
        for variant in alternatives:
            evidence = profile.attribute_route_evidence.get(attribute, {}).get(variant["id"], {})
            variant["result"] = evidence.get("outcome", "not_tested")
            variant["active"] = profile.attribute_routes.get(attribute) == variant["id"]
        return {
            "attribute": attribute, "capability": ATTRIBUTES[attribute]["capability"],
            "routes": alternatives, "active": profile.attribute_routes.get(attribute),
            "draft": profile.attribute_drafts.get(attribute),
        }

    async def add_attribute_route(self, vin: str, definition: dict[str, Any]) -> str:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        route = validate_custom_read_route(definition)
        if route["id"] in profile.attribute_custom:
            raise ValueError("Choose a new custom route identifier")
        if len(profile.attribute_custom) >= 50:
            raise ValueError("Too many custom routes")
        profile.attribute_custom[route["id"]] = route
        await self.storage.async_save(self.profiles)
        return route["id"]

    def _attribute_request(self, car: V3Vehicle, profile: DevelopmentProfile,
                           attribute: str, operation: str) -> tuple[str, str, list[str]]:
        route = get_read_variant(attribute, operation, profile.attribute_custom)
        path = (route["path"].replace("{VIN}", car.vin)
                .replace("{TYPE}", "Audi").replace("{COUNTRY}", car.country))
        if "{JOBS}" in path:
            jobs = list(planned_jobs(car, profile))
            required = ATTRIBUTES[attribute]["job"]
            # Manual discovery of a missing attribute must include its own job,
            # even if the regular vehicle poll already pruned unobserved jobs.
            if required and required not in jobs:
                jobs.append(required)
            path = path.replace("{JOBS}", ",".join(jobs))
        return route["family"], path, route["response_paths"]

    def _record_attribute_response(self, car: V3Vehicle, profile: DevelopmentProfile,
                                   attribute: str, operation: str, mappings: list[str],
                                   response: V3Response) -> dict[str, Any]:
        matched = next(
            ((path, read_path(response.data, path)) for path in mappings
             if read_path(response.data, path) is not None), None
        )
        field, value = matched if matched is not None else (mappings[0], None)
        # Some Audi APIs return HTTP 200/207 with an invalid or error-coded
        # value. Never promote "unknown" to a configured or usable entity.
        if isinstance(value, str) and value.strip().lower() in (
            "", "unknown", "unsupported", "invalid", "unavailable", "error", "notavailable"
        ):
            value = None
        if isinstance(value, dict) and (
            "error" in value or not value
        ):
            value = None
        if isinstance(value, list) and not value:
            value = None
        variant = get_read_variant(attribute, operation, profile.attribute_custom)
        family = variant["family"]
        try:
            value = normalize_api_value(value, variant.get("conversion"))
        except ValueError:
            value = None
        captured = capture_time(response.data, field) if value is not None else None
        fresh = timestamp_is_fresh(captured, response.observed_at)
        if not 200 <= response.status < 300:
            outcome = "api_error"
        elif value is None:
            outcome = "mapping_missing"
        else:
            outcome = "verified" if fresh else "readable_but_stale"
        profile.attribute_route_evidence.setdefault(attribute, {})[operation] = {
            "outcome": outcome, "path": field, "http_status": response.status,
        }
        if 200 <= response.status < 300 and value is not None and len(str(value)) <= 10000:
            last = car.readings.get(attribute)
            if _accept_observation(last, captured):
                car.readings[attribute] = {
                    "value": value, "captured": captured,
                    "observed": response.observed_at.isoformat(),
                    "fresh": fresh, "path": field, "job": ATTRIBUTES[attribute]["job"],
                    "status": outcome, "family": family,
                }
            profile.attribute_evidence[attribute] = {
                "status": outcome, "path": field,
                "job": ATTRIBUTES[attribute]["job"],
                "source": "mbb.legacy" if family == "mbb" else "cariad.selectivestatus",
                "timestamp_present": bool(captured),
            }
        return {
            "attribute": attribute, "route": operation, "result": outcome,
            "http_status": response.status, "mapping": field,
            "captured": captured, "value": value if isinstance(value, (str, int, float, bool)) else None,
        }

    async def test_attribute_route(self, vin: str, attribute: str, route: str) -> dict[str, Any]:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        family, path, mappings = self._attribute_request(car, profile, attribute, route)
        if family != ("mbb" if car.context.auth == "legacy" else "cariad"):
            raise ValueError("Read route is not applicable to this vehicle API family")
        response = await self.transport.request(family, "GET", path)
        self._api_record(profile, route, family, "GET", response, car.vin)
        result = self._record_attribute_response(car, profile, attribute, route, mappings, response)
        await self.storage.async_save(self.profiles)
        return result

    async def save_attribute_candidate(self, vin: str, attribute: str, route: str) -> None:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        get_read_variant(attribute, route, profile.attribute_custom)
        profile.attribute_drafts[attribute] = route
        await self.storage.async_save(self.profiles)

    def _notify_discovery_change(self) -> None:
        coordinator = getattr(getattr(self.entry, "runtime_data", None), "coordinator", None)
        if coordinator is not None and hasattr(coordinator, "async_set_updated_data"):
            coordinator.async_set_updated_data(list(self.vehicles.values()))
        if coordinator is not None and hasattr(self.hass, "async_create_task"):
            from .registry_lifecycle import async_apply_v3_entity_visibility
            self.hass.async_create_task(
                async_apply_v3_entity_visibility(self.hass, self.entry, True),
                eager_start=False,
            )

    async def activate_attribute_route(self, vin: str, attribute: str, route: str) -> None:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        choice = get_read_variant(attribute, route, profile.attribute_custom)
        if choice["family"] != ("mbb" if car.context.auth == "legacy" else "cariad"):
            raise ValueError("Route does not match the vehicle API family")
        result = profile.attribute_route_evidence.get(attribute, {}).get(route, {})
        if result.get("outcome") != "verified" and not (
            choice["family"] == "mbb" and result.get("outcome") == "readable_but_stale"
        ):
            if choice["family"] == "mbb":
                raise ValueError("Test an MBB GET response before enabling legacy polling")
            raise ValueError("Test the route and verify fresh vehicle data before activation")
        profile.attribute_routes[attribute] = route
        profile.attribute_drafts[attribute] = route
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()

    async def disable_attribute_route(self, vin: str, attribute: str) -> None:
        car = self.require_vehicle(vin)
        if attribute not in ATTRIBUTES:
            raise ValueError("Unknown historical attribute")
        profile = self.profiles[car.vin.lower()]
        profile.attribute_routes.pop(attribute, None)
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()

    def diagnostics(self) -> dict[str, Any]:
        """No VIN, tokens, literal user routes, response bodies or coordinates."""
        vehicles = []
        for index, car in enumerate(self.vehicles.values(), 1):
            p = self.profiles.get(car.vin.lower())
            vehicles.append({
                "vehicle_slot": index,
                "context": {
                    "auth": car.context.auth,
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
                    # Operation IDs are stable for built-ins; user-authored
                    # names and literal custom URL templates are private and
                    # replaced with generic identifiers for diagnostics.
                    "read_route_evidence": [
                        {
                            "operation": ident if ident in self.registry.operations
                            else "custom_status_variant",
                            "outcome": evidence.get("outcome", "untested"),
                            "http_class": (
                                f"{evidence['http_status'] // 100}xx"
                                if type(evidence.get("http_status")) is int
                                else "unknown"
                            ),
                            "schema_valid": evidence.get("schema_valid", False),
                            "timestamp_present": evidence.get("fresh", False),
                        }
                        for ident, evidence in (
                            p.read_results.items() if p else ()
                        )
                    ][:15],
                    "control_route_evidence": [
                        {
                            "operation": ident if ident in self.registry.operations
                            else "custom_control_variant",
                            "outcome": outcome,
                        }
                        for ident, outcome in (
                            p.control_results.items() if p else ()
                        )
                    ][:15],
                    "disabled_controls": sorted(p.discovery.disabled) if p else [],
                    "automatic_read_discovery": discovery_summary(p) if p else {},
                    "last_api_results": [
                        {"operation": ident if ident in self.registry.operations
                         else "custom_or_discovery_route", **entry}
                        for ident, entry in reversed(list(p.api_observations.items()))
                    ][:24] if p else [],
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
