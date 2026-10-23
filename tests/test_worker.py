"""Test the isolated worker's strict operation allowlist using fake pyghmi."""
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "ipmi_core"
spec = importlib.util.spec_from_file_location("ipmi_core_worker_test", ROOT / "worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

REQUEST = {"action": "status", "host": "192.0.2.60", "port": 623,
           "username": "operator", "password": "SECRET", "privlevel": 3}


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.mock = MagicMock()
        self.ipmi_command = types.ModuleType("pyghmi.ipmi.command")
        self.ipmi_command.Command = MagicMock(return_value=self.mock)
        self.ipmi = types.ModuleType("pyghmi.ipmi")
        self.ipmi.command = self.ipmi_command
        self.pyghmi = types.ModuleType("pyghmi")
        self.pyghmi.ipmi = self.ipmi
        self.patch_modules = patch.dict(sys.modules, {"pyghmi": self.pyghmi,
            "pyghmi.ipmi": self.ipmi, "pyghmi.ipmi.command": self.ipmi_command})
        self.patch_modules.start()
        self.addCleanup(self.patch_modules.stop)

    def test_status_read_only(self):
        self.mock.get_power.return_value = {"powerstate": "on"}
        self.assertEqual(worker.perform(REQUEST), {"ok": True, "powerstate": "on"})
        self.mock.set_power.assert_not_called()
        self.mock.ipmi_session.logout.assert_called_once()
        self.assertEqual(self.ipmi_command.Command.call_args.kwargs["privlevel"], 3)
        self.assertFalse(self.ipmi_command.Command.call_args.kwargs["keepalive"])

    def test_power_on_only_when_off(self):
        self.mock.get_power.return_value = {"powerstate": "off"}
        request = {**REQUEST, "action": "power_on"}
        self.assertEqual(worker.perform(request), {"ok": True, "sent": True, "powerstate": "off"})
        self.mock.set_power.assert_called_once_with("on", wait=False)

    def test_already_on_has_no_command(self):
        self.mock.get_power.return_value = {"powerstate": "on"}
        self.assertEqual(worker.perform({**REQUEST, "action": "power_on"}),
                         {"ok": True, "sent": False, "powerstate": "on"})
        self.mock.set_power.assert_not_called()

    def test_acpi_shutdown_only_when_on(self):
        self.mock.get_power.return_value = {"powerstate": "on"}
        self.mock.set_power.return_value = {"pendingpowerstate": "shutdown"}
        response = worker.perform({**REQUEST, "action": "graceful_shutdown"})
        self.assertEqual(response, {"ok": True, "sent": True, "powerstate": "on"})
        self.mock.set_power.assert_called_once_with("shutdown", wait=False)

    def test_acpi_shutdown_noop_when_off(self):
        self.mock.get_power.return_value = {"powerstate": "off"}
        response = worker.perform({**REQUEST, "action": "graceful_shutdown"})
        self.assertEqual(response, {"ok": True, "sent": False, "powerstate": "off"})
        self.mock.set_power.assert_not_called()

    def test_acpi_shutdown_rejection_is_error_without_hard_off(self):
        self.mock.get_power.return_value = {"powerstate": "on"}
        self.mock.set_power.return_value = {"error": "unsupported"}
        with self.assertRaises(ValueError):
            worker.perform({**REQUEST, "action": "graceful_shutdown"})
        self.mock.set_power.assert_called_once_with("shutdown", wait=False)

    def test_acpi_shutdown_unreadable_state_never_sends(self):
        self.mock.get_power.return_value = {"powerstate": "?"}
        with self.assertRaises(ValueError):
            worker.perform({**REQUEST, "action": "graceful_shutdown"})
        self.mock.set_power.assert_not_called()

    def test_refuse_any_other_operation_before_connection(self):
        for action in ["off", "reset", "cycle", "raw", None]:
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    worker.perform({**REQUEST, "action": action})
        self.ipmi_command.Command.assert_not_called()

    def test_backend_error_not_silently_successful(self):
        self.mock.get_power.return_value = {"powerstate": "off"}
        self.mock.set_power.return_value = {"error": "rejected"}
        with self.assertRaises(ValueError):
            worker.perform({**REQUEST, "action": "power_on"})
        self.mock.ipmi_session.logout.assert_called_once()

    def test_unreadable_state(self):
        self.mock.get_power.return_value = {"powerstate": "?"}
        with self.assertRaises(ValueError):
            worker.perform(REQUEST)
        self.mock.ipmi_session.logout.assert_called_once()

if __name__ == "__main__":
    unittest.main()
