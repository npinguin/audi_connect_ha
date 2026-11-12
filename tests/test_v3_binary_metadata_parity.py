"""Compare actual V2 descriptions to the V3 HA entity projection."""
from types import SimpleNamespace

from custom_components.audiconnect.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
from custom_components.audiconnect.v3.attribute_contracts import binary_contracts
from custom_components.audiconnect.v3.entities import V3ReadOnlyBinarySensor
from custom_components.audiconnect.v3.vehicle import V3Vehicle


def test_all_v2_binary_sensor_metadata_matches_independent_v3_projection():
    car = V3Vehicle("WAUZZZ4M0MD123456", "Audi", "Q8", "q8", "DE")
    coordinator = SimpleNamespace(async_add_listener=lambda callback: None)
    assert set(binary_contracts()) == {d.key for d in BINARY_SENSOR_DESCRIPTIONS}
    for description in BINARY_SENSOR_DESCRIPTIONS:
        entity = V3ReadOnlyBinarySensor(coordinator, car,
            {"id": description.key, "entity_key": description.key, "capability": "vehicle_status"})
        assert entity.unique_id == car.vin.lower() + "_binary_sensor_" + description.key
        contract = binary_contracts()[description.key]
        assert entity.name == contract["name"]
        assert entity.device_class == description.device_class
        assert entity.entity_category is None
        assert entity.icon == contract["icon"]
