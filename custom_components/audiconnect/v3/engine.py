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
from .registry import CapabilityRegistry
from .transport import V3Response, V3Transport
from .vehicle import V3Vehicle
from .freshness import timestamp_is_fresh
from .attribute_runtime import planned_jobs, observe_read_only
from .attribute_routes import get_read_variant, read_variants, validate_custom_read_route
from .historical_catalog import ATTRIBUTES, capture_time, read_path
from .legacy_read_mappings import FIELDS as MBB_FIELDS
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
            TYPE="Audi", JOBS=",".join(planned_jobs(vehicle, profile)),
        )
        body = op.get("request_body")
        if op["method"] == "POST" and op.get("request_mode") == "secure_spin":
            if op["family"] != "cariad" or ident not in ("cariad.access.lock", "cariad.access.unlock"):
                raise ValueError("Unreviewed credential-bearing control")
            spin = getattr(getattr(self.auth, "service", None), "_spin", None)
            if not isinstance(spin, str) or not spin:
                raise ValueError("Audi S-PIN must be configured for remote door controls")
            body = {"spin": spin}  # Never persist or display S-PIN.
        return op["family"], op["method"], path, body

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
                    self._record_attribute_response(car, profile, ident, route, mappings, response)
                if 200 <= response.status < 300:
                    cloud_reachable = True
        if cloud_reachable:
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

    def control_enabled(self, vin: str, aspect: str, capability: str = "climate") -> bool:
        self.require_vehicle(vin)
        p = self.profiles[vin.lower()]
        return (
            f"{capability}.{aspect}" not in p.discovery.disabled
            and p.active.get(f"{capability}.{aspect}") is not None
            and p.control_results.get(p.active[f"{capability}.{aspect}"]) == "worked"
            and not p.custom.get(p.active[f"{capability}.{aspect}"], {}).get("variables")
        )

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
        if profile.registry.operations[operation]["method"] != "POST":
            raise ValueError("Read-only operation cannot be a control")
        async with self._actions:
            # Reject invalid templates/parameters BEFORE reserving a pending
            # physical action, otherwise a mere validation error locks the car.
            family, method, path, body = self._operation_request(
                vehicle, operation, params
            )
            attempt = profile.begin_test(
                capability, aspect, operation, now=time.time()
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
                "response_preview": safe_response_preview(
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

    async def send_control(self, vin: str, aspect: str, capability: str = "climate") -> None:
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
            ident = p.active[f"{capability}.{aspect}"]
            family, method, path, body = self._operation_request(car, ident)
            self._normal_action_at[vin.lower()] = now
            try:
                response = await self.transport.request(
                    family, method, path, body=body, explicit_action=True
                )
            except (TimeoutError, OSError, RuntimeError) as err:
                car.last_command_result = "transport_uncertain"
                raise RuntimeError(
                    "Audi command outcome uncertain; check the car"
                ) from err
            car.last_command_result = (
                "accepted_unconfirmed" if 200 <= response.status < 300
                else f"request_failed_{response.status}"
            )
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    "Audi rejected the selected vehicle command"
                )


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
        family = get_read_variant(attribute, operation, profile.attribute_custom)["family"]
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
            if not last or fresh or not last.get("fresh"):
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
