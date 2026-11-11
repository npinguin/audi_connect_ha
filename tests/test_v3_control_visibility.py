"""V3 reviewed controls are restored by registry migration, never pre-enabled."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"custom_components/audiconnect/v3"
def test_reviewed_control_entity_ids_are_respected_in_visibility_migration():
    src=(ROOT/"registry_lifecycle.py").read_text()
    assert "engine.control_enabled(vehicle.vin, action, cap)" in src
    assert 'active_ids.add(f"{vin}_button_{button_key}")' in src
    assert 'active_ids.add(f"{vin}_switch_climate_quick_control")' in src
    assert 'active_ids.add(f"{vin}_lock_lock")' in src
    assert "if entity.unique_id in active_ids" in src
