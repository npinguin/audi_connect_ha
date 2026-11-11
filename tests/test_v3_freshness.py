"""V3 cached data must not be promoted to live Climate capability."""

from datetime import UTC, datetime, timedelta
from custom_components.audiconnect.v3.freshness import timestamp_is_fresh


def test_four_hour_old_capture_is_not_fresh():
    now = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
    assert not timestamp_is_fresh((now - timedelta(minutes=257)).isoformat(), now)
    assert timestamp_is_fresh((now - timedelta(minutes=15)).isoformat(), now)


def test_no_or_invalid_timestamp_cannot_confirm_state():
    now = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
    assert not timestamp_is_fresh(None, now)
    assert not timestamp_is_fresh("yesterday", now)
    assert not timestamp_is_fresh("2026-11-11T15:00:00", now)
    assert not timestamp_is_fresh((now + timedelta(minutes=6)).isoformat(), now)
