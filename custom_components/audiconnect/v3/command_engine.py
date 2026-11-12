"""V3 command owner: eligibility, dispatch, manual evidence and normal execution.

No HA entities, V2 business logic or status polling. Dependencies are explicit
and shared with the composition root; a command cannot create a second runtime.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .action_discovery import approval_group
from .command_journal import CommandRecord
from .command_readback import configure_readback, reconcile_readback
from .control_resolution import control_decision, resolve_control
from .response_preview import safe_response_preview
from .vehicle import V3Vehicle


class CommandEngine:
    def __init__(self, *, auth, transport, storage, profiles, require_vehicle,
                 operation_request, api_record, notify):
        self.auth = auth
        self._transport = transport
        self.storage = storage
        self.profiles = profiles
        self.require_vehicle = require_vehicle
        self._operation_request = operation_request
        self._api_record = api_record
        self._notify_discovery_change = notify
        self._actions = asyncio.Lock()
        self._wake_attempts: dict[str, list[float]] = {}

    @property
    def transport(self):
        return self._transport()

    async def _command_request(self, car: V3Vehicle, ident: str,
                               params: dict[str, Any] | None = None):
        family, method, path, body = self._operation_request(car, ident, params)
        op = self.profiles[car.vin.lower()].registry.operations[ident]
        mode = op.get("request_mode")
        if mode in ("mbb_climate_start", "mbb_climate_stop"):
            from .legacy_commands import climate_body
            body = climate_body(mode, params or {})
        elif mode in {"charging_settings_update", "charge_mode",
                    "charging_profile_update", "climate_settings_update",
                    "climate_start_settings", "flash", "auxiliary_start",
                    "engine_start"}:
            from .command_payloads import build
            body = await build(self, car, mode, params or {})
        return family, method, path, body

    async def _dispatch_command(self, car, family, method, path, body):
        if family == "mbb" and hasattr(self.transport, "executors"):
            from .legacy_commands import configure_home_region
            await configure_home_region(self.transport,self.auth,car)
        if family == "mbb" and path.endswith(("/lock", "/unlock")):
            from .legacy_commands import security_token
            token = await security_token(self.transport, car.vin, path.rsplit("/", 1)[-1],
                                         getattr(self.auth.service, "_spin", None))
            return await self.transport.request(family, method, path, body=body,
                                                explicit_action=True, security_token=token)
        return await self.transport.request(family, method, path, body=body, explicit_action=True)

    def control_routes_for(self, vin: str, capability: str, action: str) -> dict[str, Any]:
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        applicable = profile.registry.resolve(capability, action, vehicle.context)["available_operations"]
        routes = [
            {
                "id": op, "family": profile.registry.operations[op]["family"],
                "method": profile.registry.operations[op]["method"],
                "path": profile.registry.operations[op]["path"],
                "approval_group": approval_group(capability, action, profile.registry.operations[op]),
                "parameters_required": bool(profile.registry.operations[op].get("request_variables")) or profile.registry.operations[op].get("request_mode") in (
                    "charge_mode", "charging_settings_update", "charging_profile_update",
                    "climate_settings_update", "climate_start_settings"
                ),
                "status": profile.control_results.get(op, "not_tested"),
                "active": profile.active.get(f"{capability}.{action}") == op,
            }
            for op in applicable if profile.registry.operations[op]["method"] in ("POST", "PUT")
        ]
        in_progress = profile.discovery._active
        match = control_decision(vehicle, profile, self.auth, capability, action)
        return {
            "capability": capability, "action": action,
            "routes": routes, "active": match["operation"],
            "binding": match,
            "pending": in_progress.public() if in_progress else None,
            "requires": "Explicit per-action consent and physical verification",
            "spin_configured": bool(getattr(getattr(self.auth, "service", None), "_spin", None)),
        }

    async def disable_control(self, vin: str, capability: str, action: str) -> None:
        vehicle = self.require_vehicle(vin)
        profile = self.profiles[vehicle.vin.lower()]
        profile.disable(capability, action)
        await self.storage.async_save(self.profiles)
        self._notify_discovery_change()

    def reconcile_commands(self) -> None:
        """Correlate fresh scheduled observations without another request."""
        for vin, profile in self.profiles.items():
            if profile.last_command is None:
                continue
            try:
                car = self.require_vehicle(vin)
            except ValueError:
                continue
            if reconcile_readback(profile.last_command, car):
                car.last_command_result = "verified"

    def refresh_bindings(self) -> None:
        """Pure local matching; no request per control and no physical tests."""
        for key, profile in self.profiles.items():
            try:
                car = self.require_vehicle(key)
            except ValueError:
                continue
            profile.fast_bindings = {
                f"{capability}.{action}": control_decision(car, profile, self.auth, capability, action)
                for capability, definition in profile.registry.capabilities.items()
                for action in (definition.get("control") or {})
            }

    def _command_route(self, vin: str, aspect: str, capability: str) -> str | None:
        try:
            car = self.require_vehicle(vin)
        except ValueError:
            return None
        return resolve_control(car, self.profiles[vin.lower()], self.auth, capability, aspect)

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
        family = profile.registry.operations.get(operation, {}).get("family")
        if family not in ("cariad","mbb") or (family=="mbb" and self.auth.uses_auth0):
            raise ValueError("Control is not applicable to this authentication family")
        if operation not in profile.registry.resolve(
            capability, aspect, vehicle.context
        )["available_operations"]:
            raise ValueError("Control not applicable to this car")
        if capability == "remote" and aspect in ("engine_start", "engine_stop"):
            from .command_policy import eligible_operation
            if eligible_operation(vehicle, self.auth, capability, aspect) != operation:
                raise ValueError("Remote engine operation is not permitted for this vehicle")
        if profile.registry.operations[operation]["method"] not in ("POST", "PUT"):
            raise ValueError("Read-only operation cannot be a control")
        async with self._actions:
            if profile.discovery._active is not None:
                raise ValueError("Review the previous action before trying another")
            if profile.last_command is not None:
                profile.last_command.check_next(time.time())
            if f"{capability}.{aspect}" in profile.discovery.disabled:
                raise ValueError("This action has been disabled by the user")
            if (profile.discovery.history and
                    time.time() < profile.discovery.history[-1].started_at
                    + profile.discovery.cooldown_seconds):
                raise ValueError("Vehicle command cooldown still active")
            # Reject invalid templates/parameters BEFORE reserving a pending
            # physical action, otherwise a mere validation error locks the car.
            proof_required = profile.registry.operations[operation].get("request_mode") == "engine_start"
            if proof_required:
                if params:
                    raise ValueError("Unexpected engine start parameters")
                family, method, path, body = self._operation_request(vehicle, operation, params)
            else:
                family, method, path, body = await self._command_request(vehicle, operation, params)
            self._reserve_wake(vehicle.vin, operation)
            attempt = profile.begin_test(
                capability, aspect, operation, now=time.time()
            )
            await self.storage.async_save(self.profiles)
            try:
                if proof_required:
                    family, method, path, body = await self._command_request(vehicle, operation, params)
                response = await self._dispatch_command(vehicle, family, method, path, body)
                profile.observe_http(attempt.sequence, response.status)
                self._api_record(profile, operation, family, method, response, vehicle.vin)
            except (TimeoutError, OSError, RuntimeError, ValueError):
                profile.observe_http(attempt.sequence, None)
                response = None
                self._api_record(profile, operation, family, method, None, vehicle.vin)
            await self.storage.async_save(self.profiles)
            return {
                "sequence": attempt.sequence, "operation": operation,
                "transport": attempt.transport,
                "status": response.status if response else None,
                "response_preview": None if (capability == "access" or aspect in (
                    "engine_start", "engine_stop", "preheater_start"
                )) else safe_response_preview(
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

    async def send_control(
        self, vin: str, aspect: str, capability: str = "climate",
        *, params: dict[str, Any] | None = None,
    ) -> None:
        """One normal mutation, persisted before dispatch; never replay."""
        car = self.require_vehicle(vin)
        p = self.profiles[vin.lower()]
        async with self._actions:
            if p.discovery._active is not None:
                raise RuntimeError("A vehicle control experiment is awaiting physical confirmation")
            if p.last_command is not None:
                p.last_command.check_next(time.time())
            if p.discovery.history and time.time() < (
                p.discovery.history[-1].started_at + p.discovery.cooldown_seconds
            ):
                raise RuntimeError("Vehicle command cooldown active after engineering test")
            ident = self._command_route(vin, aspect, capability)
            if ident is None:
                raise RuntimeError("No eligible Audi command route")
            proof_required = p.registry.operations[ident].get("request_mode") == "engine_start"
            if proof_required:
                if params:
                    raise ValueError("Unexpected engine start parameters")
                family, method, path, body = self._operation_request(car, ident, params)
            else:
                family, method, path, body = await self._command_request(car, ident, params)
            self._reserve_wake(vin, ident)
            record = CommandRecord.begin(capability, aspect, ident, time.time())
            configure_readback(record, params)
            p.last_command = record
            # If storage fails here, no physical action is attempted.
            await self.storage.async_save(self.profiles)
            try:
                if proof_required:
                    family, method, path, body = await self._command_request(car, ident, params)
                response = await self._dispatch_command(car, family, method, path, body)
                self._api_record(p, ident, family, method, response, car.vin)
                if not 200 <= response.status < 300:
                    # A server error can occur after execution; do not assume failure.
                    record.state = "uncertain" if response.status >= 500 else "rejected"
                    car.last_command_result = f"request_failed_{response.status}"
                else:
                    record.state = "accepted_unconfirmed"
                    car.last_command_result = record.state
                    if family == "cariad":
                        from .request_status import confirm, request_id_of
                        request_id = request_id_of(response.data)
                        record.request_id = request_id
                        # Persist backend acceptance/ID before a cancellable follow-up.
                        await self.storage.async_save(self.profiles)
                        if request_id is not None:
                            car.last_command_result = await confirm(self.transport, car.vin, request_id)
                    elif family == "mbb":
                        from .legacy_commands import confirm
                        car.last_command_result = await confirm(self.transport, path, response.data)
                    if car.last_command_result in ("backend_completed", "rejected"):
                        record.state = car.last_command_result
            except asyncio.CancelledError:
                # The pre-dispatch journal is already durable; restart restores uncertainty.
                record.state = "uncertain"
                car.last_command_result = "transport_uncertain"
                raise
            except (TimeoutError, OSError, RuntimeError, ValueError) as err:
                record.state = "uncertain"
                car.last_command_result = "transport_uncertain"
                self._api_record(p, ident, family, method, None, car.vin)
                await self.storage.async_save(self.profiles)
                raise RuntimeError("Audi command outcome uncertain; check the car") from err
            await self.storage.async_save(self.profiles)
            self._notify_discovery_change()
            if record.state in ("rejected", "uncertain"):
                raise RuntimeError("Audi command rejected or uncertain; no automatic retry")

    async def review_normal_command(self, vin: str, command_id: str) -> None:
        """Explicit acknowledgement after inspecting the car; never dispatch."""
        car = self.require_vehicle(vin)
        p = self.profiles[car.vin.lower()]
        async with self._actions:
            record = p.last_command
            if record is None or record.command_id != command_id or not record.unresolved:
                raise ValueError("No matching unresolved normal command")
            record.state = "reviewed"
            await self.storage.async_save(self.profiles)
            self._notify_discovery_change()

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

