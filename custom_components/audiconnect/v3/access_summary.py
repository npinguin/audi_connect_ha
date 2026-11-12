"""Read-only access data display. Stale or partial is never a safe closed state."""
from .freshness import capture_age_minutes

COMPONENTS = {
    "door": ("frontLeft", "frontRight", "rearLeft", "rearRight", "trunk", "bonnet"),
    "window": ("frontLeft", "frontRight", "rearLeft", "rearRight"),
}

def access_summary(car, kind):
    row = car.readings.get(kind + "_detail", {})
    value = row.get("value")
    rows = value.get("items", []) if isinstance(value, dict) else []
    names = COMPONENTS[kind]
    # Only explicitly known components. Contradictions and duplicates are unknown.
    states = {}
    for component in rows:
        name, tokens = component.get("name"), component.get("status")
        if name not in names:
            continue
        state = "unknown"
        if isinstance(tokens, list) and "unsupported" not in tokens:
            if ("open" in tokens) != ("closed" in tokens):
                state = "open" if "open" in tokens else "closed"
        states[name] = "unknown" if name in states else state
    states = {name: states.get(name, "unknown") for name in names}
    age = capture_age_minutes(row.get("captured"))
    aggregate = ("open" if "open" in states.values() else
                 "closed" if all(s == "closed" for s in states.values()) else "unknown")
    state = ("unknown" if age is None else "stale" if age > 60 else aggregate)
    return state, {"components": states, "last_reported_aggregate": aggregate,
                   "vehicle_captured": row.get("captured"), "age_minutes": age,
                   "cloud_observed": row.get("observed"),
                   "freshness": "unknown" if age is None else "stale" if age > 60 else "fresh",
                   "complete": all(s != "unknown" for s in states.values())}
