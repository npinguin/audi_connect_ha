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


def test_no_v3_probe_services_in_public_contract():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"
    yaml = (root / "services.yaml").read_text()
    for name in ("probe_api_paths", "probe_vehicle_health", "probe_trip_data", "refresh_trip_data"):
        assert f"\n{name}:" not in yaml
    init = (root / "__init__.py").read_text()
    assert "SERVICE_PROBE_API_PATHS" not in init
    assert "_handle_probe_api_paths" not in init
    assert "PROBE_SCHEMA" not in init
    assert "probe_read_only_api(" not in init
    assert 'for obsolete in ("probe_api_paths", "probe_vehicle_health", "probe_trip_data", "refresh_trip_data"):' in init
    engine = (root / "v3" / "engine.py").read_text()
    assert "async def restore_reads(" not in engine
    status = (root / "v3" / "status_engine.py").read_text()
    assert "await self._poll_trips(car)" in status


def test_trip_data_poll_uses_one_cadence_and_retains_existing_data():
    import asyncio
    from unittest.mock import AsyncMock
    from custom_components.audiconnect.v3.status_engine import StatusEngine
    from custom_components.audiconnect.v3.vehicle import V3Vehicle
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    stamp = datetime.now(UTC).isoformat()
    transport = NS(remaining_calls=100, request=AsyncMock(return_value=NS(
        status=200, data={"data":[{"tripEndTimestamp": stamp, "mileage_km": 35}]}
    )))
    engine = NS(transport=transport, _trip_poll_at={})
    asyncio.run(StatusEngine._poll_trips(engine, car))
    assert transport.request.await_count == 3
    assert car.trips["shortterm_current"]["mileage"] == 35
    asyncio.run(StatusEngine._poll_trips(engine, car))
    assert transport.request.await_count == 3
