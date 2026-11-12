"""Last response evidence is private, redacted and durable across restarts."""
from datetime import UTC, datetime
import json
import pytest

from custom_components.audiconnect.v3.api_observations import (
    MAX_ROUTES, record_for, save_record, validate_record,
)
from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
from custom_components.audiconnect.v3.profile_store import restore_profile
from custom_components.audiconnect.v3.registry import CapabilityRegistry, VehicleContext
from custom_components.audiconnect.v3.runtime import catalog_path


def test_safe_read_record_roundtrip_and_no_vin_or_secret():
    reg=CapabilityRegistry.from_json_file(catalog_path())
    ctx=VehicleContext(auth="auth0")
    profile=DevelopmentProfile(reg,ctx)
    rec=record_for(family="cariad",method="GET",http_status=200,
        vin="WAUZZZ4M0MD123456",at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        payload={"charging":{"value":{"soc":97}},"vin":"WAUZZZ4M0MD123456",
                 "email":"test@example.com","spin":"1234","coordinates":[50.1,4.2]})
    save_record(profile,"cariad.status.charging",rec)
    data=json.dumps(profile.snapshot())
    for secret in ("WAUZZZ4M0MD123456","test@example.com","1234","50.1"):
        assert secret not in data
    assert '"soc": 97' in data
    assert rec["preview"]["coordinates"] == "[redacted]"
    loaded=restore_profile(reg,ctx,profile.snapshot())
    assert loaded.api_observations==profile.api_observations

def test_control_responses_are_never_stored_raw():
    x=record_for(family="cariad",method="POST",http_status=202,
        vin="WAUZZZ4M0MD123456",payload={"token":"SECRET","state":"unlock"})
    assert x["preview"]=="[control response withheld: security]"
    with pytest.raises(ValueError):
        validate_record({**x,"preview":{"state":"unlock"}})

def test_history_bound():
    class Profile: api_observations={}
    p=Profile();p.api_observations={}
    for i in range(60):
        save_record(p,f"route_{i}",record_for(
            family="mbb",method="GET",http_status=404,vin="",payload=None))
    assert len(p.api_observations)==MAX_ROUTES
    assert "route_0" not in p.api_observations

def test_unimplemented_climate_adapter_is_excluded_but_bodyless_is_manual_candidate():
    m=CapabilityRegistry.from_json_file(catalog_path())
    values=m.resolve("climate","start",VehicleContext(auth="auth0"))
    assert "cariad.climate.start.vehicle_settings" not in values["available_operations"]
    assert "cariad.climate.start.stored" in values["available_operations"]
    assert values["operation"]=="cariad.climate.start.stored"
