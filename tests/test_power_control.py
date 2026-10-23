"""Regression tests for guarded IPMI ON and physical state confirmation."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "ipmi_core"
package = sys.modules.get("ipmi_core")
if package is None:
    package = types.ModuleType("ipmi_core")
    package.__path__ = [str(ROOT)]
    sys.modules["ipmi_core"] = package
if "ipmi_core.client" not in sys.modules:
    spec = importlib.util.spec_from_file_location("ipmi_core.client", ROOT / "client.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
spec = importlib.util.spec_from_file_location(
    "ipmi_core.power_control", ROOT / "power_control.py"
)
power = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = power
spec.loader.exec_module(power)
from ipmi_core.client import IpmiCoreError, PowerOnResult


class TestPowerOnController(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.send = AsyncMock(return_value=PowerOnResult(sent=True, observed_on=False))
        self.read = AsyncMock(return_value=True)
        self.publish = MagicMock()
        self.unavailable = MagicMock()
        self.controller = power.PowerOnController(
            self.send, self.read, self.publish, self.unavailable,
            interval=0.002, timeout=0.1, cooldown=60,
        )

    async def asyncTearDown(self):
        await self.controller.async_shutdown()

    async def wait_confirmation(self):
        task = self.controller._confirmation_task
        if task is not None:
            await asyncio.wait_for(task, 1)

    async def test_off_on_updates_as_soon_as_bmc_confirms(self):
        self.read.side_effect = [False, False, True]
        await self.controller.async_press()
        self.publish.assert_not_called()
        await self.wait_confirmation()
        self.assertEqual(self.publish.call_args_list[-1].args, (True,))
        self.assertEqual(self.read.await_count, 3)
        self.send.assert_awaited_once()

    async def test_already_on_skips_command_and_publishes_immediately(self):
        self.send.return_value = PowerOnResult(sent=False, observed_on=True)
        await self.controller.async_press()
        self.publish.assert_called_once_with(True)
        self.assertIsNone(self.controller._confirmation_task)
        self.read.assert_not_awaited()

    async def test_concurrent_presses_issue_one_command(self):
        entered, proceed = asyncio.Event(), asyncio.Event()

        async def slow_send():
            entered.set()
            await proceed.wait()
            return PowerOnResult(sent=True, observed_on=False)

        self.send.side_effect = slow_send
        first = asyncio.create_task(self.controller.async_press())
        await entered.wait()
        await self.controller.async_press()
        proceed.set()
        await first
        await self.wait_confirmation()
        self.assertEqual(self.send.await_count, 1)

    async def test_press_during_confirmation_does_not_repeat_on(self):
        entered, proceed = asyncio.Event(), asyncio.Event()

        async def slow_read():
            entered.set()
            await proceed.wait()
            return True

        self.read.side_effect = slow_read
        await self.controller.async_press()
        await entered.wait()
        await self.controller.async_press()
        proceed.set()
        await self.wait_confirmation()
        self.send.assert_awaited_once()

    async def test_confirmation_timeout_never_claims_on(self):
        self.read.return_value = False
        await self.controller.async_press()
        await self.wait_confirmation()
        self.assertGreaterEqual(self.publish.call_count, 1)
        self.assertTrue(all(c.args == (False,) for c in self.publish.call_args_list))
        self.unavailable.assert_not_called()
        self.send.assert_awaited_once()

    async def test_transient_read_failure_becomes_unavailable_then_recovers(self):
        self.read.side_effect = [IpmiCoreError("offline"), True]
        await self.controller.async_press()
        await self.wait_confirmation()
        self.unavailable.assert_called_once()
        self.publish.assert_called_once_with(True)

    async def test_command_failure_fails_closed_and_cooldown_is_read_only(self):
        self.send.side_effect = IpmiCoreError("command error")
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.unavailable.assert_called_once()
        self.publish.assert_not_called()
        await self.controller.async_press()
        self.assertEqual(self.send.await_count, 1)
        self.read.assert_awaited_once()

    async def test_cooldown_does_not_resend_unconfirmed_on(self):
        self.read.return_value = False
        await self.controller.async_press()
        await self.wait_confirmation()
        await self.controller.async_press()
        self.send.assert_awaited_once()
        self.assertEqual(self.publish.call_args.args, (False,))

    async def test_unload_cancels_confirmation(self):
        entered = asyncio.Event()

        async def blocked_read():
            entered.set()
            await asyncio.sleep(10)
            return True

        self.read.side_effect = blocked_read
        await self.controller.async_press()
        await entered.wait()
        await self.controller.async_shutdown()
        self.publish.assert_not_called()
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()

    async def test_shutdown_during_send_does_not_spawn_confirmation(self):
        entered, proceed = asyncio.Event(), asyncio.Event()

        async def slow_send():
            entered.set()
            await proceed.wait()
            return PowerOnResult(sent=True, observed_on=False)

        self.send.side_effect = slow_send
        sending = asyncio.create_task(self.controller.async_press())
        await entered.wait()
        await self.controller.async_shutdown()
        proceed.set()
        await sending
        self.assertIsNone(self.controller._confirmation_task)
        self.read.assert_not_awaited()
        self.publish.assert_not_called()

    async def test_noop_rejects_inconsistent_on_command_result(self):
        self.send.return_value = PowerOnResult(sent=True, observed_on=True)
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.unavailable.assert_called_once()
        self.publish.assert_not_called()

    async def test_invalid_acknowledgement_is_not_optimistic(self):
        self.send.return_value = PowerOnResult(sent=False, observed_on=False)
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.publish.assert_not_called()
        self.unavailable.assert_called_once()
        self.assertIsNone(self.controller._confirmation_task)


if __name__ == "__main__":
    unittest.main()
