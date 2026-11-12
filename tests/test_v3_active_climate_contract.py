"""Active clean-runtime replacements for retired pilot architecture checks."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as NS

from custom_components.audiconnect.v3.entities import V3ClimateEntity
from custom_components.audiconnect.v3.runtime import V3_DEFAULT, V3_ENABLED
from custom_components.audiconnect.v3.vehicle import V3Vehicle
from custom_components.audiconnect.v3.coordinator_clean import V3CleanCoordinator
from custom_components.audiconnect.coordinator import AudiDataUpdateCoordinator

VIN = "WAUZZZ4M0MD123456"


def test_clean_runtime_preserves_option_and_identity():
    assert V3_DEFAULT == "v2" and V3_ENABLED == "v3_climate"
    assert not issubclass(V3CleanCoordinator, AudiDataUpdateCoordinator)
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    coordinator = NS(engine=NS(control_enabled=lambda *args: False))
    entity = V3ClimateEntity(coordinator, car)
    assert entity.unique_id == VIN.lower() + "_climate_climatisation"
    assert entity.hvac_mode is None


def test_stale_climate_readback_is_never_reported_as_current():
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    coordinator = NS(engine=NS(control_enabled=lambda *args: False))
    entity = V3ClimateEntity(coordinator, car)
    now = datetime.now(UTC)
    car.set_climate("off", (now - timedelta(hours=2)).isoformat(),
                    route="test", observed_at=now, http_status=200)
    assert entity.hvac_mode is None
    car.set_climate("heating", now.isoformat(), route="test",
                    observed_at=now, http_status=200)
    assert entity.hvac_mode is not None
    assert entity.hvac_mode.value == "heat_cool"


def test_trusted_manufacturer_context_not_nickname():
    car = V3Vehicle.from_graphql({"vin": VIN, "nickname": "Audi Q8",
                                 "vehicle": {"media": {"longName": "Audi A4"}}}, "DE")
    assert car.model_family == ""
    car = V3Vehicle.from_graphql({"vin": VIN, "nickname": "other",
                                 "vehicle": {"media": {"longName": "Audi Q8"}}}, "DE")
    assert car.model_family == "q8"

def test_climate_buttons_are_independent_of_stale_state_and_use_existing_ids():
    import asyncio
    from custom_components.audiconnect.v3.ha_platforms import setup
    car = V3Vehicle(VIN, "Audi", "Q8", "q8", "DE")
    now = datetime.now(UTC)
    car.set_climate("off", (now-timedelta(hours=2)).isoformat(),
                    route="test", observed_at=now, http_status=200)
    enabled = {"start", "stop"}
    calls, offered, listeners = [], [], []
    async def send(vin, action, capability):
        calls.append((vin, action, capability))
    engine = NS(vehicles={VIN.lower():car}, profiles={},
                control_enabled=lambda vin, action, capability="climate": capability=="climate" and action in enabled,
                send_control=send)
    coordinator = NS(engine=engine,last_update_success=True,
                     async_add_listener=lambda cb: listeners.append(cb))
    entry = NS(entry_id="entry",runtime_data=NS(v3=engine,coordinator=coordinator),
               async_on_unload=lambda cb:None)
    setup("button",entry,offered.extend)
    buttons = {e.unique_id:e for e in offered}
    for suffix, action in (("start_climate_car_settings","start"),("stop_climate","stop")):
        entity=buttons[VIN.lower()+"_button_"+suffix]
        assert entity.available and entity.entity_category is None
        entity.async_write_ha_state=lambda:None
        asyncio.run(entity.async_press())
        assert calls[-1]==(VIN,action,"climate")
    assert V3ClimateEntity(coordinator,car).hvac_mode is None
    enabled.remove("start")
    assert not buttons[VIN.lower()+"_button_start_climate_car_settings"].available
    assert buttons[VIN.lower()+"_button_stop_climate"].available
