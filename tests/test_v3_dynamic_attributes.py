"""V3 read-only value discovery preserves historical entity identity."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"


def test_v3_binary_sensor_platform_is_loaded_from_v3_and_not_v2():
    main = (ROOT / "__init__.py").read_text()
    code = (ROOT / "binary_sensor.py").read_text()
    assert "loaded_platforms=list(PLATFORMS)" in main
    assert 'from .v3.ha_platforms import setup as v3_setup' in code
    assert "if isinstance(runtime_data.v3, V3Engine)" in code
    assert "V3ReadOnlyBinarySensor" in (ROOT/"v3"/"ha_platforms.py").read_text()


def test_recovered_sensor_requires_vehicle_specific_evidence():
    sensor = (ROOT / "sensor.py").read_text()
    binary = (ROOT / "binary_sensor.py").read_text()
    assert 'from .v3.ha_platforms import setup as v3_setup' in sensor
    assert 'from .v3.ha_platforms import setup as v3_setup' in binary
    platforms = (ROOT / "v3" / "ha_platforms.py").read_text()
    assert "for ident in car.readings" in platforms
    assert "projection_reading(car, descriptor)" in platforms
    # No discovery result may disable a pre-existing V2 ID. The entity can
    # remain unavailable until V3 implements that source, but its ID survives.
    visibility = (ROOT / "v3" / "registry_lifecycle.py").read_text()
    assert "recorded & owned" in visibility
    assert "registry.async_update_entity(entity_id, disabled_by=None)" in visibility
    assert "retired_pilot_entity(unique_id) or duplicate_refresh" in visibility
    # Exact migration behaviour is exercised in test_v3_entity_identity_and_categories.
