"""V3 previous fixbranch trip routes and safe normalization."""
from types import SimpleNamespace as NS
from datetime import UTC, datetime
import pytest

from custom_components.audiconnect.v3.trips import normalize_cariad_trip
from custom_components.audiconnect.v3.family_executors import CARIADExecutor

VIN = "WAUZZZ4M0MD123456"

def test_trip_routes_read_only_allowlist():
    auth = NS(uses_auth0=True, country="DE", access_token=lambda family: "test")
    for suffix in ("shortterm", "longterm", "shortterm/last"):
        path = f"/vehicle/v1/trips/{VIN}/{suffix}"
        assert CARIADExecutor().plan(auth, "GET", path).url.endswith(path)
        with pytest.raises(ValueError):
            CARIADExecutor().plan(auth, "POST", path, {}, explicit_action=True)
    with pytest.raises(ValueError):
        CARIADExecutor().plan(auth, "GET", f"/vehicle/v1/trips/{VIN}/unknown")

def test_trip_normalization_never_invents_units_or_timestamp():
    stamp = datetime.now(UTC).isoformat()
    trip, verdict = normalize_cariad_trip({"data": [{"tripEndTimestamp": stamp,
        "mileage_km": 35, "averageFuelConsumption_L_per_100km": 7.3}]})
    assert verdict == "normalized"
    assert trip["mileage"] == 35
    assert trip["averageFuelConsumption"] == 7.3
    assert trip["tripID"] is None
    assert normalize_cariad_trip({"mileage_km": 20})[0] is None
    assert normalize_cariad_trip({"timestamp": stamp, "averageFuelConsumption": 81})[0] is None
