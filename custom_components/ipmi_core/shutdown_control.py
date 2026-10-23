"""Optional, explicitly opt-in ACPI OS shutdown with physical-state confirmation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .client import GracefulShutdownResult, IpmiCoreError
from .const import (
    SHUTDOWN_CONFIRM_INTERVAL,
    SHUTDOWN_CONFIRM_TIMEOUT,
    SHUTDOWN_RETRY_COOLDOWN,
)

_LOGGER = logging.getLogger(__name__)


class GracefulShutdownController:
    """Never cut power: request OS shutdown once and confirm the BMC's OFF."""

    def __init__(
        self,
        send_shutdown: Callable[[], Awaitable[GracefulShutdownResult]],
        read_state: Callable[[], Awaitable[bool]],
        publish_state: Callable[[bool], None],
        publish_unavailable: Callable[[], None],
        *,
        interval: float = SHUTDOWN_CONFIRM_INTERVAL,
        timeout: float = SHUTDOWN_CONFIRM_TIMEOUT,
        cooldown: float = SHUTDOWN_RETRY_COOLDOWN,
    ) -> None:
        self._send_shutdown = send_shutdown
        self._read_state = read_state
        self._publish_state = publish_state
        self._publish_unavailable = publish_unavailable
        self._interval = interval
        self._timeout = timeout
        self._cooldown = cooldown
        self._busy = False
        self._stopped = False
        self._confirmation_task: asyncio.Task[None] | None = None
        self._last_attempt: float | None = None

    @property
    def is_active(self) -> bool:
        return self._busy or (
            self._confirmation_task is not None
            and not self._confirmation_task.done()
        )

    async def async_press(self) -> None:
        """Issue at most one ACPI request, never an IPMI hard-OFF."""
        if self._stopped:
            raise IpmiCoreError("IPMI Core device is unloading")
        if self.is_active:
            return
        self._busy = True
        try:
            now = asyncio.get_running_loop().time()
            if self._last_attempt is not None and now - self._last_attempt < self._cooldown:
                # A previous request might have been accepted despite a lost
                # response. Only read the chassis; never blindly resend.
                try:
                    self._publish_state(await self._read_state())
                except (IpmiCoreError, TimeoutError):
                    self._publish_unavailable()
                    raise
                return
            self._last_attempt = now
            try:
                result = await self._send_shutdown()
            except (IpmiCoreError, TimeoutError):
                self._publish_unavailable()
                raise
            if self._stopped:
                # The ACPI signal may have been sent; do not start tasks after unload.
                return
            if result.observed_off and result.sent:
                self._publish_unavailable()
                raise IpmiCoreError("Inconsistent graceful shutdown acknowledgement")
            if result.observed_off:
                # Verified OFF: this is a no-op, never a shutdown command.
                self._last_attempt = None
                self._publish_state(False)
                return
            if not result.sent:
                self._publish_unavailable()
                raise IpmiCoreError("Invalid graceful shutdown acknowledgement")
            # A successful ACPI *request* does not mean the OS is down.
            self._confirmation_task = asyncio.create_task(
                self._async_confirm_off(), name="ipmi_core_confirm_graceful_shutdown"
            )
        finally:
            self._busy = False

    async def _async_confirm_off(self) -> None:
        """Keep the real ON state visible until the BMC proves OFF."""
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._interval)
                    try:
                        still_on = await self._read_state()
                    except (IpmiCoreError, TimeoutError):
                        self._publish_unavailable()
                        continue
                    self._publish_state(still_on)
                    if not still_on:
                        return
        except TimeoutError:
            _LOGGER.warning(
                "Graceful ACPI shutdown was not physically confirmed within %.0f seconds; "
                "no forced power-off was attempted",
                self._timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            self._publish_unavailable()
            _LOGGER.error("IPMI graceful shutdown confirmation failed unexpectedly")
        finally:
            self._confirmation_task = None

    async def async_shutdown(self) -> None:
        """Stop all verification tasks before unloading the HA integration."""
        self._stopped = True
        if self._confirmation_task is not None:
            self._confirmation_task.cancel()
            await asyncio.gather(self._confirmation_task, return_exceptions=True)
            self._confirmation_task = None
