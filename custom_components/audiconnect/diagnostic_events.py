"""Bounded, privacy-safe Audi API observations; never retain raw HTTP data."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit

_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def classify_route(url: str) -> str:
    """Return a fixed category, never a raw URL (which can contain a VIN)."""
    path = urlsplit(url).path.lower()
    if "/services/rlu_v1/" in path or "security-pin-auth-requested" in path:
        return "remote_lock_authorization"
    if "/fs-car/bs/climatisation/" in path:
        return "legacy_climatisation"
    if "/auxiliaryheating/" in path:
        return "auxiliary_heating"
    if "/climatisation/" in path:
        return "modern_climatisation"
    if "/engine/" in path:
        return "remote_engine"
    if "/charging/" in path or "/charger/" in path:
        return "charging"
    if "/pendingrequests" in path:
        return "command_confirmation"
    if "selectivestatus" in path:
        return "selective_status"
    if "/trip" in path:
        return "trip_data"
    if "/position" in path:
        return "vehicle_position"
    return "other"


def build_http_event(method: str, url: str, status: int) -> dict[str, object] | None:
    """Observe mutating calls and HTTP errors without requesting extra data."""
    method = method.upper()
    if method not in _MUTATION_METHODS and status < 400:
        return None
    return {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "method": method if method in _MUTATION_METHODS or method == "GET" else "OTHER",
        "route": classify_route(url),
        "http_status": int(status),
        "outcome": (
            "http_rejected" if status >= 400 else
            "http_accepted_not_vehicle_confirmed" if method in _MUTATION_METHODS else
            "http_response"
        ),
    }
