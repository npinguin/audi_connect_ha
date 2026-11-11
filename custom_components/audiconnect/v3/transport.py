"""V3-owned Audi API transport and per-entry cloud request accounting.

Owns all V3 business GET/POSTs. Auth provider only supplies scoped bearer tokens.
Never execute a user-provided absolute URL or untrusted Authorization header.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import V3Auth
from .family_executors import build_family_executors

_GRAPHQL_QUERY = """query vehicleList {
  userVehicles {
    vin
    nickname
    vehicle { core { modelYear } media { shortName longName }
              classification { driveTrain } }
  }
}"""


@dataclass(frozen=True)
class V3Response:
    status: int
    data: Any
    observed_at: datetime
    remaining_calls: int | None = None


class V3Transport:
    """Audi region host allowlist and single-connection request budget."""

    def __init__(self, hass: Any, auth: V3Auth):
        self.auth = auth
        self.session = async_get_clientsession(hass)
        self.remaining_calls: int | None = None
        self.last_cloud_poll: datetime | None = None
        self._request_lock = asyncio.Lock()
        self._request_count = 0
        self.executors = build_family_executors()

    @property
    def request_count(self) -> int:
        return self._request_count

    async def request(
        self, family: str, method: str, path: str, *,
        body: Any = None, explicit_action: bool = False,
    ) -> V3Response:
        if family not in self.executors:
            raise ValueError("Unknown or unsupported V3 executor")
        await self.auth.ensure_ready()
        plan = self.executors[family].plan(
            self.auth, method, path, body, explicit_action=explicit_action
        )
        async with self._request_lock:
            if self.remaining_calls is not None and self.remaining_calls <= 8:
                raise RuntimeError("Audi request budget too low; V3 poll suspended")
            async with asyncio.timeout(25):
                async with self.session.request(
                    plan.method, plan.url,
                    headers=plan.headers,
                    json=plan.body if plan.body is not None else None,
                    allow_redirects=False,
                ) as response:
                    self._request_count += 1
                    quota = response.headers.get("Vcf-Remaining-Calls")
                    if quota is not None:
                        try:
                            self.remaining_calls = int(quota)
                        except ValueError:
                            pass
                    raw = await response.text()
                    try:
                        payload = await response.json(content_type=None) if raw.strip() else None
                    except (ValueError, TypeError):
                        payload = None
                    timestamp = datetime.now(UTC)
                    self.last_cloud_poll = timestamp
                    # 207 is partial and must not be interpreted as fully supported.
                    return V3Response(
                        status=response.status,
                        data=payload,
                        observed_at=timestamp,
                        remaining_calls=self.remaining_calls,
                    )

    async def discover_vehicles(self) -> list[dict[str, Any]]:
        response = await self.request(
            "graphql", "POST", "/vgql/v1/graphql",
            body={"query": _GRAPHQL_QUERY}, explicit_action=True,
        )
        if not 200 <= response.status < 300 or not isinstance(response.data, dict):
            raise RuntimeError("Audi vehicle discovery request failed")
        data = response.data.get("data")
        vehicles = data.get("userVehicles") if isinstance(data, dict) else None
        if not isinstance(vehicles, list):
            raise RuntimeError("Audi vehicle list unavailable (not an empty account)")
        return [car for car in vehicles if isinstance(car, dict)]
