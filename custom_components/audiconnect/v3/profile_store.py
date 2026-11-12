"""V3 local development profile persistence; no V2 runtime dependencies.

Stored profiles are scoped to the existing HA config entry and a private vehicle
key. Never export this raw store as public diagnostic or community telemetry.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from .action_discovery import ActionAttempt
from .command_journal import CommandRecord, restore_history
from .operation_revision import operation_revision
from .development_profiles import DevelopmentProfile, DevelopmentProfileError
from .registry import CapabilityRegistry, VehicleContext
from .historical_catalog import ATTRIBUTES, V2_JOBS
from .api_observations import validate_record, MAX_ROUTES
from .attribute_routes import validate_custom_read_route, get_read_variant, read_variants


def restore_profile(
    catalog: CapabilityRegistry,
    context: VehicleContext,
    saved: Mapping[str, Any],
    *,
    cooldown_seconds: float = 15,
) -> DevelopmentProfile:
    """Validate and restore user paths and proven selections, without requests."""
    if not isinstance(saved, Mapping) or saved.get("schema_version") != 1:
        raise DevelopmentProfileError("Invalid V3 profile version")
    saved_context = saved.get("vehicle_context")
    old_context = context
    if saved_context is not None:
        try:
            old_context = VehicleContext(**saved_context)
        except (ValueError, TypeError) as exc:
            raise DevelopmentProfileError("Invalid saved vehicle context") from exc
        if (old_context.auth not in ("auth0", "legacy") or type(old_context.legacy_cariad) is not bool
                or type(old_context.legacy_api_level) is not int
                or any(not isinstance(value, str) or len(value) > 100 for value in
                       (old_context.region, old_context.vehicle_type, old_context.model_family))):
            raise DevelopmentProfileError("Invalid saved vehicle context")
    profile = DevelopmentProfile(catalog, old_context, cooldown_seconds=cooldown_seconds)
    custom = saved.get("custom_routes", [])
    read = saved.get("read_evidence", {})
    control = saved.get("control_evidence", {})
    active = saved.get("active", {})
    discovery = saved.get("discovery", {})
    if (
        not isinstance(custom, list) or len(custom) > 50
        or not isinstance(read, dict) or len(read) > 100
        or not isinstance(control, dict) or len(control) > 100
        or not isinstance(active, dict) or not isinstance(discovery, dict)
    ):
        raise DevelopmentProfileError("Malformed local development profile")
    for operation in custom:
        profile.add(operation)
    try:
        if "command_journal" in saved:
            profile.command_journal, profile.last_command = restore_history(saved["command_journal"])
        if profile.last_command is None and saved.get("last_command") is not None:
            profile.track_command(CommandRecord.restore(saved["last_command"]))
    except ValueError as exc:
        raise DevelopmentProfileError("Invalid stored command journal") from exc
    invalidated = saved.get("invalidated_attempt_sequence")
    if invalidated is not None and (type(invalidated) is not int or invalidated < 1):
        raise DevelopmentProfileError("Invalid context-invalidated attempt")
    profile.invalidated_attempt_sequence = invalidated
    for operation, result in read.items():
        if not isinstance(result, dict) or set(result) != {
            "http_status", "schema_valid", "fresh", "outcome"
        } or type(result["http_status"]) is not int:
            raise DevelopmentProfileError("Malformed GET evidence")
        owners = [capability for capability, definition in profile.registry.capabilities.items()
                  if operation in (definition.get("status") or {}).get("operations", [])]
        if len(owners) != 1:
            raise DevelopmentProfileError("Ambiguous stored status operation")
        verified = profile.record_status(
            owners[0], operation, http_status=result["http_status"],
            schema_valid=result["schema_valid"], fresh=result["fresh"]
        )
        if verified != result["outcome"]:
            raise DevelopmentProfileError("Stored GET evidence is inconsistent")
    for operation, result in control.items():
        if (
            result not in ("worked", "failed")
            or operation not in profile.registry.operations
            or profile.registry.operations[operation]["method"] not in ("POST","PUT")
        ):
            raise DevelopmentProfileError("Malformed action evidence")
        profile.control_results[operation] = result
    # Historical attribute evidence is optional for profiles saved by b4.
    ar = saved.get("attribute_routes", {})
    ae = saved.get("attribute_evidence", {})
    ac = saved.get("attribute_custom", {})
    ad = saved.get("attribute_drafts", {})
    are = saved.get("attribute_route_evidence", {})
    if any(not isinstance(q, dict) for q in (ac, ad, are)) or len(ac) > 50 or len(ad) > len(ATTRIBUTES) or len(are) > len(ATTRIBUTES):
        raise DevelopmentProfileError("Invalid custom read route storage")
    for ident, value in ac.items():
        route = validate_custom_read_route(value)
        if ident != route["id"]:
            raise DevelopmentProfileError("Custom route ID mismatch")
        profile.attribute_custom[ident] = route
    for ident, variants in are.items():
        if ident not in ATTRIBUTES or not isinstance(variants, dict) or len(variants) > 25:
            raise DevelopmentProfileError("Invalid read route evidence")
        for route, data in variants.items():
            get_read_variant(ident, route, profile.attribute_custom)
            if not isinstance(data, dict) or set(data) != {"outcome", "path", "http_status"}:
                raise DevelopmentProfileError("Untrusted route evidence")
            if data["outcome"] not in ("verified", "readable_but_stale", "mapping_missing", "api_error") or data["path"] not in get_read_variant(ident, route, profile.attribute_custom)["response_paths"] or type(data["http_status"]) is not int:
                raise DevelopmentProfileError("Invalid route evidence values")
            profile.attribute_route_evidence.setdefault(ident, {})[route] = dict(data)
    for ident, route in ad.items():
        get_read_variant(ident, route, profile.attribute_custom)
        profile.attribute_drafts[ident] = route
    if not isinstance(ar, dict) or not isinstance(ae, dict) or len(ar) > len(ATTRIBUTES) or len(ae) > len(ATTRIBUTES):
        raise DevelopmentProfileError("Invalid attribute profile")
    for ident, detail in ae.items():
        if ident not in ATTRIBUTES or not isinstance(detail, dict) or set(detail) != {"status", "path", "job", "source", "timestamp_present"}:
            raise DevelopmentProfileError("Invalid attribute evidence")
        if (detail["status"] not in ("verified", "readable_but_stale")
            or detail["path"] not in {
                p for variant in read_variants(ident, profile.attribute_custom)
                for p in variant["response_paths"]
            }
            or detail["job"] != ATTRIBUTES[ident]["job"]
            or detail["source"] not in ("cariad.selectivestatus", "mbb.legacy")
            or (detail["source"] == "mbb.legacy"
                and detail["path"] not in {
                    p for variant in read_variants(ident, profile.attribute_custom)
                    if variant["family"] == "mbb" for p in variant["response_paths"]
                })
            or type(detail["timestamp_present"]) is not bool):
            raise DevelopmentProfileError("Untrusted attribute evidence")
        profile.attribute_evidence[ident] = dict(detail)
    for ident, route in ar.items():
        if ident not in ATTRIBUTES or ident not in ae:
            raise DevelopmentProfileError("Unverified active attribute")
        get_read_variant(ident, route, profile.attribute_custom)
        if route != "cariad.selectivestatus.batch" and profile.attribute_route_evidence.get(ident, {}).get(route, {}).get("outcome") not in ("verified", "readable_but_stale"):
            raise DevelopmentProfileError("Unverified active route selection")
        profile.attribute_routes[ident] = route
    # Added after b5: older saved per-vehicle profiles load without any upgrade.
    observed_jobs = saved.get("job_discovery", {})
    probed_jobs = saved.get("job_probe_attempts", {})
    if (not isinstance(observed_jobs, dict) or not isinstance(probed_jobs, dict)
            or len(observed_jobs) > len(V2_JOBS) or len(probed_jobs) > len(V2_JOBS)):
        raise DevelopmentProfileError("Invalid CARIAD discovery data")
    for job, result in observed_jobs.items():
        if job not in V2_JOBS or result not in ("observed", "not_observed", "inconclusive"):
            raise DevelopmentProfileError("Untrusted discovery job status")
    for job, count in probed_jobs.items():
        if job not in V2_JOBS or type(count) is not int or not 0 <= count <= 1:
            raise DevelopmentProfileError("Untrusted read-only probe count")
    profile.job_discovery.update(observed_jobs)
    profile.job_probe_attempts.update(probed_jobs)
    observations = saved.get("api_observations", {})
    if not isinstance(observations, dict) or len(observations) > MAX_ROUTES:
        raise DevelopmentProfileError("Invalid saved API observations")
    for ident, item in observations.items():
        if not isinstance(ident, str) or not 1 <= len(ident) <= 120:
            raise DevelopmentProfileError("Invalid API route ID")
        try:
            validate_record(item)
        except ValueError as exc:
            raise DevelopmentProfileError("Invalid saved API evidence") from exc
        profile.api_observations[ident] = dict(item)
    disabled = discovery.get("disabled_controls", [])
    if not isinstance(disabled, list) or any(
        item not in {f"{c}.{a}" for c, d in catalog.capabilities.items()
                     for a in (d.get("control") or {})} for item in disabled
    ):
        raise DevelopmentProfileError("Malformed disabled actions")
    profile.discovery.disabled = set(disabled)
    attempts = discovery.get("attempts", [])
    if not isinstance(attempts, list) or len(attempts) > 100:
        raise DevelopmentProfileError("Malformed action history")
    prev = 0
    for saved_attempt in attempts:
        if not isinstance(saved_attempt, dict):
            raise DevelopmentProfileError("Malformed action record")
        try:
            attempt = ActionAttempt(**saved_attempt)
        except (TypeError, ValueError) as err:
            raise DevelopmentProfileError("Malformed action fields") from err
        if (
            type(attempt.sequence) is not int or attempt.sequence <= prev
            or attempt.capability not in catalog.capabilities
            or attempt.action not in (catalog.capabilities.get(attempt.capability, {}).get("control") or {})
            or attempt.operation not in profile.registry.operations
            or profile.registry.operations[attempt.operation]["method"] not in ("POST", "PUT")
            or attempt.result not in (
                "worked", "failed", "uncertain_pending_review",
                "awaiting_user_feedback"
            )
            or type(attempt.started_at) not in (int, float)
            or attempt.started_at < 0
        ):
            raise DevelopmentProfileError("Untrusted action history")
        profile.discovery.history.append(attempt)
        prev = attempt.sequence
    profile.discovery._sequence = prev
    # Never replay a command interrupted by a Home Assistant restart.
    unresolved = [
        attempt for attempt in profile.discovery.history
        if attempt.result in ("uncertain_pending_review", "awaiting_user_feedback")
    ]
    if unresolved:
        pending = unresolved[-1]
        pending.result = "uncertain_pending_review"
        profile.discovery._active = pending
    drafts = saved.get("draft_selected", {})
    if not isinstance(drafts, dict):
        raise DevelopmentProfileError("Invalid draft route selections")
    for key, operation in drafts.items():
        if "." not in key:
            raise DevelopmentProfileError("Unknown draft capability")
        capability, action = key.split(".", 1)
        profile.save_candidate(capability, action, operation)
    revisions = saved.get("active_revisions", {})
    if not isinstance(revisions, dict):
        raise DevelopmentProfileError("Malformed route revisions")
    for key, operation in active.items():
        if "." not in key:
            raise DevelopmentProfileError("Unexpected active capability")
        capability, action = key.split(".", 1)
        # Validate the evidence even for old, unversioned data. Do not treat
        # the old record as proof for a changed or unknown operation revision.
        profile.choose_working(capability, action, operation)
        if action != "status":
            if revisions.get(key) != operation_revision(profile.registry.operations[operation]):
                profile.active.pop(key, None)
                profile.active_revisions.pop(key, None)
                profile.discovery.preferred.pop(key, None)
            else:
                profile.discovery.preferred[key] = operation
    # Catalog-match cache is not an authorization source; recomputed at poll.
    profile.fast_bindings = {}
    profile.rebind_context(context)
    return profile


class V3ProfileStorage:
    """Private HA .storage adapter, not wired to V2 or a dashboard."""

    def __init__(self, hass: Any, entry_id: str) -> None:
        from homeassistant.helpers.storage import Store
        if not isinstance(entry_id, str) or not entry_id:
            raise DevelopmentProfileError("Missing HA entry identifier")
        self._store = Store(hass, 1, f"audiconnect_v3_{entry_id}_profiles")
        self._write_lock = asyncio.Lock()

    async def async_load(
        self, catalog: CapabilityRegistry,
        vehicles: Mapping[str, VehicleContext],
    ) -> dict[str, DevelopmentProfile]:
        saved = await self._store.async_load() or {}
        if not isinstance(saved, dict) or not isinstance(
            saved.get("profiles", {}), dict
        ):
            raise DevelopmentProfileError("Invalid HA profile storage")
        records = saved.get("profiles", {})
        return {
            vehicle_key: (
                restore_profile(catalog, context, records[vehicle_key])
                if vehicle_key in records else DevelopmentProfile(catalog, context)
            )
            for vehicle_key, context in vehicles.items()
        }

    async def async_save(self, profiles: Mapping[str, DevelopmentProfile]) -> None:
        if not hasattr(self, "_write_lock"):
            self._write_lock = asyncio.Lock()
        async with self._write_lock:
            await self._save_locked(profiles)

    async def _save_locked(self, profiles: Mapping[str, DevelopmentProfile]) -> None:
        if len(profiles) > 50:
            raise DevelopmentProfileError("Too many vehicles")
        # A partial or failed vehicle inventory is NOT permission to delete
        # earlier tested configurations belonging to the same account.
        old = await self._store.async_load() or {}
        if not isinstance(old, dict) or not isinstance(old.get("profiles", {}), dict):
            raise DevelopmentProfileError("Invalid existing local profile store")
        records = dict(old.get("profiles", {}))
        records.update({
            key: value.snapshot() for key, value in profiles.items()
        })
        if len(records) > 50:
            raise DevelopmentProfileError("Too many saved vehicle profiles")
        await self._store.async_save({"profiles": records})
