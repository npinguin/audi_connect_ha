"""Capability snapshot: no raw vehicle identifiers or private HAR fields."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
p = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/capability_catalog.py"
spec = importlib.util.spec_from_file_location("audi_capability_catalog", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_three_way_verdict_and_no_ids():
    car = NS(capabilities=frozenset(["charging", "vehicleWakeUp", "SECRET_CUSTOM"]),
             impaired_capabilities=frozenset(["vehicleWakeUp"]),
             has_capability=lambda c: c in ["charging", "vehicleWakeUp", "SECRET_CUSTOM"])
    data = m.snapshot_capabilities(car)
    assert data["groups"]["charging"]["charging"] == "reported"
    assert data["groups"]["remote"]["vehicleWakeUp"] == "reported_impaired"
    assert data["groups"]["service"]["dealerAppointment"] == "not_reported_for_this_vehicle"
    assert "SECRET_CUSTOM" not in repr(data)
    assert data["command_authorization_confirmed"] is False

def test_empty_capabilities_are_unknown():
    car = NS(capabilities=frozenset(), impaired_capabilities=frozenset(),
             has_capability=lambda c: None)
    data = m.snapshot_capabilities(car)
    assert data["groups"]["charging"]["charging"] == "unknown"



def test_vehicle_context_hints_never_authorize_remote_actions():
    car = NS(car_type="hybrid", model="Audi Q8 TFSI e", model_source="audi_long_name")
    profile = m.describe_vehicle_context(car, uses_auth0=True)
    assert profile["vehicle_type_hint"] == "hybrid_unspecified"
    assert profile["model_family_hint"] == "q8"
    assert profile["api_generation_hint"] == "auth0_cariad"
    assert profile["model_inference_authorizes_commands"] is False
    assert profile["wake_policy"] == "manual_opt_in_only"
    assert "TFSI" not in str(profile)


def test_nickname_is_not_a_verified_model_family():
    car = NS(car_type=None, model="Q8", model_source="nickname_fallback")
    profile = m.describe_vehicle_context(car, uses_auth0=False)
    assert profile["vehicle_type_hint"] == "unknown"
    assert profile["model_family_hint"] == "unverified"
