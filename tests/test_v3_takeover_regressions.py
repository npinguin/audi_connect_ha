"""Regression tests for issues exposed by the b12 completeness diagnostics."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from custom_components.audiconnect.v3.attribute_runtime import _accept_observation
from custom_components.audiconnect.v3.derived_values import observe_derived
from custom_components.audiconnect.v3.response_preview import safe_schema_inventory, validate_schema_fields
from custom_components.audiconnect.v3.structured_details import observe_structured, details_for
from custom_components.audiconnect.v3.vehicle import V3Vehicle

VIN = "WAUZZZ4M0MD123456"


def test_parking_light_never_uses_other_light_types():
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    now = datetime.now(UTC)
    def observe(lights):
        observe_derived(car, SimpleNamespace(), {"vehicleLights": {"lightsStatus": {"value": {
            "carCapturedTimestamp": now.isoformat(), "lights": lights}}}}, now, _accept_observation)
    observe([{"name": "parkingLight", "status": "off"}, {"name": "headlight", "status": "on"}])
    assert car.readings["parking_light"]["value"] is False
    observe([{"name": "headlight", "status": "on"}])
    assert car.readings["parking_light"]["value"] is None


def test_partial_access_report_invalidates_missing_or_contradictory_components():
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    now = datetime.now(UTC)
    def observe(stamp, rows):
        observe_derived(car, SimpleNamespace(), {"access": {"accessStatus": {"value": {
            "carCapturedTimestamp": stamp.isoformat(), "doors": rows}}}}, stamp, _accept_observation)
    observe(now, [{"name": "frontLeft", "status": ["closed", "locked"]}])
    assert car.readings["left_front_door_open"]["value"] is False
    observe(now + timedelta(seconds=1), [{"name": "frontRight", "status": ["open", "closed"]}])
    assert car.readings["left_front_door_open"]["value"] is None
    assert car.readings["right_front_door_open"]["value"] is None


def test_structured_timers_services_and_components_are_bounded_and_typed():
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    now = datetime.now(UTC)
    stamp = now.isoformat()
    payload = {
        "chargingTimers": {"chargingTimersStatus": {"value": {
            "carCapturedTimestamp": stamp, "timers": [
                {"id": 1, "enabled": True, "recurringTimer": {
                    "departureTimeLocal": "07:30", "repetitionDays": ["monday"]},
                    "latitude": 50.1, "secret": "private"},
                {"id": 2, "enabled": False, "singleTimer": {"startDateTimeLocal": "2026-11-13T07:30:00"}}]}}},
        "userCapabilities": {"capabilitiesStatus": {"value": [
            {"id": "charging", "expirationDate": "2027-01-01T00:00:00Z",
             "userDisablingAllowed": False, "secret": "private"}]}},
        "access": {"accessStatus": {"value": {"carCapturedTimestamp": stamp,
            "overallStatus": "safe", "doors": [{"name": "frontLeft", "status": ["closed", "locked"]}]}}},
    }
    observe_structured(car, payload, now, _accept_observation)
    info = details_for(car, "charging_timers_detail", "connected_services_detail", "door_detail")
    assert info["charging_timers"]["data"]["items"][0]["departure_time_local"] == "07:30"
    assert info["charging_timers"]["data"]["items"][1]["start_datetime_local"] == "2026-11-13T07:30:00"
    assert info["connected_services"]["data"]["items"][0]["user_disabling_allowed"] is False
    assert info["door"]["data"]["items"][0]["status"] == ["closed", "locked"]
    assert "private" not in str(info) and "latitude" not in str(info)
    assert info["connected_services"]["vehicle_captured"] is None
    assert info["charging_timers"]["vehicle_captured"] == stamp


def test_schema_per_job_preserves_window_location_enum_and_redacts_geography():
    fields, truncated = safe_schema_inventory({"windowHeatingStatus": [
        {"windowLocation": "front", "windowHeatingState": "off", "latitude": 50.1}]},
        all_items=True)
    validate_schema_fields(fields)
    assert not truncated
    assert any(row["path"].endswith("windowLocation") for row in fields)
    assert not any("latitude" in row["path"] for row in fields)


def test_generic_charging_does_not_authorize_unobserved_parameter_writes():
    from custom_components.audiconnect.v3.command_policy import eligible_operation
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    car.advertised_capabilities.add("charging")
    auth = SimpleNamespace(uses_auth0=True, service=SimpleNamespace(_spin=None))
    for aspect in ("set_target_soc", "set_charge_mode", "set_location_charge_target"):
        assert eligible_operation(car, auth, "charging", aspect) is None
    assert eligible_operation(car, auth, "charging", "start") == "cariad.charging.start"
    car.readings["targetstateOfCharge"] = {"value": 80}
    car.readings["availableChargeModes"] = {"value": ["manual", "timer"]}
    car.charging_profiles = [{"id": 1, "targetSOC_pct": 70}]
    for aspect in ("set_target_soc", "set_charge_mode", "set_location_charge_target"):
        assert eligible_operation(car, auth, "charging", aspect) is not None
