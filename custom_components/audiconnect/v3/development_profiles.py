"""V3 development profiles: add custom API paths and select proven operations.

Pure domain model: no Home Assistant, HTTP, V2 account, scheduler or secrets.
Instances are scoped to ONE vehicle by the application layer. Only the shared
authentication/config layer may provide context/credentials to the future
V3-owned dispatcher. No arbitrary hosts, auth headers, python or Jinja eval.
"""

from __future__ import annotations

from copy import deepcopy
import re
from string import Formatter
from typing import Any, Mapping
from urllib.parse import quote

from .action_discovery import DiscoveryError, GuidedActionDiscovery
from .registry import CapabilityRegistry, RegistryError, VehicleContext

_ID = re.compile(r"^user\.climate\.(?:status|start|stop)\.[a-z][a-z0-9_]{0,31}$")
_VAR = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")
_TYPE = {"string", "integer", "number", "boolean"}
_SYSTEM = {"VIN", "COUNTRY", "TYPE", "JOBS"}
_SCOPES = {"auth", "region", "vehicle_type", "model_family"}


class DevelopmentProfileError(ValueError):
    """Invalid experimental route, context or capability choice."""


def _placeholders(value: str) -> set[str]:
    found: set[str] = set()
    try:
        for _text, field, format_spec, conversion in Formatter().parse(value):
            if field is not None:
                if not _VAR.fullmatch(field) or format_spec or conversion:
                    raise DevelopmentProfileError("Unsafe template placeholder")
                found.add(field)
    except ValueError as exc:
        raise DevelopmentProfileError("Malformed template") from exc
    return found


