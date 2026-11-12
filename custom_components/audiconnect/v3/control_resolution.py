"""Pure fast control-route resolution; discovery never sends vehicle actions."""
from __future__ import annotations

from .command_policy import eligible_operation


def resolve_control(car, profile, auth, capability: str, aspect: str) -> str | None:
    key = f"{capability}.{aspect}"
    if (key in profile.discovery.disabled or profile.discovery._active is not None
            or (profile.last_command is not None and profile.last_command.unresolved)):
        return None
    restricted = capability == "remote" and aspect in ("engine_start", "engine_stop")
    allowed = eligible_operation(car, auth, capability, aspect) if restricted else None
    if restricted and not allowed:
        return None
    try:
        available = profile.registry.resolve(capability, aspect, car.context)["available_operations"]
    except ValueError:
        return None
    ident = profile.active.get(key)
    if (ident and profile.control_results.get(ident) == "worked"
            and not profile.custom.get(ident, {}).get("variables")
            and (not restricted or ident == allowed) and ident in available):
        return ident
    # Historical reviewed routes may be matched automatically; this is not
    # local physical proof. Pilot-only fixtures do not enable product defaults.
    if len(profile.registry.capabilities) <= 1:
        return None
    ident = eligible_operation(car, auth, capability, aspect)
    if ident in available and profile.control_results.get(ident) != "failed":
        return ident
    return None
