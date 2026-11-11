"""V3 owns the HA polling coordinator, reusing the working V2 API adapter.

No second refresh task, no parallel session and no extra GET per poll.
"""
from __future__ import annotations

from typing import Any

from ..coordinator import AudiDataUpdateCoordinator
from .runtime import V3Runtime


class AudiV3Coordinator(AudiDataUpdateCoordinator):
    v3: V3Runtime | None = None

    async def _async_update_data(self) -> list[Any]:
        result = await super()._async_update_data()
        if self.v3 is not None:
            self.v3.observe(result)
        return result
