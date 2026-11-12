"""Pure fast control-route resolution; discovery never sends vehicle actions.

Catalog matches are not local physical proof. A cached binding is diagnostic
evidence only; the current context and policy are evaluated on every use.
"""
from __future__ import annotations

from .action_discovery import approval_group
from .command_policy import eligible_operation
from .operation_revision import operation_revision
from .command_parameters import runtime_ready


def control_decision(car, profile, auth, capability: str, aspect: str) -> dict:
    key = f"{capability}.{aspect}"

    def decision(status, operation=None):
        return {
            "status": status,
            "operation": operation,
            "revision": operation_revision(profile.registry.operations[operation]) if operation else None,
        }

    if key in profile.discovery.disabled:
        return decision("user_disabled")
    if profile.discovery._active is not None or (
        profile.last_command is not None and profile.last_command.unresolved
    ):
        return decision("pending_review")
    restricted = capability == "remote" and aspect in ("engine_start", "engine_stop")
    allowed = eligible_operation(car, auth, capability, aspect) if restricted else None
    if restricted and not allowed:
        return decision("ineligible")
    try:
        available = profile.registry.resolve(capability, aspect, car.context)["available_operations"]
    except ValueError:
        return decision("unknown")

    def currently_safe(ident):
        if ident not in available:
            return False
        op = profile.registry.operations[ident]
        group = approval_group(capability, aspect, op)
        if group not in ("non_spin", "spin"):
            return False
        if group == "spin" and not getattr(getattr(auth, "service", None), "_spin", None):
            return False
        impaired = car.impaired_capabilities
        relevant = {
            "access": {"access", "remoteLockUnlock"},
            "charging": {"charging"},
            "climate": {"climatisation"},
        }.get(capability, set())
        if capability == "climate" and aspect.startswith("preheater_"):
            relevant = {"auxiliaryHeating", "hybridCarAuxiliaryHeating"}
        if relevant and relevant & impaired:
            return False
        return True

    ident = profile.active.get(key)
    if (ident and profile.control_results.get(ident) == "worked"
            and runtime_ready(profile.custom.get(ident, {}))
            and (not profile.custom.get(ident, {}).get("parameter_bindings")
                 or eligible_operation(car, auth, capability, aspect) is not None)
            and (not profile.custom.get(ident, {}).get("handler")
                 or eligible_operation(car, auth, capability, aspect) == profile.custom[ident]["handler"])
            and (not restricted or ident == allowed) and currently_safe(ident)):
        revision = profile.active_revisions.get(key)
        if revision == operation_revision(profile.registry.operations[ident]):
            return decision("local_verified", ident)
    if len(profile.registry.capabilities) <= 1:
        return decision("unknown")
    ident = eligible_operation(car, auth, capability, aspect)
    if ident and currently_safe(ident) and profile.control_results.get(ident) != "failed":
        return decision("catalog_matched", ident)
    return decision("unknown")


def resolve_control(car, profile, auth, capability: str, aspect: str) -> str | None:
    return control_decision(car, profile, auth, capability, aspect)["operation"]
