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
