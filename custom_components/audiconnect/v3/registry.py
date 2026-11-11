"""Pure V3 capability registry: no HA services, token handling or HTTP calls.

The registry owns definitions/selection; the runtime owns dispatch and evidence.
Model/region refinements are optional: generic operations always remain defined.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
from typing import Any, Mapping

_ALLOWED_FIELDS = frozenset({"VIN", "COUNTRY", "TYPE", "JOBS"})
_ALLOWED_SCOPE = frozenset({"auth", "region", "vehicle_type", "model_family"})
_ALLOWED_METHODS = frozenset({"GET", "POST"})


class RegistryError(ValueError):
    """Invalid V3 catalog or unsupported operation."""


@dataclass(frozen=True)
class VehicleContext:
    auth: str
    region: str = ""
    vehicle_type: str = ""
    model_family: str = ""


@dataclass
class RouteEvidence:
    """Evidence for a route, scoped per vehicle by the caller."""

    readable: int = 0
    cached_present: int = 0
    consecutive_not_found: int = 0
    suspended_until: float = 0
    last_result: str = "not_tested"

    def record(self, http_status: int, usable: bool, now: float) -> None:
        if http_status in (404, 410):
            self.consecutive_not_found += 1
            self.last_result = "not_found"
            if self.consecutive_not_found >= 3:
                self.suspended_until = now + 86400
        elif 200 <= http_status < 300 and usable:
            self.readable += 1
            self.consecutive_not_found = 0
            self.suspended_until = 0
            self.last_result = "readable"
        else:
            # Neither sleeping vehicles nor Audi cloud failures remove features.
            self.consecutive_not_found = 0
            self.last_result = (
                "not_authorized" if http_status in (401, 403)
                else "rate_limited" if http_status == 429
                else "upstream_error" if http_status >= 500
                else "inconclusive"
            )

    def suspended(self, now: float) -> bool:
        return now < self.suspended_until


def _check_path(path: Any) -> None:
    if not isinstance(path, str) or not path.startswith("/"):
        raise RegistryError("API paths must be relative to approved family hosts")
    if "://" in path or "//" in path or ".." in path or "\\" in path or "#" in path:
        raise RegistryError("Unsafe API path")
    for _, field_name, _, conversion in Formatter().parse(path):
        if field_name is not None and (field_name not in _ALLOWED_FIELDS or conversion):
            raise RegistryError("Unknown or unsafe path template variable")


class CapabilityRegistry:
    """One brand catalog, with optional operation-level context refinement."""

    def __init__(self, raw: Mapping[str, Any]) -> None:
        if raw.get("schema_version") != 1 or raw.get("brand") != "audi":
            raise RegistryError("Unsupported V3 schema or brand")
        self.families = raw.get("api_families")
        self.operations = raw.get("operations")
        self.capabilities = raw.get("capabilities")
        if not all(isinstance(x, dict) for x in (
            self.families, self.operations, self.capabilities
        )):
            raise RegistryError("V3 catalog sections must be objects")
        if set(self.capabilities) != {"climate"}:
            raise RegistryError("V3 pilot intentionally owns only climate")
        for ident, op in self.operations.items():
            if not isinstance(op, dict):
                raise RegistryError("Malformed operation")
            family = self.families.get(op.get("family"))
            if not isinstance(family, dict) or family.get("auth") not in ("auth0", "legacy"):
                raise RegistryError("Unknown API family or auth")
            if op.get("method") not in _ALLOWED_METHODS:
                raise RegistryError("Method not supported by V3 pilot")
            _check_path(op.get("path"))
            scope = op.get("scope", {})
            if not isinstance(scope, dict) or set(scope) - _ALLOWED_SCOPE:
                raise RegistryError("Invalid context refinement")
            if any(not isinstance(v, str) for v in scope.values()):
                raise RegistryError("Context scope values must be strings")
            if op.get("delivery") not in ("existing_poll", "manual"):
                raise RegistryError("Unknown operation owner")
            if op["method"] == "POST" and op["delivery"] != "manual":
                raise RegistryError("A control may never execute automatically")
            if op["method"] == "GET":
                if not isinstance(op.get("response_paths"), list):
                    raise RegistryError("GET requires response mapping paths")
                if any(not isinstance(p, str) for p in op["response_paths"]):
                    raise RegistryError("Invalid response path")
        for capability, definition in self.capabilities.items():
            if not isinstance(definition, dict) or set(definition) - {"status", "control"}:
                raise RegistryError("Capability must own optional status/control")
            if not definition:
                raise RegistryError("Capability must have a supported aspect")
            control = definition.get("control") or {}
            if not isinstance(control, dict) or set(control) - {"start", "stop"}:
                raise RegistryError("Invalid control definition")
            for aspect in ("status", "start", "stop"):
                node = definition.get("status") if aspect == "status" else control.get(aspect)
                if node is None:
                    continue
                refs = node.get("operations") if isinstance(node, dict) else None
                if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)):
                    raise RegistryError("Missing or duplicate operation reference")
                for ref in refs:
                    op = self.operations.get(ref)
                    if op is None or op["method"] != ("GET" if aspect == "status" else "POST"):
                        raise RegistryError("Invalid operation reference")
    
    @classmethod
    def from_json_file(cls, path: Path) -> "CapabilityRegistry":
        """File read must run in HA's executor, never on the event loop."""
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def operations_for(self, capability: str, aspect: str) -> list[str]:
        definition = self.capabilities.get(capability)
        if definition is None or aspect not in ("status", "start", "stop"):
            raise RegistryError("Unknown capability or aspect")
        node = definition.get("status") if aspect == "status" else (
            (definition.get("control") or {}).get(aspect)
        )
        return list(node.get("operations", [])) if node else []

    def resolve(
        self,
        capability: str,
        aspect: str,
        context: VehicleContext,
        evidence: Mapping[str, RouteEvidence] | None = None,
        *,
        preferred: str | None = None,
        now: float = 0,
    ) -> dict[str, Any]:
        """Resolve exactly one known route, without making a network request."""
        evidence = evidence or {}
        candidates: list[str] = []
        excluded: list[dict[str, str]] = []
        for ident in self.operations_for(capability, aspect):
            op = self.operations[ident]
            family = self.families[op["family"]]
            scope = {**op.get("scope", {}), "auth": family["auth"]}
            if any(getattr(context, k, None) != v for k, v in scope.items()):
                excluded.append({"operation": ident, "reason": "context_mismatch"})
            elif aspect == "status" and evidence.get(
                ident, RouteEvidence()
            ).suspended(now):
                excluded.append({"operation": ident, "reason": "temporarily_quarantined"})
            else:
                candidates.append(ident)

        if preferred and preferred not in candidates:
            raise RegistryError("Selected operation does not match vehicle context")
        chosen = preferred
        if chosen is None:
            if aspect == "status":
                # Existing batch first: never schedule a second GET to learn.
                passive = [
                    ident for ident in candidates
                    if self.operations[ident]["delivery"] == "existing_poll"
                ]
                if passive:
                    chosen = min(passive, key=lambda ident: (
                        -evidence.get(ident, RouteEvidence()).readable,
                        self.operations[ident].get("priority", 100),
                    ))
            else:
                # Choosing a command here never invokes it: the HA user still
                # has to press ON/OFF. No automatic fallback or retries.
                if candidates:
                    chosen = min(candidates, key=lambda ident: self.operations[ident].get(
                        "priority", 100
                    ))

        return {
            "operation": chosen,
            "reason": "preferred" if preferred else (
                "existing_poll" if aspect == "status" and chosen
                else "manual_control_only" if chosen
                else "no_applicable_route"
            ),
            "available_operations": candidates,
            "excluded": excluded,
        }

    def extract(self, operation: str, payload: Any) -> tuple[Any, str | None]:
        """Read a dotted JSON response path, never eval/Jinja user content."""
        op = self.operations[operation]
        if op["method"] != "GET":
            raise RegistryError("Only a GET response may be extracted")
        for path in op["response_paths"]:
            result = payload
            for key in path.split("."):
                if not isinstance(result, dict) or key not in result:
                    result = None
                    break
                result = result[key]
            if result is not None:
                return result, path
        return None, None
