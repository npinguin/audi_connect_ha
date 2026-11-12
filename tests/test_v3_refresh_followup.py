"""Refresh lifecycle is independent of the background poll and uses one journal."""
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import time

import pytest

from custom_components.audiconnect.v3.command_journal import CommandRecord
from custom_components.audiconnect.v3.registry import CapabilityRegistry
from custom_components.audiconnect.v3.engine import V3Engine
from custom_components.audiconnect.v3.development_profiles import DevelopmentProfile
from custom_components.audiconnect.v3.vehicle import V3Vehicle
from custom_components.audiconnect.v3.transport import V3Response
from custom_components.audiconnect.const import CONF_REFRESH_AFTER_ACTION, CONF_UPDATE_SLEEP

VIN = "WAUZZZ4M0MD123456"
ROOT = Path(__file__).resolve().parents[1] / "custom_components/audiconnect/v3"


def fixture(opt_in=False):
    registry = CapabilityRegistry.from_json_file(ROOT / "full_catalog.json")
    vehicle = V3Vehicle(VIN, "Audi", "Audi Q8", "q8", "DE", car_type="phev")
    vehicle.advertised_capabilities.update({"climatisation", "vehicleWakeUp"})
    events = []
    coordinator = NS(async_request_refresh=AsyncMock())
    entry = NS(entry_id="test", options={CONF_UPDATE_SLEEP: 0, CONF_REFRESH_AFTER_ACTION: opt_in},
               runtime_data=NS(coordinator=coordinator))
    async def request(family, method, path, **kwargs):
        if method == "POST":
            rid = "refresh-id" if path.endswith("vehiclewakeup") else "climate-id"
            return V3Response(200, {"data":{"requestID":rid}}, datetime.now(UTC), 50)
        return V3Response(200, {"data":[{"id":"climate-id","status":"successful"},
                                        {"id":"refresh-id","status":"successful"}]}, datetime.now(UTC), 49)
    transport = NS(request=AsyncMock(side_effect=request), remaining_calls=50)
    engine = V3Engine(NS(bus=NS(async_fire=lambda event, data: events.append((event,data)))),
                      entry, registry, auth=NS(uses_auth0=True, service=NS()),
                      transport=transport, storage=NS(async_save=AsyncMock()))
    engine.vehicles[VIN.lower()] = vehicle
    engine.profiles[VIN.lower()] = DevelopmentProfile(registry, vehicle.context)
    return engine, transport, coordinator, events


@pytest.mark.asyncio
@pytest.mark.parametrize("opt_in", [False, True])
async def test_completed_climate_has_one_cloud_followup_and_optional_linked_wake(opt_in):
    engine, transport, coordinator, events = fixture(opt_in)
    await engine.send_control(VIN, "start", "climate")
    posts = [c.args[2] for c in transport.request.await_args_list if c.args[1] == "POST"]
    assert len(posts) == (2 if opt_in else 1)
    assert posts[0].endswith("climatisation/start")
    coordinator.async_request_refresh.assert_awaited_once()
    history = engine.profiles[VIN.lower()].command_journal
    if opt_in:
        assert posts[1].endswith("vehiclewakeup")
        assert history[-1].parent_command_id == history[0].command_id
        assert history[-1].state == "backend_completed"
        assert events == [("audiconnect_refresh_completed", {"vin": "*"*13 + VIN[-4:], "outcome": "backend_completed"})]
    else:
        assert events == []
        assert len(history) == 1


@pytest.mark.asyncio
async def test_refresh_is_not_repeated_and_uncertainty_never_creates_followup():
    engine, transport, coordinator, events = fixture(True)
    await engine.send_control(VIN, "refresh", "remote")
    posts = [c for c in transport.request.await_args_list if c.args[1] == "POST"]
    assert len(posts) == 1
    coordinator.async_request_refresh.assert_awaited_once()
    engine, transport, coordinator, events = fixture(True)
    transport.request.side_effect = None
    transport.request.return_value = V3Response(200, {}, datetime.now(UTC), 50)
    await engine.send_control(VIN, "start", "climate")
    assert transport.request.await_count == 1
    assert events == []
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_unrelated_parent_cannot_bypass_cooldown_or_trigger_refresh():
    engine, transport, coordinator, events = fixture(True)
    p = engine.profiles[VIN.lower()]
    parent = CommandRecord.begin("climate", "start", "cariad.climate.start.stored", time.time())
    parent.state = "backend_completed"
    p.track_command(parent)
    with pytest.raises(RuntimeError, match="parent command"):
        await engine.commands.send_control(VIN, "refresh", "remote", _follow_up_to="wrong")
    transport.request.assert_not_awaited()
