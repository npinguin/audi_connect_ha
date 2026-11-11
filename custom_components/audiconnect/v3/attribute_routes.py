"""Safe per-attribute V3 API route variants. Read-only discovery only.

The historical inventory remains global; route choices and evidence are per vehicle.
Explicit GET tests never promote a control or authorize future POST requests.
"""
from __future__ import annotations
import re
from typing import Any, Mapping
from .historical_catalog import ATTRIBUTES
from .legacy_read_mappings import variant_for
from .api_value_mappings import transform_for, validate_transform

_BASE = "/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs={JOBS}"
_ID = re.compile(r"^user\.read\.[a-z][a-z0-9_]{0,40}$")
_PATH = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")


def validate_custom_read_route(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"id", "attribute", "family", "method", "path", "response_path"}
    if not isinstance(value, Mapping) or not required <= set(value) or set(value) - required - {"conversion"}:
        raise ValueError("Invalid custom read route fields")
    ident, attr = value["id"], value["attribute"]
    if not isinstance(ident, str) or not _ID.fullmatch(ident) or attr not in ATTRIBUTES:
        raise ValueError("Unknown attribute or invalid route ID")
    if value["family"] != "cariad" or value["method"] != "GET":
        raise ValueError("Only approved CARIAD GET routes are executable in clean V3")
    path, mapping = value["path"], value["response_path"]
    if not isinstance(path, str) or len(path) > 1024 or not path.startswith("/vehicle/v1/vehicles/{VIN}/"):
        raise ValueError("Custom read path must be VIN-templated CARIAD vehicle route")
    if any(bad in path.lower() for bad in ("://", "#", "\\", "..", "%2e", "%2f", "%5c", "%00")) or any(ord(c) < 32 for c in path):
        raise ValueError("Unsafe custom read path")
    if set(re.findall(r"\{([^{}]+)\}", path)) != {"VIN"} or "{" in path.replace("{VIN}", "") or "}" in path.replace("{VIN}", ""):
        raise ValueError("Only the VIN placeholder is permitted")
    if not isinstance(mapping, str) or len(mapping) > 180 or not _PATH.fullmatch(mapping):
        raise ValueError("Invalid response mapping")
    if "conversion" in value:
        validate_transform(value["conversion"])
    return dict(value)


def read_variants(attribute: str, custom: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if attribute not in ATTRIBUTES:
        raise ValueError("Unknown historical attribute")
    field = ATTRIBUTES[attribute]
    variants = []
    if field["paths"] and field["job"]:
        variants.extend((
            {"id": "cariad.selectivestatus.batch", "family": "cariad", "method": "GET",
             "path": _BASE, "response_paths": field["paths"], "kind": "shared_batch",
             "conversion": transform_for("cariad", attribute)},
            {"id": "cariad.selectivestatus.targeted", "family": "cariad", "method": "GET",
             "path": _BASE.replace("{JOBS}", field["job"]),
             "response_paths": field["paths"], "kind": "targeted_job",
             "conversion": transform_for("cariad", attribute)},
        ))
    legacy = variant_for(attribute)
    if legacy is not None:
        legacy["conversion"] = transform_for("mbb", attribute)
        variants.append(legacy)
    for ident, value in custom.items():
        if value.get("attribute") == attribute:
            variants.append({"id": ident, "family": value["family"],
                "method": "GET", "path": value["path"],
                "response_paths": [value["response_path"]], "kind": "custom",
                "conversion": value.get("conversion")})
    return variants


def get_read_variant(attribute: str, route: str, custom: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    found = next((r for r in read_variants(attribute, custom) if r["id"] == route), None)
    if not found:
        raise ValueError("Unknown or non-applicable read-only API variant")
    return found
