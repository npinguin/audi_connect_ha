"""Private VIN-scoped manufacturer metadata; never an authorization source."""
from datetime import datetime
from .vehicle import model_family_from_name

def validate_identity(row, region):
    if not isinstance(row, dict) or row.get("region") != region:
        return {}
    model, source, year = row.get("model"), row.get("source"), row.get("year", "")
    stamp = row.get("observed_at")
    if (not isinstance(model, str) or not 0 < len(model) <= 120
            or model.strip().lower() in ("", "unknown", "invalid", "unavailable", "unsupported", "error")
            or source not in ("audi_long_name", "audi_short_name")
            or not isinstance(year, str) or (year and (not year.isdigit() or len(year) != 4
                                                       or not 1980 <= int(year) <= 2100))):
        return {}
    try:
        if datetime.fromisoformat(stamp).tzinfo is None:
            return {}
    except (TypeError, ValueError):
        return {}
    from .transport import IDENTITY_QUERIES, INVENTORY_OPERATION
    operation = row.get("operation", INVENTORY_OPERATION)
    if operation not in IDENTITY_QUERIES or operation.endswith(".images"):
        operation = INVENTORY_OPERATION
    return {"model": model, "source": source, "year": year, "region": region, "operation": operation,
            "family": model_family_from_name(model), "observed_at": stamp}

def apply_cached_identity(car, row):
    identity = validate_identity(row, car.country)
    if not car.model and identity:
        car.model = identity["model"]
        car.model_family = identity["family"]
        car.model_year = car.model_year or identity["year"]
        car.model_source = identity["source"]
        car.identity_restored = True
        car.identity_observed_at = identity["observed_at"]
        car.identity_operation = identity["operation"]
        if car.name == "Audi vehicle":
            car.name = car.model

def capture_identity(car):
    if car.identity_restored or not car.model or not car.identity_observed_at:
        return {}
    return validate_identity({"model": car.model, "source": car.model_source,
        "year": car.model_year, "region": car.country,
        "observed_at": car.identity_observed_at, "operation": car.identity_operation}, car.country)


def previous_registry_model(hass, entry, vin):
    """Presentation-only migration aid. No other integration or user label."""
    from homeassistant.helpers import device_registry as dr
    from ..const import DOMAIN
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, vin.lower())})
    if device is None or entry.entry_id not in device.config_entries or device.manufacturer != "Audi":
        return None
    model = device.model
    if (isinstance(model, str) and 0 < len(model.strip()) <= 120
            and model.strip().lower() not in ("audi", "audi vehicle", "unknown", "unavailable", "none")):
        return model.strip()
    return None
