"""Shared V3 status polling recovers source-derived V2 fields without guesses."""
from __future__ import annotations
from datetime import UTC, datetime, timedelta
from custom_components.audiconnect.v3.attribute_runtime import observe_read_only, planned_jobs
from custom_components.audiconnect.v3.vehicle import V3Vehicle

class Profile:
    attribute_routes = None
    attribute_evidence = None
    def __init__(self):
        self.attribute_routes, self.attribute_evidence = {}, {}

def car():
    return V3Vehicle(vin="TESTVIN0000000001", name="Audi", model="Q8", model_family="q8", country="DE")

def test_single_selectivestatus_response_recovers_multiple_fields():
    car1,p,now=car(),Profile(),datetime.now(UTC)
    assert len(planned_jobs(car1,p)) >= 23
    sample={"charging":{"batteryStatus":{"value":{"currentSOC_pct":55,"carCapturedTimestamp":now.isoformat()}},"chargingStatus":{"value":{"chargingState":"charging","carCapturedTimestamp":now.isoformat()}}},"climatisation":{"climatisationStatus":{"value":{"climatisationState":"off","carCapturedTimestamp":now.isoformat()}}}}
    outcome=observe_read_only(car1,p,sample,now)
    assert outcome["fresh"] >= 3
    assert all(name in p.attribute_routes for name in ("stateOfCharge","chargingState","climatisationState"))
    assert set(planned_jobs(car1,p)) >= {"charging","climatisation","userCapabilities"}
    assert "tripStatistics" not in planned_jobs(car1,p)

def test_unknown_and_stale_values_are_not_promoted():
    car1,p,now=car(),Profile(),datetime.now(UTC)
    old=(now-timedelta(hours=3)).isoformat()
    observe_read_only(car1,p,{"charging":{"batteryStatus":{"value":{"currentSOC_pct":0,"carCapturedTimestamp":old}}}},now)
    assert car1.readings["stateOfCharge"]["status"] == "readable_but_stale"
    assert "stateOfCharge" not in p.attribute_routes
    assert "charging" in planned_jobs(car1,p)  # mapped stale field still refreshes
    assert "plugState" not in car1.readings

def test_capability_advertisement_is_not_fresh_attribute_evidence():
    car1,p,now=car(),Profile(),datetime.now(UTC)
    observe_read_only(car1,p,{"userCapabilities":{"capabilitiesStatus":{"value":[{"id":"charging","status":None},{"id":"onlineLogBook","status":"impaired"}]}}},now)
    assert car1.advertised_capabilities == {"charging","onlineLogBook"}
    assert car1.impaired_capabilities == {"onlineLogBook"}
    assert not p.attribute_routes
