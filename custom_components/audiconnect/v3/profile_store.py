"""V3 local development profile persistence; no V2 runtime dependencies.

Stored profiles are scoped to the existing HA config entry and a private vehicle
key. Never export this raw store as public diagnostic or community telemetry.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .action_discovery import ActionAttempt
from .development_profiles import DevelopmentProfile, DevelopmentProfileError
from .registry import CapabilityRegistry, VehicleContext
from .historical_catalog import ATTRIBUTES
from .attribute_routes import validate_custom_read_route, get_read_variant


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
    profile = DevelopmentProfile(catalog, context, cooldown_seconds=cooldown_seconds)
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
    for operation, result in read.items():
        if not isinstance(result, dict) or set(result) != {
            "http_status", "schema_valid", "fresh", "outcome"
        } or type(result["http_status"]) is not int:
            raise DevelopmentProfileError("Malformed GET evidence")
        verified = profile.record_status(
            "climate", operation, http_status=result["http_status"],
            schema_valid=result["schema_valid"], fresh=result["fresh"]
        )
        if verified != result["outcome"]:
            raise DevelopmentProfileError("Stored GET evidence is inconsistent")
    for operation, result in control.items():
        if (
            result not in ("worked", "failed")
            or operation not in profile.registry.operations
            or profile.registry.operations[operation]["method"] != "POST"
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
            or detail["path"] not in ATTRIBUTES[ident]["paths"]
            or detail["job"] != ATTRIBUTES[ident]["job"]
            or detail["source"] != "cariad.selectivestatus"
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
    disabled = discovery.get("disabled_controls", [])
    if not isinstance(disabled, list) or any(
        item not in ("climate.start", "climate.stop") for item in disabled
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
            or attempt.capability != "climate"
            or attempt.action not in ("start", "stop")
            or attempt.operation not in profile.registry.operations
            or profile.registry.operations[attempt.operation]["method"] != "POST"
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
        if key not in ("climate.status", "climate.start", "climate.stop"):
            raise DevelopmentProfileError("Unknown draft capability")
        profile.save_candidate("climate", key.split(".")[1], operation)
    for key, operation in active.items():
        if key not in ("climate.status", "climate.start", "climate.stop"):
            raise DevelopmentProfileError("Unexpected active capability")
        profile.choose_working("climate", key.split(".")[1], operation)
        if key != "climate.status":
            profile.discovery.preferred[key] = operation
    return profile


class V3ProfileStorage:
    """Private HA .storage adapter, not wired to V2 or a dashboard."""

    def __init__(self, hass: Any, entry_id: str) -> None:
        from homeassistant.helpers.storage import Store
        if not isinstance(entry_id, str) or not entry_id:
            raise DevelopmentProfileError("Missing HA entry identifier")
        self._store = Store(hass, 1, f"audiconnect_v3_{entry_id}_profiles")

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
