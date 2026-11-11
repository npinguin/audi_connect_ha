"""V3 dynamically restores V2 entity unique IDs, not unknown or user-disabled keys."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"audiconnect"

def test_v3_binary_sensor_platform_is_loaded_from_v3_and_not_v2():
    main=(ROOT/"__init__.py").read_text()
    code=(ROOT/"binary_sensor.py").read_text()
    assert "Platform.BINARY_SENSOR" in main
    assert "V3ReadOnlyBinarySensor" in code
    assert "if isinstance(runtime_data.v3, V3Engine)" in code

def test_recovered_sensor_is_based_on_vehicle_specific_evidence():
    code=(ROOT/"sensor.py").read_text()
    assert "profile.attribute_routes" in code
    assert "key not in vehicle.readings" in (ROOT/"binary_sensor.py").read_text()
    visibility=(ROOT/"v3/registry_lifecycle.py").read_text()
    assert "entity.unique_id in active_ids" in visibility
