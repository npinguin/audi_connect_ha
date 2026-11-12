"""V3-owned Audi API transport and per-entry cloud request accounting.

Owns all V3 business GET/POSTs. Auth provider only supplies scoped bearer tokens.
Never execute a user-provided absolute URL or untrusted Authorization header.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import V3Auth
from .family_executors import build_family_executors
from .quota import QuotaBudget

INVENTORY_OPERATION = "graphql.inventory.vehicleList"
_GRAPHQL_QUERY = """query vehicleList {
  userVehicles {
    vin
    nickname
    vehicle { core { modelYear } media { shortName longName }
              classification { driveTrain } }
  }
}"""


# Optional OEM render discovery is deliberately separate from identity.
# Public reference: vwgroup-connect-ha/cariad/api/graphql.py (renderPictures).
_GRAPHQL_IMAGES_QUERY = """query vehicleImages {
  userVehicles {
    vin
    vehicle { renderPictures { mediaType url } }
  }
}"""


@dataclass(frozen=True)
class V3Response:
    status: int
    data: Any
    observed_at: datetime
    remaining_calls: int | None = None
    request: dict[str, Any] | None = field(default=None, repr=False, compare=False)


class V3Transport:
    """Audi region host allowlist and single-connection request budget."""

    def __init__(self, hass: Any, auth: V3Auth):
        self.auth = auth
        self.session = async_get_clientsession(hass)
        self.quota = QuotaBudget()
        self.last_cloud_poll: datetime | None = None
        self._request_lock = asyncio.Lock()
        self._request_count = 0
        self.executors = build_family_executors()
        self.last_inventory_metadata: V3Response | None = None

    @property
    def remaining_calls(self) -> int | None:
        return self.quota.remaining

    @property
    def remaining_calls_observed_at(self) -> datetime | None:
        return self.quota.observed_at

    @property
    def request_count(self) -> int:
        return self._request_count

    async def request(
        self, family: str, method: str, path: str, *,
        body: Any = None, explicit_action: bool = False,
        security_token: str | None = None,
        region_vin: str | None = None,
    ) -> V3Response:
        if family not in self.executors:
            raise ValueError("Unknown or unsupported V3 executor")
        if security_token is not None and family != "mbb":
            raise ValueError("Security token is only valid for MBB RLU")
        kwargs = {"security_token": security_token} if security_token is not None else {}
        if region_vin is not None:
            if family != "mbb":
                raise ValueError("Region VIN is only valid for MBB")
            kwargs["region_vin"] = region_vin
        async with self._request_lock:
            # GraphQL inventory uses POST transport but is a fixed read-only query.
            read_only = method == "GET" or (
                family == "graphql" and method == "POST"
                and path == "/vgql/v1/graphql"
                and body in ({"query": _GRAPHQL_QUERY}, {"query": _GRAPHQL_IMAGES_QUERY})
            )
            self.quota.authorize(datetime.now(UTC), read_only=read_only)
            await self.auth.ensure_ready()
            plan = self.executors[family].plan(
                self.auth, method, path, body, explicit_action=explicit_action, **kwargs
            )
            async with asyncio.timeout(25):
                async with self.session.request(
                    plan.method, plan.url,
                    headers=plan.headers,
                    json=plan.body if plan.body is not None else None,
                    allow_redirects=False,
                ) as response:
                    self._request_count += 1
                    self.quota.observe(response.status, response.headers, datetime.now(UTC))
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
                        request={"method": plan.method, "url": plan.url, "body": plan.body},
                    )

    async def discover_vehicles(self) -> list[dict[str, Any]]:
        self.last_inventory_metadata = None
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
        # Only request metadata is retained here, not an account-wide raw response.
        self.last_inventory_metadata = replace(response, data=None)
        return [car for car in vehicles if isinstance(car, dict)]


    async def discover_vehicle_images(self) -> dict[str, str]:
        """One optional fixed read query; no token exchange or fallback login."""
        response = await self.request(
            "graphql", "POST", "/vgql/v1/graphql",
            body={"query": _GRAPHQL_IMAGES_QUERY}, explicit_action=True,
        )
        if not 200 <= response.status < 300 or not isinstance(response.data, dict):
            raise RuntimeError("Audi vehicle render query unavailable")
        data = response.data.get("data")
        rows = data.get("userVehicles") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise RuntimeError("Audi vehicle render list unavailable")
        from .vehicle import select_vehicle_image
        result = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            vin = row.get("vin")
            if not isinstance(vin, str) or len(vin) != 17 or not vin.isalnum():
                continue
            vehicle = row.get("vehicle")
            url = select_vehicle_image(vehicle, vin)
            if url:
                result[vin.lower()] = url
        return result
