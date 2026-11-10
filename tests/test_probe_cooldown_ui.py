"""Cooldown is explicit to callers and cannot launch another Audi API burst."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from custom_components.audiconnect.audi_connect_account import AudiConnectAccount

VIN = "SYNTHETICVIN000001"


class FakeService:
    def __init__(self):
        self.calls = 0

    async def probe_known_read_only_paths(self, vin, *, extended, restore, restore_group="trips"):
        self.calls += 1
        return {
            "mode": "restore" if restore else "extended" if extended else "core",
            "attempted": 0,
            "restore_group": restore_group,
            "results": [],
        }


def account_with_previous_core_probe(seconds_ago=360):
    account = object.__new__(AudiConnectAccount)
    account._loggedin = True
    account._vehicles = [SimpleNamespace(vin=VIN)]
    account._readonly_probe_attempted = {VIN.lower(): time.monotonic() - seconds_ago}
    account._readonly_probe_reports = {
        VIN.lower(): {"mode": "core", "attempted": 8, "results": []}
    }
    account._readonly_probe_lock = asyncio.Lock()
    account._audi_service = FakeService()
    return account


def test_different_mode_during_cooldown_reports_minutes_not_unknown_error():
    account = account_with_previous_core_probe()
    with pytest.raises(RuntimeError, match=r"Try again in 9 minute"):
        asyncio.run(account.probe_read_only_api(VIN, restore=True))
    assert account._audi_service.calls == 0
    assert account._readonly_probe_reports[VIN.lower()]["mode"] == "core"


def test_repeat_same_mode_reuses_report_without_api_requests():
    account = account_with_previous_core_probe()
    result = asyncio.run(account.probe_read_only_api(VIN))
    assert result["mode"] == "core"
    assert result["attempted"] == 8
    assert account._audi_service.calls == 0


def test_different_mode_after_fifteen_minutes_is_allowed():
    account = account_with_previous_core_probe(seconds_ago=901)
    result = asyncio.run(account.probe_read_only_api(VIN, restore=True))
    assert result["mode"] == "restore"
    assert account._audi_service.calls == 1


def test_restore_group_change_uses_shared_cooldown():
    account = account_with_previous_core_probe(seconds_ago=901)
    asyncio.run(
        account.probe_read_only_api(VIN, restore=True, restore_group="trips")
    )
    with pytest.raises(RuntimeError, match="cooldown active"):
        asyncio.run(
            account.probe_read_only_api(
                VIN, restore=True, restore_group="vehicle_health"
            )
        )
    assert account._audi_service.calls == 1


def test_repeat_same_restore_group_uses_cached_results():
    account = account_with_previous_core_probe(seconds_ago=901)
    first = asyncio.run(
        account.probe_read_only_api(
            VIN, restore=True, restore_group="vehicle_health"
        )
    )
    second = asyncio.run(
        account.probe_read_only_api(
            VIN, restore=True, restore_group="vehicle_health"
        )
    )
    assert first == second
    assert account._audi_service.calls == 1
