"""Independent, slow telemetry polling which cannot invalidate chassis power."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from collections.abc import Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import IpmiCoreClient, IpmiCoreError
from .const import DOMAIN, TELEMETRY_POLL_SECONDS
from .telemetry_models import TelemetrySnapshot

_LOGGER = logging.getLogger(__name__)


class IpmiCoreTelemetryCoordinator(DataUpdateCoordinator[TelemetrySnapshot]):
    """A separate coordinator so telemetry errors cannot erase power status."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: IpmiCoreClient,
        shared_executor: Callable[[Callable], Awaitable],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_telemetry_{entry.entry_id}",
            update_interval=timedelta(seconds=TELEMETRY_POLL_SECONDS),
            always_update=False,
        )
        self._client = client
        self._shared_executor = shared_executor

    async def _async_update_data(self) -> TelemetrySnapshot:
        try:
            return await self._shared_executor(self._client.get_telemetry)
        except (TimeoutError, IpmiCoreError) as err:
            # No backend exception details or BMC identity in diagnostics.
            raise UpdateFailed("BMC telemetry temporarily unavailable") from err
