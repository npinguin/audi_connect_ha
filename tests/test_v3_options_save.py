"""A runtime mode selection must be saved without losing V2 settings."""

import pytest
from types import SimpleNamespace

from custom_components.audiconnect.config_flow import OptionsFlowHandler


@pytest.mark.asyncio
async def test_switch_v2_to_v3_saves_mode_and_preserves_legacy_options():
    flow = OptionsFlowHandler()
    flow.handler = "test-audi-entry"
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _id: flow._test_entry
        )
    )
    flow._test_entry = SimpleNamespace(
        data={"scan_interval": 15},
        options={
            "runtime_version": "v2",
            "scan_interval": 15,
            "climate_quick_start": True,
            "experimental_commands": True,
            "local_dealers": {"EXAMPLE": {"name": "Dealer"}},
        },
    )
    result = await flow.async_step_init({
        "runtime_version": "v3_climate",
        "scan_interval": 15,
        "scan_initial": True,
    })
    assert result["type"] == "create_entry"
    saved = result["data"]
    assert saved["runtime_version"] == "v3_climate"
    assert saved["v3_development_workbench"] is False
    assert saved["climate_quick_start"] is True
    assert saved["experimental_commands"] is True
    assert "local_dealers" in saved


@pytest.mark.asyncio
async def test_switch_back_to_v2_preserves_legacy_configuration():
    flow = OptionsFlowHandler()
    flow.handler = "test-audi-entry"
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _id: flow._test_entry
        )
    )
    flow._test_entry = SimpleNamespace(
        data={"scan_interval": 15},
        options={
            "runtime_version": "v3_climate",
            "v3_development_workbench": True,
            "climate_quick_start": True,
            "scan_interval": 15,
        },
    )
    result = await flow.async_step_init({
        "runtime_version": "v2",
        "scan_interval": 15,
    })
    assert result["type"] == "create_entry"
    saved = result["data"]
    assert saved["runtime_version"] == "v2"
    assert saved["v3_development_workbench"] is False
    assert saved["climate_quick_start"] is True


def test_form_can_render_v3_workbench_option_when_mode_is_v3():
    flow = OptionsFlowHandler()
    flow.handler = "test-audi-entry"
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _id: flow._test_entry
        )
    )
    flow._test_entry = SimpleNamespace(
        data={"scan_interval": 15}, options={"runtime_version": "v2"},
    )
    schema = flow._options_schema({
        "runtime_version": "v3_climate",
        "scan_interval": 15,
    })
    fields = [key.schema for key in schema.schema]
    assert "v3_development_workbench" in fields
    assert "climate_quick_start" not in fields
    assert "experimental_commands" not in fields
    assert "edit_local_dealer" in fields
