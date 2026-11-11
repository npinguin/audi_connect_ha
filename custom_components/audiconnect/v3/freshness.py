"""Vehicle capture timestamps must be recent, not merely present."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def timestamp_is_fresh(
    captured: Any, observed_at: datetime, *, max_age_minutes: int = 60,
) -> bool:
    """Do not mistake cached 4-hour-old vehicle state for a current reading.

    Allow a 5-minute car/cloud clock skew into the future. A cloud HTTP
    response timestamp is not a substitute for a vehicle capture timestamp.
    """
    if not isinstance(captured, str) or observed_at.tzinfo is None:
        return False
    try:
        stamp = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        return False
    diff = (
        observed_at.astimezone(UTC) - stamp.astimezone(UTC)
    ).total_seconds()
    return -300 <= diff <= max_age_minutes * 60
