"""V3 beta anti-drift contracts that must match HACS and HA packaging."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDI = ROOT / "custom_components" / "audiconnect"
V3 = AUDI / "v3"


def test_beta_manifest_version_and_hacs_metadata_are_consistent():
    manifest = json.loads((AUDI / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    notes = (ROOT / "docs/V3_RELEASE_NOTES_3.0.0b3.md").read_text()
    assert manifest["domain"] == "audiconnect"  # no second config entry
    assert manifest["version"] == "3.0.0b3"
    assert "3.0.0b3" in notes
    assert hacs["homeassistant"] == "2026.7.0"
    assert "npinguin/audi_connect_ha" in manifest["documentation"]
    assert manifest["issue_tracker"].endswith("npinguin/audi_connect_ha/issues")


def test_pilot_model_has_only_climate_with_optional_aspects():
    model = json.loads((V3 / "climate.json").read_text())
    assert model["schema_version"] == 1
    assert list(model["capabilities"]) == ["climate"]
    climate = model["capabilities"]["climate"]
    assert set(climate) == {"status", "control"}
    for operation in model["operations"].values():
        assert operation["path"].startswith("/")
        assert "://" not in operation["path"]
        assert operation["method"] in ("GET", "POST")
        if operation["method"] == "POST":
            assert operation["delivery"] == "manual"


def test_runtime_selection_is_in_options_and_single_setup_owner():
    flow = (AUDI / "config_flow.py").read_text()
    init = (AUDI / "__init__.py").read_text()
    translations = json.loads((AUDI / "strings.json").read_text())
    for option in (
        "runtime_version",
        "v3_climate_start_route",
        "v3_climate_status_route",
        "v3_climate_experimental_unknown",
    ):
        assert option in flow
        assert option in translations["options"]["step"]["init"]["data"]
    assert "coordinator = V3CleanCoordinator(hass, engine, config_entry)" in init
    assert "account=None, coordinator=coordinator, v3=engine" in init
    assert "config_entry.runtime_data = AudiRuntimeData(" in init


def test_clean_capability_owner_and_in_place_entity_id():
    entry = (AUDI / "climate.py").read_text()
    modern = (V3 / "entities.py").read_text()
    engine = (V3 / "engine.py").read_text()
    assert "V3ClimateEntity(" in entry
    assert 'vehicle.vin.lower()}_climate_climatisation' in modern
    assert "def control_enabled(" in engine
    assert "async_refresh_data" not in engine
    assert "AudiAccount" not in engine


def test_no_auto_wake_and_v3_device_registry_cleanup_disabled():
    init = (AUDI / "__init__.py").read_text()
    modern = (V3 / "coordinator_clean.py").read_text()
    assert "if runtime_data.v3 is not None:" in init
    assert "class V3CleanCoordinator(DataUpdateCoordinator" in modern
    assert "AudiDataUpdateCoordinator" not in modern
    assert "trigger_vehicle_wakeup" not in modern


def test_workbench_is_opt_in_and_panel_re_registration_is_safe():
    main = (AUDI / "__init__.py").read_text()
    dashboard = (V3 / "dashboard.py").read_text()
    flow = (AUDI / "config_flow.py").read_text()
    assert 'config_entry.options.get("v3_development_workbench", False)' in main
    assert '_HANDLERS_KEY = "audiconnect_v3_dashboard_commands_registered"' in dashboard
    assert "if not hass.data.get(_HANDLERS_KEY):" in dashboard
    assert 'hass.data.pop(_READY_KEY, False)' in dashboard
    assert '"v3_development_workbench"' in flow


def test_workbench_capability_coverage_and_draft_storage_contract():
    dashboard = (V3 / "dashboard.py").read_text()
    client = (V3 / "frontend/panel.js").read_text()
    model = (V3 / "development_profiles.py").read_text()
    assert '"audiconnect/v3/status"' in dashboard
    assert '"audiconnect/v3/save_candidate"' in dashboard
    assert 'this.api("status"' in client
    assert 'this.api("save_candidate"' in client
    assert "def save_candidate(" in model
    assert '"draft_selected": dict(self.draft_selected)' in model
