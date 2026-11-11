"""Manual wake is explicitly user driven and bounded by battery/API budgets."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace as NS

from custom_components.audiconnect import audi_connect_account as module
from custom_components.audiconnect.audi_connect_account import AudiConnectAccount

VIN = "TESTVIN00000000001"


class Service:
    uses_auth0 = True

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def trigger_vehicle_wakeup(self, vin):
        self.calls.append(vin)
        if self.fail:
            raise RuntimeError("synthetic refusal")


def make_account(*, calls_remaining=50, fail=False):
    account = object.__new__(AudiConnectAccount)
    account._loggedin = True
    account._vehicles = [NS(vin=VIN)]
    account._audi_service = Service(fail=fail)
    account._api = NS(vcf_remaining_calls=calls_remaining)
    account._manual_wake_attempted = {}
    account._manual_wake_reports = {}
    account._manual_wake_lock = asyncio.Lock()
    return account


def test_wake_ack_is_unconfirmed_and_repeat_press_blocked(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(module, "time", NS(monotonic=lambda: clock[0]))
    account = make_account()
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is True
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert account._audi_service.calls == [VIN]
    report = account.get_manual_wake_report(VIN)
    assert report["outcome"] == "cooldown_blocked"
    assert report["retry_after_seconds"] == 1800
    assert report["physical_vehicle_wake_verified"] is False
    assert VIN not in repr(report)
    clock[0] += 1801
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is True
    assert len(account._audi_service.calls) == 2


def test_daily_budget_blocks_fifth_wake(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(module, "time", NS(monotonic=lambda: clock[0]))
    account = make_account()
    for _ in range(4):
        assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is True
        clock[0] += 1801
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert len(account._audi_service.calls) == 4
    assert account.get_manual_wake_report(VIN)["outcome"] == "daily_budget_blocked"


def test_known_low_api_quota_blocks_wake():
    account = make_account(calls_remaining=12)
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert account.get_manual_wake_report(VIN)["outcome"] == "api_budget_blocked"
    assert account._audi_service.calls == []


def test_failed_wake_consumes_cooldown(monkeypatch):
    monkeypatch.setattr(module, "time", NS(monotonic=lambda: 1000.0))
    account = make_account(fail=True)
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert len(account._audi_service.calls) == 1


def test_unknown_vehicle_never_receives_wake():
    account = make_account()
    assert asyncio.run(account.trigger_vehicle_wakeup("UNKNOWN")) is False
    assert account._audi_service.calls == []


def test_legacy_session_never_receives_modern_wake():
    account = make_account()
    account._audi_service.uses_auth0 = False
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is False
    assert account._audi_service.calls == []


def test_attempt_budget_rolls_off_after_24_hours(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(module, "time", NS(monotonic=lambda: clock[0]))
    account = make_account()
    for _ in range(4):
        assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is True
        clock[0] += 1801
    clock[0] += 86401
    assert asyncio.run(account.trigger_vehicle_wakeup(VIN)) is True
    assert account.get_manual_wake_report(VIN)["attempts_24h"] == 1
