"""V3 control availability uses verified vehicle capability, not registry hiding."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "audiconnect"


def test_controls_are_created_only_after_independent_v3_verification():
    platforms = (ROOT / "v3" / "ha_platforms.py").read_text()
    assert "engine.control_enabled(" in platforms
    assert '"start")' in platforms and '"stop")' in platforms
    assert '"lock", "access")' in platforms
    assert '"unlock", "access")' in platforms
    # The V2 modules are merely entrypoint selectors, not V3 implementers.
    for domain in ("button", "switch", "lock"):
        source = (ROOT / f"{domain}.py").read_text()
        assert 'from .v3.ha_platforms import setup as v3_setup' in source


def test_registry_never_hides_v2_entities_to_gate_v3_controls():
    src = (ROOT / "v3" / "registry_lifecycle.py").read_text()
    assert "async_entries_for_config_entry" in src
    assert "RegistryEntryDisabler.INTEGRATION" in src  # restore only
    assert "registry.async_update_entity(entity_id, disabled_by=None)" in src
    assert "disabled_by=er.RegistryEntryDisabler.INTEGRATION" not in src
