"""Single IPMI state poll shared by all entities."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import traceback

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import IpmiCoreClient, IpmiCoreError
from .const import CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS, DOMAIN, OPERATION_TIMEOUT
from .power_control import PowerOnController
from .shutdown_control import GracefulShutdownController

_LOGGER = logging.getLogger(__name__)


class IpmiCoreCoordinator(DataUpdateCoordinator[bool]):
    """Store the last successfully read *physical* chassis state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: IpmiCoreClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(
                seconds=int(entry.data.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS))
            ),
            always_update=False,
        )
        self.client = client
        self._operation_lock = asyncio.Lock()
        self._last_failure_signature: tuple[str, str, int] | None = None
        self._power_on = PowerOnController(
            send_on=self._async_send_power_on,
            read_state=self._async_read_power,
            publish_state=self.async_set_updated_data,
            publish_unavailable=self._mark_unavailable,
        )
        self._graceful_shutdown = GracefulShutdownController(
            send_shutdown=self._async_send_graceful_shutdown,
            read_state=self._async_read_power,
            publish_state=self.async_set_updated_data,
            publish_unavailable=self._mark_unavailable,
        )

    async def _async_operation(self, fn):
        # Status, button and confirmation probes share one serialized lane.
        # Do not allow concurrent BMC workers, even across HA entities.
        async with asyncio.timeout(OPERATION_TIMEOUT):
            async with self._operation_lock:
                return await self.hass.async_add_executor_job(fn)

    async def _async_read_power(self) -> bool:
        return await self._async_operation(self.client.get_power)

    async def _async_send_power_on(self):
        return await self._async_operation(self.client.power_on)

    async def _async_send_graceful_shutdown(self):
        return await self._async_operation(self.client.graceful_shutdown)

    def _mark_unavailable(self) -> None:
        self.async_set_update_error(UpdateFailed("BMC power status is not available"))

    async def async_power_on(self) -> None:
        """Guard power-on and confirm the physical transition asynchronously."""
        if self._graceful_shutdown.is_active:
            raise IpmiCoreError("Graceful shutdown is already in progress")
        await self._power_on.async_press()

    async def async_graceful_shutdown(self) -> None:
        """Only ACPI OS shutdown, never a chassis power cut."""
        if self._power_on.is_active:
            raise IpmiCoreError("Power-on is already in progress")
        await self._graceful_shutdown.async_press()

    async def async_shutdown(self) -> None:
        await self._power_on.async_shutdown()
        await self._graceful_shutdown.async_shutdown()

    async def _async_update_data(self) -> bool:
        try:
            result = await self._async_read_power()
            self._last_failure_signature = None
            return result
        except (TimeoutError, IpmiCoreError) as err:
            # A short, sanitized signature makes production debugging possible
            # without logging BMC responses, credentials or exception messages.
            root = err
            while root.__cause__ is not None:
                root = root.__cause__
            frames = traceback.extract_tb(root.__traceback__)
            last = frames[-1] if frames else None
            signature = (
                type(root).__name__,
                last.name if last else "unknown",
                last.lineno if last else 0,
            )
            if signature != self._last_failure_signature:
                _LOGGER.warning(
                    "IPMI Core poll failed: %s in %s (line %s); "
                    "exception details intentionally omitted",
                    *signature,
                )
                self._last_failure_signature = signature
            raise UpdateFailed("BMC power status is not available") from err
