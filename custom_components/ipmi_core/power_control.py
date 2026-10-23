"""Bounded fail-closed power-on orchestration, independent of Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .client import IpmiCoreError, PowerOnResult
from .const import POWER_ON_CONFIRM_INTERVAL, POWER_ON_CONFIRM_TIMEOUT, POWER_ON_RETRY_COOLDOWN

_LOGGER = logging.getLogger(__name__)


class PowerOnController:
    """Guard one ON request and publish only states verified by the BMC."""

    def __init__(
        self,
        send_on: Callable[[], Awaitable[PowerOnResult]],
        read_state: Callable[[], Awaitable[bool]],
        publish_state: Callable[[bool], None],
        publish_unavailable: Callable[[], None],
        *,
        interval: float = POWER_ON_CONFIRM_INTERVAL,
        timeout: float = POWER_ON_CONFIRM_TIMEOUT,
        cooldown: float = POWER_ON_RETRY_COOLDOWN,
    ) -> None:
        self._send_on = send_on
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
        """Suppress concurrent/duplicate ON requests without blocking the UI."""
        if self._stopped:
            raise IpmiCoreError("IPMI Core device is unloading")
        if self._busy or (
            self._confirmation_task is not None
            and not self._confirmation_task.done()
        ):
            return

        self._busy = True
        try:
            now = asyncio.get_running_loop().time()
            if self._last_attempt is not None and now - self._last_attempt < self._cooldown:
                # A prior command may have been accepted even if its response
                # was lost: only perform a fresh read during the cooldown.
                try:
                    self._publish_state(await self._read_state())
                except (IpmiCoreError, TimeoutError):
                    self._publish_unavailable()
                    raise
                return

            self._last_attempt = now
            try:
                result = await self._send_on()
            except (IpmiCoreError, TimeoutError):
                self._publish_unavailable()
                raise
            if self._stopped:
                # An in-flight command cannot be safely withdrawn. The config
                # entry has been unloaded; do not create new tasks afterwards.
                return
            if result.observed_on and result.sent:
                self._publish_unavailable()
                raise IpmiCoreError("Inconsistent IPMI power-on acknowledgement")
            if result.observed_on:
                # Verified ON, with no command sent by the worker.
                self._last_attempt = None
                self._publish_state(True)
                return
            if not result.sent:
                self._publish_unavailable()
                raise IpmiCoreError("Invalid IPMI power-on acknowledgement")
            # Accepted ON is not physical ON: verify in a background task.
            self._confirmation_task = asyncio.create_task(
                self._async_confirm_on(), name="ipmi_core_confirm_power_on"
            )
        finally:
            self._busy = False

    async def _async_confirm_on(self) -> None:
        """Read-only confirmation with a finite deadline; never resend ON."""
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._interval)
                    try:
                        state = await self._read_state()
                    except (IpmiCoreError, TimeoutError):
                        self._publish_unavailable()
                        continue
                    self._publish_state(state)
                    if state:
                        return
        except TimeoutError:
            _LOGGER.warning(
                "IPMI power-on not physically confirmed within %.0f seconds",
                self._timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            self._publish_unavailable()
            _LOGGER.error("IPMI power-on confirmation failed unexpectedly")
        finally:
            self._confirmation_task = None

    async def async_shutdown(self) -> None:
        """Cancel follow-up reads on unload; do not interrupt an ON command."""
        self._stopped = True
        if self._confirmation_task is not None:
            self._confirmation_task.cancel()
            await asyncio.gather(self._confirmation_task, return_exceptions=True)
            self._confirmation_task = None
