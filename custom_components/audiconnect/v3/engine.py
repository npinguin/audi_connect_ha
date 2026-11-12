"""V3 composition root, public runtime facade and profile orchestration.

No V2 account, vehicle model, legacy service calls, or V2 coordinator imports.
The auth facade is the only bridge to existing Audi credential code.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
import time
from typing import Any

from .auth import V3Auth
from .action_discovery import approval_group, validate_approval
from .command_engine import CommandEngine
from .command_parameters import runtime_ready
from .status_engine import StatusEngine
from .development_profiles import DevelopmentProfile, DevelopmentProfileError
from .profile_store import V3ProfileStorage
from .response_preview import safe_response_preview
from .api_observations import record_for, save_record
from .registry import CapabilityRegistry
from .product_contract import entity_projection_report
from .transport import V3Response, V3Transport
from .vehicle import V3Vehicle
from .freshness import timestamp_is_fresh
from .attribute_runtime import planned_jobs, observe_read_only, _accept_observation
from .custom_attributes import MAX_CUSTOM_ATTRIBUTES, attributes_for, descriptor, validate_definition
from .attribute_routes import get_read_variant, read_variants, validate_custom_read_route
from .historical_catalog import ATTRIBUTES, capture_time, read_path
from .legacy_read_mappings import FIELDS as MBB_FIELDS
from .legacy_read_mappings import ROUTES as MBB_ROUTES
from .api_value_mappings import normalize_api_value
from .historical_catalog import V2_JOBS
from .read_discovery import record_jobs, pending_groups, reserve_group, summary as discovery_summary
from ..const import (CONF_FILTER_VINS, CONF_REFRESH_AFTER_ACTION, CONF_UPDATE_SLEEP,
                     DOMAIN, REFRESH_VEHICLE_DATA_COMPLETED_EVENT,
                     REFRESH_VEHICLE_DATA_FAILED_EVENT, UPDATE_SLEEP)

_LOGGER = logging.getLogger(__name__)


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
        self._known_vehicle_inventory = False
        self.cloud_refresh_vin: str | None = None
        self.projected_entities: dict[str, set[str]] = {}
        self.commands = CommandEngine(
            auth=self.auth, transport=lambda: self.transport, storage=self.storage,
            profiles=self.profiles, require_vehicle=self.require_vehicle,
            operation_request=self._operation_request, api_record=self._api_record,
            notify=self._notify_discovery_change,
        )
        self.status = StatusEngine(
            hass=hass, entry=entry, auth=self.auth, transport=lambda: self.transport,
            storage=self.storage, vehicles=self.vehicles, profiles=self.profiles,
            discover=self.discover, known_inventory=lambda: self._known_vehicle_inventory,
            operation_request=self._operation_request, api_record=self._api_record,
        )

    @property
    def last_cloud_poll_success(self):
        return self.status.last_cloud_poll_success

    @property
    def last_cloud_poll_attempt(self):
        return self.status.last_cloud_poll_attempt

    @property
    def last_cloud_poll_succeeded(self):
        return self.status.last_cloud_poll_succeeded

    async def discover(self) -> None:
        """Own vehicle discovery. No V2 vehicle updates or extra poll task."""
        found = await self.transport.discover_vehicles()
        options = getattr(self.entry, "options", {})
        data = getattr(self.entry, "data", {})
        excluded = {x.strip().lower() for x in str(options.get(
            CONF_FILTER_VINS, data.get(CONF_FILTER_VINS, "")
        )).split(",") if x.strip()}
        known: dict[str, V3Vehicle] = {}
        complete = bool(found)
        for item in found:
            try:
                parsed = V3Vehicle.from_graphql(item, self.auth.country)
            except (ValueError, TypeError, AttributeError):
                complete = False
                continue
            if parsed.vin.lower() in excluded:
                continue
            vehicle = self.vehicles.get(parsed.vin.lower(), parsed)
            old_context = vehicle.context
            if parsed.model:
                vehicle.model = parsed.model
                vehicle.model_family = parsed.model_family
            if parsed.car_type:
                vehicle.car_type = parsed.car_type
            if parsed.model_year:
                vehicle.model_year = parsed.model_year
            vehicle.country = parsed.country
            vehicle.inventory_present = True
            vehicle.inventory_misses = 0
            vehicle.name = parsed.name
            vehicle.auth_family = "auth0" if self.auth.uses_auth0 else "legacy"
            vehicle.legacy_cariad = not self.auth.uses_auth0 and bool(getattr(self.auth,"has_cariad_bearer",False))
            vehicle.legacy_api_level = getattr(self.auth,"legacy_api_level",0)
            profile = self.profiles.get(parsed.vin.lower())
            if profile is not None and vehicle.context != old_context:
                profile.rebind_context(vehicle.context)
                vehicle.advertised_capabilities.clear()
                vehicle.impaired_capabilities.clear()
                vehicle.readings.clear()
                vehicle.capability_readings.clear()
                vehicle.climate_state = vehicle.climate_captured = None
                vehicle.position = None
                vehicle.charging_profiles.clear()
                vehicle.active_charging_profile_id = None
                vehicle.charging_profiles_captured = None
                vehicle.trips.clear()
            known[parsed.vin.lower()] = vehicle
        # An empty or malformed inventory cannot revoke a vehicle. Require two
        # complete nonempty snapshots, or an explicit local VIN exclusion.
        for key, car in self.vehicles.items():
            if key in excluded:
                car.inventory_present = False
            elif key not in known and complete:
                car.inventory_misses += 1
                if car.inventory_misses >= 2:
                    car.inventory_present = False
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
        if op["family"] == "mbb" and vehicle.country == "US" and "/climater/actions" in path:
            path = f"/api/bs/climatisation/v1/vehicles/{vehicle.vin}/climater/actions"
        body = op.get("request_body")
        if op.get("request_mode") == "secure_spin" and body is None:
            body = {"spin": "{SPIN}"}  # Support older immutable catalogs.
        return op["family"], op["method"], path, self._resolve_secure_body(
            vehicle, ident, op["family"], op["method"], path, body
        )

    async def _command_request(self, car, ident, params=None):
        return await self.commands._command_request(car, ident, params)

    async def _dispatch_command(self, car, family, method, path, body):
        return await self.commands._dispatch_command(car, family, method, path, body)

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
        Legacy MBB: at most five reviewed GETs, only for legacy auth.
        The API cloud budget remains enforced by V3Transport.
        """
        vehicle = self.require_vehicle(vin)
        expected = "mbb" if vehicle.context.auth == "legacy" else "cariad"
        if family != expected and not (family=="cariad" and vehicle.legacy_cariad):
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
                from .legacy_values import observe_legacy
                kind = route_id.rsplit(".", 1)[-1]
                observe_legacy(vehicle, profile, kind, response)
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
        cars = await self.status.poll()
        self.commands.reconcile_commands()
        self.commands.refresh_bindings()
        await self.storage.async_save(self.profiles)
        return cars

    def require_vehicle(self, vin: str) -> V3Vehicle:
        vehicle = self.vehicles.get(vin.lower())
        if vehicle is None or not vehicle.inventory_present:
            raise ValueError("Vehicle is not present in the current account inventory")
        return vehicle

    def control_routes_for(self, vin: str, capability: str, action: str) -> dict[str, Any]:
        return self.commands.control_routes_for(vin, capability, action)

    async def disable_control(self, vin: str, capability: str, action: str) -> None:
        await self.commands.disable_control(vin, capability, action)

    def _command_route(self, vin: str, aspect: str, capability: str) -> str | None:
        return self.commands._command_route(vin, aspect, capability)

    def control_enabled(self, vin: str, aspect: str, capability: str = "climate") -> bool:
        return self.commands.control_enabled(vin, aspect, capability)

    async def approved_control_discovery(
        self, vin: str, aspect: str, operation: str, *,
        approval: str, params: dict[str, Any] | None = None,
        capability: str = "climate",
    ) -> dict[str, Any]:
        """Public discovery boundary: one explicit approval, one vehicle action."""
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        op = profile.registry.operations.get(operation)
        if op is None:
            raise ValueError("Unknown discovery operation")
        if operation not in profile.registry.resolve(
            capability, aspect, vehicle.context
        )["available_operations"]:
            raise ValueError("Control not applicable to this car")
        validate_approval(capability, aspect, op, approval,
                          has_spin=bool(getattr(getattr(self.auth, "service", None), "_spin", None)))
        return await self.test_action(
            vin, aspect, operation, params=params, capability=capability
        )

    async def test_action(self, vin: str, aspect: str, operation: str, *,
                          params: dict[str, Any] | None = None, capability: str = "climate"):
        return await self.commands.test_action(vin, aspect, operation, params=params, capability=capability)

    async def review_action(self, vin: str, sequence: int, outcome: str):
        return await self.commands.review_action(vin, sequence, outcome)

    async def add_route(self, vin: str, route: dict[str, Any]) -> str:
        profile = self.profiles[self.require_vehicle(vin).vin.lower()]
        op = profile.add(route)
        await self.storage.async_save(self.profiles)
        return op


    async def test_status_route(
        self, vin: str, operation: str, *, params: dict[str, Any] | None = None,
        capability: str = "climate",
    ) -> dict[str, Any]:
        """On-demand read-only GET test, with explicit response classification."""
        car = self.require_vehicle(vin)
        p = self.profiles[car.vin.lower()]
        allowed = p.registry.resolve(
            capability, "status", car.context
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
        if capability == "climate":
            valid = 200 <= response.status < 300 and car.set_climate(
                field_value, timestamp, route=operation,
                observed_at=response.observed_at, http_status=response.status,
            )
            if valid:
                car.climate_field = field
        else:
            valid = 200 <= response.status < 300 and field_value is not None
        fresh = bool(valid and timestamp_is_fresh(timestamp, response.observed_at))
        verdict = p.record_status(
            capability, operation, http_status=response.status,
            schema_valid=valid, fresh=fresh,
        )
        if verdict == "worked" and not p.custom.get(operation, {}).get("variables"):
            p.choose_working(capability, "status", operation)
        await self.storage.async_save(self.profiles)
        return {
            "http_status": response.status,
            "field": field,
            "value": (car.climate_state if capability == "climate" else field_value) if valid else None,
            "captured": timestamp if valid else None,
            "result": verdict,
            "schema_keys": sorted(response.data.keys())[:20]
            if isinstance(response.data, dict) else [],
            "response_preview": safe_response_preview(
                response.data, vehicle_vin=car.vin
            ),
        }

    async def save_candidate(
        self, vin: str, aspect: str, operation: str, capability: str = "climate",
    ) -> None:
        """Save a planned test route without exposing unproven vehicle controls."""
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        profile.save_candidate(capability, aspect, operation)
        await self.storage.async_save(self.profiles)

    async def select_working(self, vin: str, aspect: str, operation: str, capability: str = "climate") -> None:
        """Admin selects another previously verified route; no request."""
        car = self.require_vehicle(vin)
        p = self.profiles[car.vin.lower()]
        if not runtime_ready(p.custom.get(operation, {})):
            raise DevelopmentProfileError("Dynamic parameters without semantic bindings remain test-only")
        p.choose_working(capability, aspect, operation)
        await self.storage.async_save(self.profiles)

    async def disable_action(self, vin: str, aspect: str, capability: str = "climate") -> None:
        p = self.profiles[self.require_vehicle(vin).vin.lower()]
        p.disable(capability, aspect)
        await self.storage.async_save(self.profiles)

    def _refresh_event(self, vin: str, record) -> None:
        """Retain historical event IDs, never report an unconfirmed refresh as complete."""
        bus = getattr(self.hass, "bus", None)
        if bus is None:
            return
        completed = record.state in ("backend_completed", "verified")
        event = REFRESH_VEHICLE_DATA_COMPLETED_EVENT if completed else REFRESH_VEHICLE_DATA_FAILED_EVENT
        bus.async_fire(f"{DOMAIN}_{event}", {
            "vin": "*" * max(0, len(vin) - 4) + vin[-4:],
            "outcome": record.state,
        })

    async def _follow_up_cloud(self) -> None:
        """One read-only coordinator refresh, never a second polling owner."""
        coordinator = getattr(getattr(self.entry, "runtime_data", None), "coordinator", None)
        if coordinator is None or not hasattr(coordinator, "async_request_refresh"):
            return
        try:
            delay = float(getattr(self.entry, "options", {}).get(CONF_UPDATE_SLEEP, UPDATE_SLEEP))
        except (TypeError, ValueError):
            delay = UPDATE_SLEEP
        try:
            await asyncio.sleep(max(0, min(delay, 300)))
            await coordinator.async_request_refresh()
        except Exception:
            # A follow-up read must not turn an already accepted command into a
            # failed service call (which could prompt an unsafe user retry).
            _LOGGER.warning("Audi command follow-up cloud read failed")

    async def _after_command(self, vin: str, record) -> None:
        if getattr(getattr(self.entry, "runtime_data", None), "coordinator", None) is None:
            return
        remote_refresh = record.capability == "remote" and record.action == "refresh"
        if remote_refresh:
            self._refresh_event(vin, record)
        elif (getattr(self.entry, "options", {}).get(CONF_REFRESH_AFTER_ACTION, False)
              and record.state in ("backend_completed", "verified")
              and not (record.capability == "remote" and record.action == "wake")):
            # The existing opt-in V2 option permits one explicit refresh after
            # an accepted action. Never send it after uncertainty, recurse, or
            # bypass the wake quota/security/evidence checks.
            try:
                refresh = await self.commands.send_control(vin, "refresh", "remote",
                                                           _follow_up_to=record.command_id)
            except (RuntimeError, ValueError):
                profile = self.profiles.get(vin.lower())
                refresh = getattr(profile, "last_command", None)
                if refresh is not None and refresh.parent_command_id == record.command_id:
                    self._refresh_event(vin, refresh)
                _LOGGER.debug("Audi optional vehicle refresh skipped or unconfirmed")
            else:
                self._refresh_event(vin, refresh)
        await self._follow_up_cloud()

    async def send_control(self, vin: str, aspect: str, capability: str = "climate", *,
                           params: dict[str, Any] | None = None) -> None:
        profile = self.profiles.get(vin.lower())
        previous = getattr(profile, "last_command", None)
        try:
            record = await self.commands.send_control(vin, aspect, capability, params=params)
        except (RuntimeError, ValueError):
            current = getattr(profile, "last_command", None)
            if capability == "remote" and aspect == "refresh" and current is not None and current is not previous:
                self._refresh_event(vin, current)
                await self._follow_up_cloud()
            raise
        await self._after_command(vin, record)

    async def review_normal_command(self, vin: str, command_id: str) -> None:
        await self.commands.review_normal_command(vin, command_id)

    async def send_setting(self, vin: str, kind: str, value: Any) -> None:
        record = await self.commands.send_setting(vin, kind, value)
        await self._after_command(vin, record)

    def attribute_routes_for(self, vin: str, attribute: str) -> dict[str, Any]:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        alternatives = [r for r in read_variants(attribute, profile.attribute_custom, attributes_for(profile))
                        if r["family"] == ("mbb" if car.context.auth == "legacy" else "cariad")
                        or (r["family"] == "cariad" and car.legacy_cariad)]
        for variant in alternatives:
            evidence = profile.attribute_route_evidence.get(attribute, {}).get(variant["id"], {})
            variant["result"] = evidence.get("outcome", "not_tested")
            variant["active"] = profile.attribute_routes.get(attribute) == variant["id"]
        return {
            "attribute": attribute, "capability": attributes_for(profile)[attribute]["capability"],
            "routes": alternatives, "active": profile.attribute_routes.get(attribute),
            "draft": profile.attribute_drafts.get(attribute),
        }

    async def add_attribute_route(self, vin: str, definition: dict[str, Any]) -> str:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        raw = dict(definition)
        local = raw.pop("attribute_definition", None)
        attributes = attributes_for(profile)
        if local is not None:
            local = validate_definition(local)
            ident = local["id"]
            if ident != raw.get("attribute") or ident in attributes:
                raise ValueError("New local attribute must have a unique matching ID")
            if len(profile.attribute_definitions) >= MAX_CUSTOM_ATTRIBUTES:
                raise ValueError("Too many local attributes")
            attributes[ident] = descriptor(local)
        route = validate_custom_read_route(raw, attributes)
        if route["id"] in profile.attribute_custom:
            raise ValueError("Choose a new custom route identifier")
        if len(profile.attribute_custom) >= 50:
            raise ValueError("Too many custom routes")
        if local is not None:
            profile.attribute_definitions[local["id"]] = local
        profile.attribute_custom[route["id"]] = route
        await self.storage.async_save(self.profiles)
        return route["id"]

    def _attribute_request(self, car, profile, attribute, route):
        return self.status._attribute_request(car, profile, attribute, route)

    def _record_attribute_response(self, car, profile, attribute, route, mappings, response):
        return self.status._record_attribute_response(car, profile, attribute, route, mappings, response)

    async def test_attribute_route(self, vin: str, attribute: str, route: str) -> dict[str, Any]:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        family, path, mappings = self._attribute_request(car, profile, attribute, route)
        if family != ("mbb" if car.context.auth == "legacy" else "cariad") and not (
            family == "cariad" and car.legacy_cariad
        ):
            raise ValueError("Read route is not applicable to this vehicle API family")
        response = await self.transport.request(family, "GET", path)
        self._api_record(profile, route, family, "GET", response, car.vin)
        result = self._record_attribute_response(car, profile, attribute, route, mappings, response)
        await self.storage.async_save(self.profiles)
        return result

    async def save_attribute_candidate(self, vin: str, attribute: str, route: str) -> None:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        get_read_variant(attribute, route, profile.attribute_custom, attributes_for(profile))
        profile.attribute_drafts[attribute] = route
        await self.storage.async_save(self.profiles)

    def _notify_discovery_change(self) -> None:
        coordinator = getattr(getattr(self.entry, "runtime_data", None), "coordinator", None)
        if coordinator is not None and hasattr(coordinator, "async_update_listeners"):
            # Local evidence changes are not a successful cloud update.
            coordinator.async_update_listeners()
        if coordinator is not None and hasattr(self.hass, "async_create_task"):
            from .registry_lifecycle import async_apply_v3_entity_visibility
            self.hass.async_create_task(
                async_apply_v3_entity_visibility(self.hass, self.entry, True),
                eager_start=False,
            )

    async def activate_attribute_route(self, vin: str, attribute: str, route: str) -> None:
        car = self.require_vehicle(vin)
        profile = self.profiles[car.vin.lower()]
        choice = get_read_variant(attribute, route, profile.attribute_custom, attributes_for(profile))
        if choice["family"] != ("mbb" if car.context.auth == "legacy" else "cariad") and not (
            choice["family"] == "cariad" and car.legacy_cariad
        ):
            raise ValueError("Route does not match the vehicle API family")
        result = profile.attribute_route_evidence.get(attribute, {}).get(route, {})
        if result.get("outcome") != "verified" and not (
            (choice["family"] == "mbb" or choice.get("allow_last_known")) and result.get("outcome") == "readable_but_stale"
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
        profile = self.profiles[car.vin.lower()]
        if attribute not in attributes_for(profile):
            raise ValueError("Unknown attribute")
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
                "trip_data_sources": len(car.trips),
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
                            "fresh": evidence.get("fresh", False),
                            "timestamp_present": evidence.get("timestamp_present"),
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
            "last_poll_succeeded": self.last_cloud_poll_succeeded,
            "last_poll_attempt": self.last_cloud_poll_attempt.isoformat() if self.last_cloud_poll_attempt else None,
            "quota_remaining": self.transport.remaining_calls,
            "vehicles": vehicles,
            "entity_projection": entity_projection_report(self),
        }
