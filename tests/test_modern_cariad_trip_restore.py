"""Modern Auth0 trip reads: normalized fields, privacy, cooldown and HA IDs."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.audiconnect.audi_connect_account import (
    AudiConnectAccount,
    AudiConnectVehicle,
)
from custom_components.audiconnect.trip_restore import normalize_cariad_trip
from custom_components.audiconnect.util import parse_datetime

VIN = "SYNTHETICVIN000001"

_LAST_TRIP = {
    "data": {
        "id": "private-trip-id",
        "tripEndTimestamp": "2026-11-10T21:00:00Z",
        "tripType": "shortTerm",
        "mileage_km": 40,
        "startMileage_km": 65428,
        "overallMileage_km": 65469,
        "travelTime": 73,
        "averageFuelConsumption": 8.1,
        "averageSpeed_kmph": 33,
        "totalFuelConsumption_L": 3.24,
        "averageElectricEngineConsumption": 123,
    }
}


def test_known_unit_suffixed_cariad_fields_are_normalized_without_legacy_scaling():
    trip, status = normalize_cariad_trip(_LAST_TRIP)
    assert status == "normalized"
    assert trip["mileage"] == 40
    assert trip["overallMileage"] == 65469
    assert trip["averageFuelConsumption"] == 8.1
    assert trip["averageSpeed"] == 33
    assert trip["traveltime"] == 73
    assert trip["tripID"] is None
    assert trip["averageElectricEngineConsumption"] is None
    assert parse_datetime(trip["timestamp"]) == datetime(
        2026, 11, 10, 21, 0, tzinfo=UTC
    )
    assert "private-trip-id" not in repr(trip)


def test_explicit_electric_unit_is_safe_without_guessing_legacy_tenths():
    payload = {
        "data": {
            "tripEndTimestamp": "2026-11-10T21:00:00Z",
            "mileage_km": 10,
            "averageElectricEngineConsumption_kWh_per_100km": 25.3,
        }
    }
    trip, status = normalize_cariad_trip(payload)
    assert status == "normalized"
    assert trip["averageElectricEngineConsumption"] == 25.3
    assert trip["units"]["averageElectricEngineConsumption"] == "kWh/100km"


def test_newest_trip_selected_from_known_bounded_list():
    payload = {
        "data": {
            "trips": [
                {"tripEndTimestamp": "2026-11-09T21:00:00Z", "mileage_km": 12},
                {"tripEndTimestamp": "2026-11-10T21:00:00Z", "mileage_km": 14},
            ]
        }
    }
    trip, status = normalize_cariad_trip(payload)
    assert status == "normalized"
    assert trip["mileage"] == 14


@pytest.mark.parametrize(
    "payload",
    [
        {"data": {"id": "not-a-trip"}},
        {"data": [{"mileage_km": 10}]},
        {"data": {"tripEndTimestamp": "invalid", "mileage_km": 10}},
        {"data": {"tripEndTimestamp": "2026-11-10T21:00:00Z",
                  "mileage_km": "unknown"}},
        {"error": {"status": 404}},
        None,
    ],
)
def test_missing_or_bad_schema_does_not_create_fake_data(payload):
    trip, status = normalize_cariad_trip(payload)
    assert trip is None
    assert status != "normalized"


class _ReadService:
    uses_auth0 = True

    def __init__(self, data=None):
        self._api = SimpleNamespace(vcf_remaining_calls=None)
        self.calls = []
        self.data = data or {
            "shortterm": _LAST_TRIP,
            "longterm": _LAST_TRIP,
            "shortterm/last": _LAST_TRIP,
        }

    async def get_auth0_trip_payload(self, vin, kind):
        self.calls.append((vin, kind))
        return self.data[kind]


def _account(service=None):
    service = service or _ReadService()
    vehicle = AudiConnectVehicle(service, SimpleNamespace(vin=VIN))
    connection = object.__new__(AudiConnectAccount)
    connection._loggedin = True
    connection._audi_service = service
    connection._vehicles = [vehicle]
    connection._readonly_probe_lock = asyncio.Lock()
    connection._readonly_probe_attempted = {}
    connection._readonly_probe_reports = {}
    connection._modern_trip_reports = {}
    return connection, vehicle, service


def test_explicit_trip_refresh_fills_only_current_and_last_not_guessed_reset():
    account, vehicle, service = _account()
    report = asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert report["attempted"] == 3
    assert report["normalized"] == 3
    assert len(service.calls) == 3
    assert vehicle.shortterm_current["mileage"] == 40
    assert vehicle.longterm_current["mileage"] == 40
    assert vehicle.last_trip["averageFuelConsumption"] == 8.1
    assert vehicle.shortterm_reset is None
    assert vehicle.longterm_reset is None
    assert account.get_auth0_trip_report(VIN) == report
    assert VIN not in repr(report)
    assert "private-trip-id" not in repr(report)


def test_second_trip_request_is_blocked_by_cooldown():
    account, _vehicle, service = _account()
    asyncio.run(account.refresh_auth0_trip_data(VIN))
    with pytest.raises(RuntimeError, match="cooldown active"):
        asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert len(service.calls) == 3


def test_shared_diagnostic_probe_cooldown_blocks_trip_read():
    account, _vehicle, service = _account()
    account._readonly_probe_attempted[VIN.lower()] = time.monotonic()
    with pytest.raises(RuntimeError, match="cooldown active"):
        asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert not service.calls


def test_low_known_quota_sends_no_requests():
    account, _vehicle, service = _account()
    service._api.vcf_remaining_calls = 12
    report = asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert report["attempted"] == 0
    assert report["outcome"] == "low_rate_limit_budget"
    assert not service.calls


def test_invalid_payload_does_not_create_trip_state():
    bad = {"data": {"unknown": "value"}}
    service = _ReadService({k: bad for k in ("shortterm", "longterm", "shortterm/last")})
    account, vehicle, service = _account(service)
    report = asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert report["normalized"] == 0
    assert vehicle.last_trip is None
    assert vehicle.shortterm_current is None
    assert vehicle.longterm_current is None


def test_older_response_does_not_overwrite_fresher_trip():
    account, vehicle, _service = _account()
    vehicle._vehicle.state["shortterm_current"] = {
        "timestamp": "2026-11-12T21:00:00.000000Z",
        "mileage": 99,
    }
    report = asyncio.run(account.refresh_auth0_trip_data(VIN))
    assert vehicle.shortterm_current["mileage"] == 99
    assert report["results"][0]["outcome"] == "older_than_existing"
