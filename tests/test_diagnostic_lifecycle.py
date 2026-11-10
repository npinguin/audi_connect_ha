"""Diagnostics lifecycle regression: useful evidence without accumulating history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from collections import deque

from custom_components.audiconnect.audi_connect_account import (
    AudiConnectAccount,
    _active_diagnostic_report,
)
from custom_components.audiconnect.diagnostic_events import build_http_event


VIN = "SYNTHETICVIN000001"


def _dated_report(hours_ago: int) -> dict:
    stamp = datetime.now(UTC) - timedelta(hours=hours_ago)
    return {"ran_at": stamp.isoformat(), "attempted": 3, "mode": "restore"}


def test_recent_user_requested_probe_is_still_available():
    account = object.__new__(AudiConnectAccount)
    account._readonly_probe_reports = {VIN.lower(): _dated_report(2)}
    assert account.get_read_only_probe_report(VIN)["attempted"] == 3
    assert VIN.lower() in account._readonly_probe_reports


def test_expired_probe_report_is_removed_without_touching_vehicle_data():
    account = object.__new__(AudiConnectAccount)
    account._readonly_probe_reports = {VIN.lower(): _dated_report(25)}
    assert account.get_read_only_probe_report(VIN) is None
    assert not account._readonly_probe_reports


def test_modern_trip_report_expires_independently_of_probe():
    account = object.__new__(AudiConnectAccount)
    account._modern_trip_reports = {VIN.lower(): _dated_report(25)}
    account._readonly_probe_reports = {VIN.lower(): _dated_report(1)}
    assert account.get_auth0_trip_report(VIN) is None
    assert account.get_read_only_probe_report(VIN) is not None
    assert not account._modern_trip_reports


def test_bad_or_untrusted_timestamp_does_not_crash_diagnostics():
    for date in ("invalid", "2026-11-10T21:00:00", 123456):
        assert not _active_diagnostic_report({"ran_at": date})


def test_older_in_memory_report_without_timestamp_stays_until_restart():
    assert _active_diagnostic_report({"attempted": 3, "results": []})


def test_http_event_buffer_is_bounded_and_filters_successful_auth():
    events = deque(maxlen=20)
    for i in range(40):
        event = build_http_event(
            "POST",
            "https://emea.bff.cariad.digital/vehicle/v1/vehicles/PRIVATEVIN/"
            "vehiclewakeuptrigger",
            204,
        )
        if event:
            events.append(event)
    assert len(events) == 20
    assert all(e["route"] == "vehicle_wakeup_trigger" for e in events)
    assert all(e["outcome"] == "http_accepted_not_vehicle_confirmed" for e in events)
    assert build_http_event(
        "POST", "https://group.identity.vwgroup.io/oauth/token", 200
    ) is None
    assert build_http_event(
        "POST", "https://group.identity.vwgroup.io/oauth/token", 401
    )["outcome"] == "http_rejected"
