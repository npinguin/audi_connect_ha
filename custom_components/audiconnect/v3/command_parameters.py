"""Canonical input binding for local, physically reviewed command variants.

The mapping is configuration; semantic limits and protected settings handlers
remain code-owned. Unbound experimental parameters never become HA controls.
"""
from __future__ import annotations

import math


# The raw-template path is deliberately narrow. Settings PUTs use a reviewed
# read-modify-write handler, rather than an arbitrary replacement body.
_BINDABLE = {
    ("climate", "start_with_settings"): {
        "temp_c": ("number", 15, 30),
        "temp_f": ("number", 59, 86),
    },
}


def validate_bindings(capability, aspect, variables, bindings):
    if not isinstance(bindings, dict) or set(bindings) != set(variables):
        raise ValueError("Runtime parameter bindings must cover every variable")
    schema = _BINDABLE.get((capability, aspect), {})
    if not bindings or len(bindings) != len(set(bindings.values())):
        raise ValueError("Invalid runtime parameter binding")
    if len(bindings) != 1:
        raise ValueError("Choose exactly one canonical temperature input")
    for variable, semantic in bindings.items():
        if semantic not in schema or variables[variable] not in ("integer", "number"):
            raise ValueError("Unapproved semantic parameter binding")
    return dict(bindings)


def map_parameters(route, supplied):
    bindings = route.get("parameter_bindings", {})
    if not bindings:
        return supplied
    schema = _BINDABLE[(route["capability"], route["aspect"])]
    supplied = supplied or {}
    if set(supplied) != set(bindings.values()):
        raise ValueError("Supply the exact declared semantic command parameters")
    rendered = {}
    for variable, semantic in bindings.items():
        value = supplied[semantic]
        _, low, high = schema[semantic]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Command parameter is outside its approved range")
        if route["variables"][variable] == "integer":
            if int(value) != value:
                raise ValueError("Command parameter requires an integer")
            value = int(value)
        rendered[variable] = value
    return rendered


def runtime_ready(route):
    return not route.get("variables") or bool(route.get("parameter_bindings"))
