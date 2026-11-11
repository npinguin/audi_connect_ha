"""V3 read-only value discovery preserves historical entity identity."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"


def test_v3_binary_sensor_platform_is_loaded_from_v3_and_not_v2():
    main = (ROOT / "__init__.py").read_text()
    code = (ROOT / "binary_sensor.py").read_text()
    assert "Platform.BINARY_SENSOR" in main
    assert "V3ReadOnlyBinarySensor" in code
    assert "if isinstance(runtime_data.v3, V3Engine)" in code


def test_recovered_sensor_requires_vehicle_specific_evidence():
    sensor = (ROOT / "sensor.py").read_text()
    binary = (ROOT / "binary_sensor.py").read_text()
    assert "profile.attribute_routes" in sensor
    assert "key not in vehicle.readings" in binary
    # No discovery result may disable a pre-existing V2 ID. The entity can
    # remain unavailable until V3 implements that source, but its ID survives.
    visibility = (ROOT / "v3" / "registry_lifecycle.py").read_text()
    assert "recorded & owned" in visibility
    assert "registry.async_update_entity(entity_id, disabled_by=None)" in visibility
    assert "disabled_by=er.RegistryEntryDisabler.INTEGRATION" not in visibility
