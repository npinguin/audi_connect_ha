"""V3 control availability uses verified vehicle capability, not registry hiding."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"


def test_controls_are_created_only_after_independent_v3_verification():
    button = (ROOT / "button.py").read_text()
    switch = (ROOT / "switch.py").read_text()
    lock = (ROOT / "lock.py").read_text()
    assert "engine.control_enabled(vehicle.vin, action, capability)" in button
    assert 'engine.control_enabled(vehicle.vin, "start")' in switch
    assert 'engine.control_enabled(vehicle.vin, "stop")' in switch
    assert 'engine.control_enabled(vehicle.vin, "lock", "access")' in lock
    assert 'engine.control_enabled(vehicle.vin, "unlock", "access")' in lock


def test_registry_never_hides_v2_entities_to_gate_v3_controls():
    src = (ROOT / "v3" / "registry_lifecycle.py").read_text()
    assert "async_entries_for_config_entry" in src
    assert "RegistryEntryDisabler.INTEGRATION" in src  # restore only
    assert "registry.async_update_entity(entity_id, disabled_by=None)" in src
    assert "disabled_by=er.RegistryEntryDisabler.INTEGRATION" not in src
