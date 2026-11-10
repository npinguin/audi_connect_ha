"""User-visible Q8 climate controls: bodyless start and stop, not diagnostics only."""
from __future__ import annotations
import asyncio
from types import SimpleNamespace as NS
import pytest
from homeassistant.exceptions import HomeAssistantError
from custom_components.audiconnect.button import AudiButton, BUTTON_DESCRIPTIONS

VIN = "WAUZZZ00000000000"
buttons = {button.key: button for button in BUTTON_DESCRIPTIONS}


def vehicle(*, auth0=True):
    return NS(
        vin=VIN, climatisation_state="off",
        _audi_service=NS(uses_auth0=auth0),
        has_capability=lambda cap: cap == "climatisation",
    )


class Connection:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    async def start_climate_control(self, vin):
        self.calls.append(("start", vin))
        return self.result

    async def set_vehicle_climatisation(self, vin, active):
        self.calls.append(("stop", vin, active))
        return self.result


class Coordinator:
    last_update_success = True
    def __init__(self, connection):
        self.account = NS(connection=connection)
        self.refreshes = 0
    async def async_request_refresh(self):
        self.refreshes += 1


@pytest.mark.parametrize("key", ["start_climate_car_settings", "stop_climate"])
def test_new_controls_are_gated_to_supported_auth0_climatisation(key):
    assert buttons[key].supported_fn(vehicle(auth0=True))
    assert not buttons[key].supported_fn(vehicle(auth0=False))


@pytest.mark.parametrize(("key", "expected"), [
    ("start_climate_car_settings", ("start", VIN)),
    ("stop_climate", ("stop", VIN, False)),
])
def test_climate_buttons_actually_call_vehicle_and_refresh(key, expected):
    connection = Connection()
    coordinator = Coordinator(connection)
    button = AudiButton(coordinator, buttons[key], vehicle())
    asyncio.run(button.async_press())
    assert connection.calls == [expected]
    assert coordinator.refreshes == 1


@pytest.mark.parametrize("key", ["start_climate_car_settings", "stop_climate"])
def test_failed_climate_command_is_not_silent_or_refreshed(key):
    connection = Connection(result=False)
    coordinator = Coordinator(connection)
    button = AudiButton(coordinator, buttons[key], vehicle())
    with pytest.raises(HomeAssistantError):
        asyncio.run(button.async_press())
    assert coordinator.refreshes == 0


def test_button_id_is_stable_and_distinct():
    conn = Connection()
    coord = Coordinator(conn)
    start = AudiButton(coord, buttons["start_climate_car_settings"], vehicle())
    stop = AudiButton(coord, buttons["stop_climate"], vehicle())
    assert start.unique_id.endswith("_button_start_climate_car_settings")
    assert stop.unique_id.endswith("_button_stop_climate")
    assert start.unique_id != stop.unique_id
