"""Offline graceful ACPI shutdown tests: never issue hard power commands."""

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
    client = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = client
    spec.loader.exec_module(client)

spec = importlib.util.spec_from_file_location(
    "ipmi_core.shutdown_control", ROOT / "shutdown_control.py"
)
shutdown = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shutdown
spec.loader.exec_module(shutdown)
from ipmi_core.client import GracefulShutdownResult, IpmiCoreError


class TestGracefulShutdown(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.send = AsyncMock(return_value=GracefulShutdownResult(True, False))
        self.read = AsyncMock(return_value=False)
        self.publish = MagicMock()
        self.unavailable = MagicMock()
        self.controller = shutdown.GracefulShutdownController(
            self.send, self.read, self.publish, self.unavailable,
            interval=0.002, timeout=0.08, cooldown=600,
        )

    async def asyncTearDown(self):
        await self.controller.async_shutdown()

    async def wait_confirmation(self):
        task = self.controller._confirmation_task
        if task is not None:
            await asyncio.wait_for(task, 1)

    async def test_on_to_off_confirms_actual_physical_off(self):
        self.read.side_effect = [True, True, False]
        await self.controller.async_press()
        self.publish.assert_not_called()  # Never optimistically announce OFF.
        await self.wait_confirmation()
        self.assertEqual(self.publish.call_args.args, (False,))
        self.assertEqual(self.send.await_count, 1)

    async def test_already_off_is_read_only_noop(self):
        self.send.return_value = GracefulShutdownResult(False, True)
        await self.controller.async_press()
        self.publish.assert_called_once_with(False)
        self.read.assert_not_awaited()
        self.assertIsNone(self.controller._confirmation_task)

    async def test_no_duplicate_requests_while_sending(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def slow_send():
            started.set()
            await finish.wait()
            return GracefulShutdownResult(True, False)

        self.send.side_effect = slow_send
        first = asyncio.create_task(self.controller.async_press())
        await started.wait()
        self.assertTrue(self.controller.is_active)
        await self.controller.async_press()
        finish.set()
        await first
        await self.wait_confirmation()
        self.send.assert_awaited_once()

    async def test_no_duplicate_requests_while_monitoring(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def slow_read():
            started.set()
            await finish.wait()
            return False

        self.read.side_effect = slow_read
        await self.controller.async_press()
        await started.wait()
        await self.controller.async_press()
        finish.set()
        await self.wait_confirmation()
        self.send.assert_awaited_once()

    async def test_timeout_keeps_verified_on(self):
        self.read.return_value = True
        await self.controller.async_press()
        await self.wait_confirmation()
        self.assertGreater(self.publish.call_count, 0)
        self.assertTrue(all(call.args == (True,) for call in self.publish.call_args_list))
        self.unavailable.assert_not_called()

    async def test_transport_error_then_recovery(self):
        self.read.side_effect = [IpmiCoreError("offline"), False]
        await self.controller.async_press()
        await self.wait_confirmation()
        self.unavailable.assert_called_once()
        self.publish.assert_called_once_with(False)

    async def test_failed_command_is_unavailable_no_blind_retry(self):
        self.send.side_effect = IpmiCoreError("rejected")
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.unavailable.assert_called_once()
        await self.controller.async_press()
        self.send.assert_awaited_once()
        self.read.assert_awaited_once()

    async def test_cooldown_is_read_only(self):
        self.read.return_value = True
        await self.controller.async_press()
        await self.wait_confirmation()
        await self.controller.async_press()
        self.send.assert_awaited_once()
        self.assertEqual(self.publish.call_args.args, (True,))

    async def test_unload_cancels_monitor(self):
        started = asyncio.Event()

        async def blocked_read():
            started.set()
            await asyncio.sleep(5)
            return False

        self.read.side_effect = blocked_read
        await self.controller.async_press()
        await started.wait()
        await self.controller.async_shutdown()
        self.publish.assert_not_called()
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()

    async def test_unload_during_send_does_not_start_monitor(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def slow_send():
            started.set()
            await finish.wait()
            return GracefulShutdownResult(True, False)

        self.send.side_effect = slow_send
        task = asyncio.create_task(self.controller.async_press())
        await started.wait()
        await self.controller.async_shutdown()
        finish.set()
        await task
        self.assertIsNone(self.controller._confirmation_task)
        self.publish.assert_not_called()

    async def test_invalid_acknowledgement_fails_closed(self):
        self.send.return_value = GracefulShutdownResult(False, False)
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.publish.assert_not_called()
        self.unavailable.assert_called_once()

    async def test_contradictory_acknowledgement_fails_closed(self):
        self.send.return_value = GracefulShutdownResult(True, True)
        with self.assertRaises(IpmiCoreError):
            await self.controller.async_press()
        self.publish.assert_not_called()
        self.unavailable.assert_called_once()


if __name__ == "__main__":
    unittest.main()
