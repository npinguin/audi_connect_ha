"""Shared authentication boundary. V3 never calls legacy vehicle operations.

Only OAuth/IDK credential exchange and persistence are shared with V2.
The V3 API transport, discovery, request budget and parsing are independent.
"""
from __future__ import annotations

import time
from typing import Any
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..audi_api import AudiAPI
from ..audi_services import AudiAuthError, AudiService
from ..const import (
    CONF_API_LEVEL, CONF_PASSWORD, CONF_REFRESH_TOKEN, CONF_REGION, CONF_SPIN,
    CONF_USERNAME, DEFAULT_API_LEVEL,
)


class V3Auth:
    """Per-config-entry token owner; never poll via AudiConnectAccount."""

    def __init__(self, hass: Any, entry: Any):
        self.hass = hass
        self.entry = entry
        self.country = (entry.data.get(CONF_REGION) or "DE").upper()
        self.service = AudiService(
            AudiAPI(async_get_clientsession(hass)), self.country,
            entry.data.get(CONF_SPIN), entry.data.get(CONF_API_LEVEL, DEFAULT_API_LEVEL),
        )
        self._last_login: float | None = None

    async def ensure_ready(self) -> None:
        if self._last_login is None:
            try:
                refresh = self.entry.data.get(CONF_REFRESH_TOKEN)
                if refresh:
                    rotated = await self.service.login_with_refresh_token(refresh)
                    self._save_refresh(rotated)
                else:
                    username = self.entry.data.get(CONF_USERNAME)
                    password = self.entry.data.get(CONF_PASSWORD)
                    if not username or not password:
                        raise ConfigEntryAuthFailed("Audi login is required")
                    await self.service.login(username, password)
            except AudiAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            self._last_login = time.monotonic()
            return
        elapsed = int(time.monotonic() - self._last_login)
        try:
            refreshed = await self.service.refresh_token_if_necessary(elapsed)
        except AudiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        if refreshed:
            self._last_login = time.monotonic()
            self._save_refresh(self.service.current_refresh_token())

    def _save_refresh(self, refresh: str | None) -> None:
        if refresh and self.entry.data.get(CONF_REFRESH_TOKEN) != refresh:
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, CONF_REFRESH_TOKEN: refresh}
            )

    @property
    def uses_auth0(self) -> bool:
        return self.service.uses_auth0

    def access_token(self, family: str) -> str:
        """Only reviewed family tokens; never expose in diagnostics."""
        if family == "cariad":
            token = getattr(self.service, "_bearer_token_json", None)
        elif family == "graphql":
            token = getattr(self.service, "audiToken", None)
        elif family == "mbb":
            token = getattr(self.service, "vwToken", None)
        else:
            raise ValueError("V3 family is not enabled")
        value = token.get("access_token") if isinstance(token, dict) else None
        if not isinstance(value, str) or not value:
            raise ConfigEntryAuthFailed("Audi authentication token unavailable")
        return value