def _check_template(value: Any, allowed: set[str], *, depth: int = 0) -> None:
    if depth > 8:
        raise DevelopmentProfileError("Request template too deeply nested")
    if isinstance(value, str):
        if not _placeholders(value) <= allowed:
            raise DevelopmentProfileError("Undeclared request template variable")
        if len(value) > 2048:
            raise DevelopmentProfileError("Request field too long")
    elif isinstance(value, dict):
        if len(value) > 50 or any(
            not isinstance(k, str) or len(k) > 64 or "{" in k
            for k in value
        ):
            raise DevelopmentProfileError("Invalid JSON object keys")
        for field in value.values():
            _check_template(field, allowed, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 50:
            raise DevelopmentProfileError("Request array too long")
        for item in value:
            _check_template(item, allowed, depth=depth + 1)
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise DevelopmentProfileError("Invalid request template value")


def _validated_route(
    data: Mapping[str, Any], known_families: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(data, Mapping) or set(data) - {
        "id", "capability", "aspect", "family", "method", "path",
        "variables", "body", "response_paths", "scope", "description",
    }:
        raise DevelopmentProfileError("Unknown custom operation fields")
    operation_id = data.get("id")
    if not isinstance(operation_id, str) or not _ID.fullmatch(operation_id):
        raise DevelopmentProfileError("Invalid namespaced user operation ID")
    capability, aspect = data.get("capability"), data.get("aspect")
    if capability != "climate" or aspect not in ("status", "start", "stop"):
        raise DevelopmentProfileError("V3 pilot only models climate status/start/stop")
    if not operation_id.startswith(f"user.{capability}.{aspect}."):
        raise DevelopmentProfileError("Operation ID must match its capability and aspect")
    family = data.get("family")
    if family not in known_families:
        raise DevelopmentProfileError("Unknown API family")
    method = data.get("method")
    if method != ("GET" if aspect == "status" else "POST"):
        raise DevelopmentProfileError("Only GET status and POST controls in pilot")
    path = data.get("path")
    if not isinstance(path, str) or not 1 <= len(path) <= 1024:
        raise DevelopmentProfileError("Invalid path length")
    if (
        not path.startswith("/") or path.startswith("//") or "://" in path
        or "\\" in path or ".." in path or "#" in path or any(ord(c) < 32 for c in path)
        or re.search(r"%(?:2e|2f|5c|00)", path, re.IGNORECASE)
    ):
        raise DevelopmentProfileError("Only safe API-family-relative paths allowed")
    if "{VIN}" not in path:
        raise DevelopmentProfileError("Vehicle route must use {VIN}, never a fixed VIN")
    variables = data.get("variables", {})
    if (
        not isinstance(variables, dict) or len(variables) > 12
        or any(
            not isinstance(name, str) or not _VAR.fullmatch(name)
            or name in _SYSTEM or value not in _TYPE
            for name, value in variables.items()
        )
    ):
        raise DevelopmentProfileError("Invalid typed parameter declarations")
    allowed = set(variables) | _SYSTEM
    if not _placeholders(path) <= allowed:
        raise DevelopmentProfileError("Undeclared API path placeholder")
    body = deepcopy(data.get("body"))
    if aspect == "status" and body is not None:
        raise DevelopmentProfileError("GET status never carries a request body")
    _check_template(body, allowed)
    response_paths = data.get("response_paths", [])
    if not isinstance(response_paths, list) or (
        aspect == "status" and not response_paths
    ) or any(
        not isinstance(x, str) or not x or len(x) > 180
        or not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", x)
        for x in response_paths
    ):
        raise DevelopmentProfileError("Invalid response field mappings")
    scope = data.get("scope", {})
    if not isinstance(scope, dict) or set(scope) - _SCOPES or any(
        not isinstance(x, str) or len(x) > 60 for x in scope.values()
    ):
        raise DevelopmentProfileError("Invalid optional context scope")
    if "auth" in scope and scope["auth"] != known_families[family]["auth"]:
        raise DevelopmentProfileError("Context auth conflicts with API family")
    description = data.get("description", "")
    if not isinstance(description, str) or len(description) > 180:
        raise DevelopmentProfileError("Invalid route description")
    return {
        "id": operation_id,
        "capability": capability,
        "aspect": aspect,
        "family": family,
        "method": method,
        "path": path,
        "variables": deepcopy(variables),
        "body": body,
        "response_paths": list(response_paths),
        "scope": dict(scope),
        "description": description,
    }


def _typed_value(value: Any, kind: str) -> Any:
    if kind == "string" and isinstance(value, str) and len(value) <= 256:
        return value
    if kind == "integer" and type(value) is int:
        return value
    if kind == "number" and type(value) in (int, float) and abs(value) <= 1e9:
        return value
    if kind == "boolean" and type(value) is bool:
        return value
    raise DevelopmentProfileError("Missing or invalid typed API parameter")


def _fill_request(template: Any, params: Mapping[str, Any]) -> Any:
    if isinstance(template, dict):
        return {k: _fill_request(v, params) for k, v in template.items()}
    if isinstance(template, list):
        return [_fill_request(v, params) for v in template]
    if not isinstance(template, str):
        return template
    parts = list(Formatter().parse(template))
    if len(parts) == 1 and parts[0][0] == "" and parts[0][1] in params:
        return params[parts[0][1]]
    return template.format_map({
        key: str(value).lower() if type(value) is bool else str(value)
        for key, value in params.items()
    })


class DevelopmentProfile:
    """Per-vehicle experimental routes, results and an explicit active choice.

    Built-in routes stay in the immutable generic catalog. User routes are
    overlays. A verified result only promotes the selected route for this
    instance, not for every Audi or other vehicles in the account.
    """

    def __init__(
        self, catalog: CapabilityRegistry, context: VehicleContext,
        *, cooldown_seconds: float = 15
    ) -> None:
        self._base = {
            "schema_version": 1,
            "brand": "audi",
            "api_families": deepcopy(catalog.families),
            "operations": deepcopy(catalog.operations),
            "capabilities": deepcopy(catalog.capabilities),
        }
        self.custom: dict[str, dict[str, Any]] = {}
        self.active: dict[str, str] = {}
        self.registry = CapabilityRegistry(deepcopy(self._base))
        self.discovery = GuidedActionDiscovery(
            self.registry, context, cooldown_seconds=cooldown_seconds
        )

    def add(self, operation: Mapping[str, Any]) -> str:
        """Add a user-authored operation, purely as a development definition."""
        data = _validated_route(operation, self._base["api_families"])
        ident = data["id"]
        if ident in self.registry.operations:
            raise DevelopmentProfileError("Operation ID already exists")
        overlay = deepcopy(self._base)
        for row in [*self.custom.values(), data]:
            row_id = row["id"]
            op: dict[str, Any] = {
                "family": row["family"],
                "method": row["method"],
                "path": row["path"],
                "delivery": "manual",
                "scope": row["scope"],
                "priority": 1000,
                "request_variables": row["variables"],
                "request_body": row["body"],
            }
            if row["method"] == "GET":
                op["response_paths"] = row["response_paths"]
            overlay["operations"][row_id] = op
            target = (
                overlay["capabilities"]["climate"]["status"]
                if row["aspect"] == "status" else
                overlay["capabilities"]["climate"]["control"][row["aspect"]]
            )
            target["operations"].append(row_id)
        try:
            # The base registry enforces ownership, known families, methods,
            # scoped vehicle applicability and relative endpoint rules.
            self.registry = CapabilityRegistry(overlay)
        except RegistryError as exc:
            raise DevelopmentProfileError("Registry rejected user API path") from exc
        self.custom[ident] = data
        self.discovery.registry = self.registry
        return ident

    def candidates(self, capability: str, action: str) -> list[dict[str, str]]:
        return self.discovery.candidates(capability, action)

    def begin_test(self, capability: str, action: str, operation: str, *, now: float):
        """Called only after an authenticated user clicks Test."""
        return self.discovery.begin(
            capability, action, operation, user_initiated=True, now=now
        )

    def observe_http(self, sequence: int, status: int | None) -> None:
        self.discovery.observe_transport(sequence, http_status=status)

    def confirm(
        self, sequence: int, *, worked: bool | None,
        inspected_vehicle: bool, now: float
    ) -> None:
        attempted = self.discovery.review(
            sequence,
            result="uncertain" if worked is None else "worked" if worked else "failed",
            inspected_vehicle=inspected_vehicle,
            now=now,
        )
        key = f"{attempted.capability}.{attempted.action}"
        if attempted.result != "worked" and self.active.get(key) == attempted.operation:
            # A later failure/uncertainty invalidates this vehicle's active
            # mapping. Never keep advertising a known-broken command.
            self.active.pop(key)

    def choose_working(self, capability: str, action: str, operation: str) -> None:
        """Configuration can activate ONLY a confirmed working variant."""
        key = f"{capability}.{action}"
        if key in self.discovery.disabled:
            raise DevelopmentProfileError("Action is disabled")
        if operation not in self.registry.resolve(
            capability, action, self.discovery.context
        )["available_operations"]:
            raise DevelopmentProfileError("Route is not applicable")
        results = [
            row.result for row in self.discovery.history
            if row.capability == capability and row.action == action
            and row.operation == operation
        ]
        if not results or results[-1] != "worked":
            raise DevelopmentProfileError("Latest real vehicle test must confirm this route")
        self.active[key] = operation

    def disable(self, capability: str, action: str) -> None:
        self.discovery.disable(capability, action)
        self.active.pop(f"{capability}.{action}", None)

    def snapshot(self) -> dict[str, Any]:
        """Safe local profile record. No VIN, tokens or raw HTTP payloads."""
        return {
            "schema_version": 1,
            "custom_routes": deepcopy(list(self.custom.values())),
            "active": dict(self.active),
            "discovery": self.discovery.snapshot(),
        }

    def preview_request(
        self, operation: str, *, vehicle_values: Mapping[str, str],
        user_values: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Render a local request preview; never send it or export the VIN."""
        if operation not in self.custom:
            raise DevelopmentProfileError("Only custom routes may be previewed here")
        data = self.custom[operation]
        values: dict[str, Any] = {}
        for key in _SYSTEM:
            if key in vehicle_values:
                values[key] = vehicle_values[key]
        for key, kind in data["variables"].items():
            if key not in (user_values or {}):
                raise DevelopmentProfileError("Missing custom request parameter")
            values[key] = _typed_value(user_values[key], kind)
        required = _placeholders(data["path"])
        if not required <= set(values):
            raise DevelopmentProfileError("Missing vehicle context placeholder")
        encoded = {
            k: quote(str(v).lower() if type(v) is bool else str(v), safe="")
            for k, v in values.items()
        }
        path = data["path"].format_map(encoded)
        # Approved host and current token are selected by the future V3-only
        # adapter, never by custom template data or local control parameters.
        return {
            "method": data["method"],
            "family": data["family"],
            "relative_path": path,
            "json_body": _fill_request(data["body"], values),
            "experimental_only": True,
        }
