"""Independent API-family request executors for Audi Connect V3.

All executors consume scoped tokens from V3Auth; none creates sessions, reads
HA config entries, calls the V2 vehicle API, or chooses arbitrary remote hosts.
MBB writes remain blocked until separately proven with S-PIN and readback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

APP_VERSION = "4.31.0"
APP_AGENT = "Android/4.31.0 (Build 800341641.root project 'myaudi_android'.ext.buildTime) Android/13"
LEGACY_BASE = "https://msg.volkswagen.de"
LEGACY_REGION_HOSTS = frozenset({
    "msg.volkswagen.de",
    "mal-3a.prd.eu.dp.vwg-connect.com",
    "fal-3a.prd.eu.dp.vwg-connect.com",
    "mal-1a.prd.ece.vwg-connect.com",
})


@dataclass(frozen=True)
class RequestPlan:
    family: str
    method: str
    url: str
    headers: dict[str, str]
    body: Any = None


class FamilyExecutor(Protocol):
    family: str
    def plan(self, auth: Any, method: str, path: str, body: Any = None,
             *, explicit_action: bool = False) -> RequestPlan: ...


def _checked_path(path: str) -> str:
    if (not isinstance(path, str) or not path.startswith("/")
            or path.startswith("//") or "://" in path
            or "\\" in path or ".." in path or "#" in path
            or any(ord(c) < 32 for c in path)
            or any(token in path.lower() for token in ("%2f", "%5c", "%00", "%2e"))):
        raise ValueError("Unsafe Audi V3 relative API path")
    if urlsplit(path).netloc:
        raise ValueError("An API family cannot execute an arbitrary host")
    return urlsplit(path).path


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "X-App-Name": "myAudi", "X-App-Version": APP_VERSION,
        "User-Agent": APP_AGENT,
        "Authorization": "Bearer " + token,
    }


class CARIADExecutor:
    family = "cariad"

    def plan(self, auth: Any, method: str, path: str, body: Any = None,
             *, explicit_action: bool = False) -> RequestPlan:
        if method not in ("GET", "POST", "PUT"):
            raise ValueError("Unsupported CARIAD operation")
        if method != "GET" and not explicit_action:
            raise ValueError("CARIAD mutations need direct user intent")
        if not auth.uses_auth0:
            raise ValueError("CARIAD operation requires Auth0")
        resource = _checked_path(path)
        if resource.startswith("/vehicle/v1/trips/"):
            import re
            if (method != "GET" or body is not None or "?" in path or
                    not re.fullmatch(r"/vehicle/v1/trips/[A-Za-z0-9]{17}/(?:shortterm|longterm|shortterm/last)", resource)):
                raise ValueError("Unreviewed Audi trip route")
        elif not resource.startswith("/vehicle/v1/vehicles/"):
            raise ValueError("Path is outside the vehicle CARIAD API")
        host = "na" if auth.country == "US" else "emea"
        headers = _headers(auth.access_token(self.family))
        if method in ("POST", "PUT") and body is not None:
            headers["Content-Type"] = "application/json"
        return RequestPlan(self.family, method,
                           f"https://{host}.bff.cariad.digital" + path,
                           headers, body)


class GraphQLExecutor:
    family = "graphql"

    def plan(self, auth: Any, method: str, path: str, body: Any = None,
             *, explicit_action: bool = False) -> RequestPlan:
        if method != "POST" or _checked_path(path) != "/vgql/v1/graphql" or "?" in path:
            raise ValueError("GraphQL supports only the fixed Audi vehicle-list endpoint")
        if not isinstance(body, dict) or set(body) != {"query"} or not isinstance(body["query"], str):
            raise ValueError("Unexpected vehicle-list GraphQL request")
        host = "app-api.my.aoa.audi.com" if auth.country == "US" else "app-api.live-my.audi.com"
        headers = _headers(auth.access_token(self.family))
        headers.update({"X-User-Country": auth.country,
                        "Content-Type": "application/json; charset=utf-8"})
        return RequestPlan(self.family, method, f"https://{host}{path}", headers, body)


class MBBLegacyExecutor:
    family = "mbb"

    def __init__(self) -> None:
        self._trusted_hosts: dict[str, str] = {}

    def set_vehicle_home_region(self, vin: str, base_url: str) -> None:
        """Only Audi-verified, hard-allowlisted home-region hosts may be accepted."""
        from urllib.parse import urlsplit as split
        parts = split(base_url)
        if (parts.scheme != "https" or parts.hostname not in LEGACY_REGION_HOSTS
                or parts.username or parts.password or parts.port
                or parts.path not in ("", "/") or parts.query or parts.fragment):
            raise ValueError("Untrusted legacy MBB home region")
        if not isinstance(vin, str) or len(vin) != 17 or not vin.isalnum():
            raise ValueError("Invalid VIN for MBB host")
        self._trusted_hosts[vin.upper()] = "https://" + parts.hostname

    def plan(self, auth: Any, method: str, path: str, body: Any = None,
             *, explicit_action: bool = False) -> RequestPlan:
        if method != "GET" or body is not None:
            raise ValueError("Legacy MBB controls are not yet verified; GET only")
        if auth.uses_auth0:
            raise ValueError("Legacy MBB must not be probed on an Auth0 vehicle")
        resource = _checked_path(path)
        if not resource.startswith(("/fs-car/bs/", "/fs-car/vehicleMgmt/")) or "?" in path:
            raise ValueError("Unreviewed MBB route")
        components = resource.split("/")
        if "vehicles" not in components:
            raise ValueError("Legacy MBB route must include a vehicle")
        idx = components.index("vehicles") + 1
        if idx >= len(components) or len(components[idx]) != 17 or not components[idx].isalnum():
            raise ValueError("Invalid MBB vehicle route")
        vin = components[idx].upper()
        host = self._trusted_hosts.get(vin, LEGACY_BASE)
        headers = _headers(auth.access_token(self.family))
        headers["Accept"] = "application/json"
        return RequestPlan(self.family, method, host + path, headers)


def build_family_executors() -> dict[str, FamilyExecutor]:
    return {
        "cariad": CARIADExecutor(),
        "graphql": GraphQLExecutor(),
        "mbb": MBBLegacyExecutor(),
    }
