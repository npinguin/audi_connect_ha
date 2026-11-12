"""Manufacturer model and powertrain are different evidence, never nickname guesses."""
from datetime import UTC, datetime
from types import SimpleNamespace as NS
import pytest
from custom_components.audiconnect.v3.vehicle import V3Vehicle, powertrain_identity, normalize_powertrain
from custom_components.audiconnect.v3.trips import observe_cariad_trip
from custom_components.audiconnect.v3.derived_values import observe_derived
from custom_components.audiconnect.v3.attribute_runtime import _accept_observation
from custom_components.audiconnect.v3.entities import V3ReadOnlySensor
from custom_components.audiconnect.v3.historical_catalog import ATTRIBUTES
from custom_components.audiconnect.v3.ha_platforms import setup

VIN="WAUZZZ4M0MD123456"

@pytest.mark.parametrize("raw,expected",[("PHEV","phev"),("hybrid","hybrid"),("BEV","electric"),
    ("gasoline","combustion"),("diesel","combustion"),("invalid",None),(True,None),("Q8",None)])
def test_explicit_powertrain_enums(raw,expected):
    assert normalize_powertrain(raw)==expected

def test_trip_and_measurements_classify_without_inventing_a_model():
    car=V3Vehicle.from_graphql({"vin":VIN,"nickname":"Q8","vehicle":{"media":None}},"DE")
    now=datetime.now(UTC)
    observe_cariad_trip(car,"cariad.mobility.status.lastTrip",{"data":{"tripEndTimestamp":now.isoformat(),
        "vehicleType":"hybrid","tripType":"shortTerm","mileage_km":16}})
    assert car.model=="" and car.model_family==""
    assert powertrain_identity(car)=={"value":"hybrid","sources":{"last_trip":"hybrid"},"conflict":False}
    observe_derived(car,NS(),{"measurements":{"fuelLevelStatus":{"value":{
        "carCapturedTimestamp":now.isoformat(),"carType":"hybrid",
        "primaryEngineType":"gasoline","secondaryEngineType":"electric"}}}},now,_accept_observation)
    identity=powertrain_identity(car)
    assert identity["sources"]["fuel_level_status"]=="hybrid"
    assert identity["sources"]["engine_roles"]=="hybrid"
    assert car.readings["primary_engine_type"]["value"]=="gasoline"
    assert car.readings["secondary_engine_type"]["value"]=="electric"
    offered=[]
    engine=NS(vehicles={VIN.lower():car},profiles={})
    co=NS(engine=engine,async_add_listener=lambda cb:None)
    entry=NS(entry_id="entry",runtime_data=NS(v3=engine,coordinator=co),async_on_unload=lambda cb:None)
    setup("sensor",entry,offered.extend)
    matches=[e for e in offered if e.unique_id==VIN.lower()+"_sensor_car_type"]
    assert len(matches)==1 and matches[0].native_value=="hybrid" and matches[0].available

def test_specific_inventory_phev_is_consistent_with_generic_hybrid_and_conflict_is_unknown():
    car=V3Vehicle(VIN,"Audi","Audi Q8","q8","DE",car_type="phev")
    car.readings["carType"]={"value":"hybrid","status":"verified"}
    assert powertrain_identity(car)["value"]=="phev"
    car.readings["carType"]["value"]="electric"
    assert powertrain_identity(car)["conflict"]
    assert powertrain_identity(car)["value"] is None
    sensor=V3ReadOnlySensor(NS(async_add_listener=lambda cb:None),car,ATTRIBUTES["carType"])
    assert sensor.native_value is None and not sensor.available


def test_incomplete_identity_retries_are_bounded_and_quota_aware():
    from types import SimpleNamespace
    from custom_components.audiconnect.v3.status_engine import identity_retry_due
    incomplete = SimpleNamespace(inventory_present=True, model="", model_family="",
                                 model_year="2024", car_type="phev")
    complete = SimpleNamespace(inventory_present=True, model="Q8 TFSI e",
                               model_family="q8", model_year="2024", car_type="phev")
    vehicles = {"a": incomplete, "b": complete}
    assert [cycle for cycle in range(1, 24) if identity_retry_due(vehicles, cycle, 50)] == [2, 4, 8]
    assert not identity_retry_due(vehicles, 2, 12)
    assert identity_retry_due(vehicles, 2, None)
    incomplete.inventory_present = False
    assert not identity_retry_due(vehicles, 2, 50)
