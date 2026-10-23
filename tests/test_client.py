"""No HA/python-ipmi dependency: exercise bounded subprocess adapter via mocks."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "ipmi_core"
package = types.ModuleType("ipmi_core")
package.__path__ = [str(ROOT)]
sys.modules["ipmi_core"] = package
spec = spec_from_file_location("ipmi_core.client", ROOT / "client.py")
client_mod = module_from_spec(spec)
sys.modules[spec.name] = client_mod
spec.loader.exec_module(client_mod)


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = client_mod.IpmiCoreClient("192.0.2.60", 623, "operator", "SECRET")

    def _ok(self, output):
        return subprocess.CompletedProcess([], 0, output, "")

    @patch.object(client_mod.subprocess, "run")
    def test_read_on(self, run):
        run.return_value = self._ok('{"ok": true, "powerstate": "on"}')
        self.assertTrue(self.client.get_power())
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 12)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(kwargs["input"], '{"action": "status", "host": "192.0.2.60", "port": 623, "username": "operator", "password": "SECRET", "privlevel": 3}')
        argv = run.call_args.args[0]
        self.assertEqual(argv[:2], [sys.executable, "-I"])
        self.assertNotIn("SECRET", str(argv))
        self.assertEqual(argv[-1], str(ROOT / "worker.py"))

    @patch.object(client_mod.subprocess, "run")
    def test_repeated_queries_get_fresh_isolated_worker(self, run):
        run.return_value = self._ok('{"ok":true,"powerstate":"on"}')
        self.assertEqual([self.client.get_power() for _ in range(3)], [True] * 3)
        self.assertEqual(run.call_count, 3)

    @patch.object(client_mod.subprocess, "run")
    def test_off(self, run):
        run.return_value = self._ok('{"ok":true,"powerstate":"off"}')
        self.assertFalse(self.client.get_power())

    @patch.object(client_mod.subprocess, "run")
    def test_timeout_fails_closed(self, run):
        run.side_effect = subprocess.TimeoutExpired(["python"], 12)
        with self.assertRaisesRegex(client_mod.IpmiCoreError, "timed out"):
            self.client.get_power()

    @patch.object(client_mod.subprocess, "run")
    def test_worker_failure_fails_closed(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, '{"ok":false}', "")
        with self.assertRaises(client_mod.IpmiCoreError):
            self.client.get_power()

    @patch.object(client_mod.subprocess, "run")
    def test_invalid_state_fails_closed(self, run):
        run.return_value = self._ok('{"ok":true,"powerstate":"UNKNOWN"}')
        with self.assertRaises(client_mod.IpmiCoreError):
            self.client.get_power()

    @patch.object(client_mod.subprocess, "run")
    def test_invalid_json_fails_closed(self, run):
        run.return_value = self._ok('not json')
        with self.assertRaises(client_mod.IpmiCoreError):
            self.client.get_power()

    @patch.object(client_mod.subprocess, "run")
    def test_power_on_success(self, run):
        run.return_value = self._ok('{"ok":true,"sent":true,"powerstate":"off"}')
        self.assertEqual(
            self.client.power_on(),
            client_mod.PowerOnResult(sent=True, observed_on=False),
        )
        self.assertIn('"action": "power_on"', run.call_args.kwargs["input"])

    @patch.object(client_mod.subprocess, "run")
    def test_power_on_skip_if_already_on(self, run):
        run.return_value = self._ok('{"ok":true,"sent":false,"powerstate":"on"}')
        self.assertEqual(
            self.client.power_on(),
            client_mod.PowerOnResult(sent=False, observed_on=True),
        )

    @patch.object(client_mod.subprocess, "run")
    def test_power_on_reject_inconsistent_state(self, run):
        for response in (
            '{"ok":true,"sent":true,"powerstate":"on"}',
            '{"ok":true,"sent":false,"powerstate":"off"}',
        ):
            with self.subTest(response=response):
                run.return_value = self._ok(response)
                with self.assertRaises(client_mod.IpmiCoreError):
                    self.client.power_on()

    @patch.object(client_mod.subprocess, "run")
    def test_acpi_shutdown_when_on(self, run):
        run.return_value = self._ok('{"ok":true,"sent":true,"powerstate":"on"}')
        self.assertEqual(
            self.client.graceful_shutdown(),
            client_mod.GracefulShutdownResult(sent=True, observed_off=False),
        )
        self.assertIn('"action": "graceful_shutdown"', run.call_args.kwargs["input"])

    @patch.object(client_mod.subprocess, "run")
    def test_acpi_shutdown_noop_when_off(self, run):
        run.return_value = self._ok('{"ok":true,"sent":false,"powerstate":"off"}')
        self.assertEqual(
            self.client.graceful_shutdown(),
            client_mod.GracefulShutdownResult(sent=False, observed_off=True),
        )

    @patch.object(client_mod.subprocess, "run")
    def test_acpi_shutdown_invalid_ack_fails_closed(self, run):
        for response in (
            '{"ok":true,"sent":true,"powerstate":"off"}',
            '{"ok":true,"sent":false,"powerstate":"on"}',
        ):
            with self.subTest(response=response):
                run.return_value = self._ok(response)
                with self.assertRaises(client_mod.IpmiCoreError):
                    self.client.graceful_shutdown()

    @patch.object(client_mod.subprocess, "run")
    def test_power_on_reject_nonbool(self, run):
        run.return_value = self._ok('{"ok":true,"sent":"true","powerstate":"off"}')
        with self.assertRaises(client_mod.IpmiCoreError):
            self.client.power_on()

if __name__ == "__main__":
    unittest.main()
