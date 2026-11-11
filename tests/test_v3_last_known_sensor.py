"""Passive V2-compatible values remain readable without pretending to be live.

Cloud receipt age cannot turn an old vehicle sample into fresh data, and
active/security binary statuses stay unavailable when their capture is old.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from custom_components.audiconnect.v3.entities import (
    V3ReadOnlySensor,
    _reading_available,
)


def test_passive_last_known_held_without_marking_live():
    captured = (datetime.now(UTC) - timedelta(hours=4)).isoformat()
    row = {
        "value": 52, "captured": captured,
        "observed": datetime.now(UTC).isoformat(),
        "family": "cariad", "status": "readable_but_stale",
    }
    assert _reading_available(row, allow_last_known=True)
    assert not _reading_available(row)  # safety-critical binary/lock consumers
    fake = SimpleNamespace(
        vehicle=SimpleNamespace(readings={"stateOfCharge": row}),
        attribute={"capability": "charging", "id": "stateOfCharge"},
    )
    attrs = V3ReadOnlySensor.extra_state_attributes.fget(fake)
    assert attrs["vehicle_freshness"] == "stale_last_known"
    assert attrs["age_minutes"] >= 240


def test_unknown_or_missing_value_is_never_exposed():
    assert not _reading_available(None, allow_last_known=True)
    assert not _reading_available({"value": None, "status": "verified"}, allow_last_known=True)
    assert not _reading_available({"value": 1, "status": "api_error"}, allow_last_known=True)
    assert _reading_available({"value": 0, "status": "readable_but_stale"}, allow_last_known=True)
