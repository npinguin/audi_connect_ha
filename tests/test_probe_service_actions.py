"""HA service UI regression: one-click probes and readable invalid-mode errors."""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.audiconnect.const import DOMAIN

integration = importlib.import_module("custom_components.audiconnect")


class FakeServiceRegistry:
    def __init__(self):
        self.handlers = {}
        self.removed = []

    def has_service(self, domain, service):
        return (domain, service) in self.handlers

    def async_register(self, domain, service, callback, **kwargs):
        self.handlers[(domain, service)] = (callback, kwargs.get("schema"))

    def async_remove(self, domain, service):
        self.removed.append((domain, service))
        self.handlers.pop((domain, service), None)


class FakeConnection:
    def __init__(self):
        self.calls = []

    async def probe_read_only_api(self, vin, **kwargs):
        if kwargs["restore_group"] != "trips" and not kwargs["restore"]:
            raise ValueError("Restore group requires restore=true")
        self.calls.append((vin, kwargs))
        return {"attempted": 3, "mode": "restore"}


def make_hass(monkeypatch):
    connection = FakeConnection()
    account = SimpleNamespace(connection=connection)
    hass = SimpleNamespace(services=FakeServiceRegistry())
    monkeypatch.setattr(
        integration, "_resolve_service_call", lambda hass, call: ("VIN", account)
    )
    integration._async_register_services(hass)
    return hass, connection


def call_action(hass, name, data=None):
    callback, schema = hass.services.handlers[(DOMAIN, name)]
    values = schema({"device_id": "fake-device", **(data or {})}) if schema else data
    return asyncio.run(callback(SimpleNamespace(data=values or {})))


@pytest.mark.parametrize(
    ("action", "group"),
    [
        ("probe_vehicle_health", "vehicle_health"),
        ("probe_trip_data", "trips"),
    ],
)
def test_dedicated_probe_requires_only_device_id(monkeypatch, action, group):
    hass, connection = make_hass(monkeypatch)
    call_action(hass, action)
    assert connection.calls == [(
        "VIN",
        {
            "extended": False,
            "restore": True,
            "restore_group": group,
        },
    )]


def test_dedicated_probes_do_not_use_backend_when_device_is_missing(monkeypatch):
    hass, connection = make_hass(monkeypatch)
    monkeypatch.setattr(integration, "_resolve_service_call", lambda *args: None)
    with pytest.raises(HomeAssistantError, match="device or account"):
        call_action(hass, "probe_vehicle_health")
    assert connection.calls == []


def test_legacy_invalid_combo_is_explained_instead_of_unknown_error(monkeypatch):
    hass, connection = make_hass(monkeypatch)
    with pytest.raises(HomeAssistantError, match="Restore group requires restore=true"):
        call_action(
            hass,
            "probe_api_paths",
            {"restore": False, "restore_group": "vehicle_health"},
        )
    assert connection.calls == []


def test_legacy_core_probe_remains_backward_compatible(monkeypatch):
    hass, connection = make_hass(monkeypatch)
    call_action(hass, "probe_api_paths")
    assert connection.calls[0][1] == {
        "extended": False,
        "restore": False,
        "restore_group": "trips",
    }


def test_legacy_valid_vehicle_health_selection_is_unchanged(monkeypatch):
    hass, connection = make_hass(monkeypatch)
    call_action(
        hass,
        "probe_api_paths",
        {"restore": True, "restore_group": "vehicle_health"},
    )
    assert connection.calls[0][1]["restore"] is True
    assert connection.calls[0][1]["restore_group"] == "vehicle_health"


def test_service_unload_unregisters_new_actions(monkeypatch):
    hass, _connection = make_hass(monkeypatch)

    class ConfigEntries:
        async def async_unload_platforms(self, *_):
            return True

        def async_entries(self, *_):
            return [object()]

    hass.config_entries = ConfigEntries()
    entry = SimpleNamespace()
    assert asyncio.run(integration.async_unload_entry(hass, entry))
    for service in (
        "probe_api_paths", "probe_vehicle_health", "probe_trip_data",
        "refresh_trip_data",
    ):
        assert not hass.services.has_service(DOMAIN, service)
