"""Declarative API response normalization using Home Assistant unit converters.

The API definition owns the conversion. Entity code never changes a value.
Only standard, whitelisted HA unit families are executable; no eval or
untrusted Python expressions, implicit scaling or assumptions about source.
"""
from __future__ import annotations
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, Mapping
from homeassistant.util.unit_conversion import (
    DistanceConverter, DurationConverter, ElectricCurrentConverter,
    PowerConverter, TemperatureConverter, EnergyConverter, SpeedConverter,
)

_CONVERTERS = {
    "distance": DistanceConverter,
    "duration": DurationConverter,
    "current": ElectricCurrentConverter,
    "power": PowerConverter,
    "temperature": TemperatureConverter,
    "energy": EnergyConverter,
    "speed": SpeedConverter,
}

@lru_cache(maxsize=1)
def _route_mappings() -> dict[str, dict[str, dict[str, Any]]]:
    doc = json.loads(Path(__file__).with_name("api_value_mappings.json").read_text())
    if doc.get("schema_version") != 1 or not isinstance(doc.get("routes"), dict):
        raise ValueError("Invalid Audi V3 API conversion catalog")
    return doc["routes"]

def transform_for(family: str, attribute: str) -> dict[str, Any] | None:
    return _route_mappings().get(family, {}).get(attribute)

def validate_transform(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"unit_class", "from", "to"}:
        raise ValueError("Invalid API unit conversion definition")
    cls = _CONVERTERS.get(value["unit_class"])
    if (cls is None or value["from"] not in cls.VALID_UNITS
            or value["to"] not in cls.VALID_UNITS):
        raise ValueError("Unsupported unit conversion")
    return dict(value)

def normalize_api_value(raw: Any, conversion: Mapping[str, Any] | None) -> Any:
    if conversion is None:
        return raw
    t = validate_transform(conversion)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        raise ValueError("Unit conversion requires a finite numeric source")
    cls = _CONVERTERS[t["unit_class"]]
    return cls.convert(raw, t["from"], t["to"])
