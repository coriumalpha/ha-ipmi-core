"""Offline regression tests for chassis vs. BMC communication diagnostics."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "ipmi_core"


class CoordinatorEntityStub:
    """Minimal generic stub for testing this Home Assistant entity contract."""

    def __class_getitem__(cls, _):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return self.coordinator.last_update_success


class BinarySensorEntityStub:
    pass


class DeviceClassStub:
    POWER = "power"
    CONNECTIVITY = "connectivity"
    PROBLEM = "problem"


class EntryStub:
    entry_id = "configured_bmc_01"
    title = "Test IPMI"

    def __init__(self, coordinator):
        self.runtime_data = types.SimpleNamespace(coordinator=coordinator, telemetry=coordinator)


class TestBmcCommunicationSensor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_modules = {}

        def module(name, **attributes):
            obj = types.ModuleType(name)
            for key, value in attributes.items():
                setattr(obj, key, value)
            fake_modules[name] = obj

        module("homeassistant")
        module("homeassistant.components")
        module("homeassistant.components.binary_sensor",
               BinarySensorDeviceClass=DeviceClassStub,
               BinarySensorEntity=BinarySensorEntityStub)
        module("homeassistant.config_entries", ConfigEntry=EntryStub)
        module("homeassistant.const",
               EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic"))
        module("homeassistant.core", HomeAssistant=object)
        module("homeassistant.helpers")
        module("homeassistant.helpers.device_registry", DeviceInfo=dict)
        module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
        module("homeassistant.helpers.update_coordinator",
               CoordinatorEntity=CoordinatorEntityStub)
        module("ipmi_core.coordinator", IpmiCoreCoordinator=object)

        package = sys.modules.get("ipmi_core")
        if package is None:
            package = types.ModuleType("ipmi_core")
            package.__path__ = [str(ROOT)]
            fake_modules["ipmi_core"] = package

        spec = importlib.util.spec_from_file_location(
            "ipmi_core.binary_sensor", ROOT / "binary_sensor.py"
        )
        obj = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, fake_modules):
            spec.loader.exec_module(obj)
        cls.mod = obj

    def test_distinct_power_and_comm_diagnostics(self):
        coord = types.SimpleNamespace(data=False, last_update_success=True)
        entry = EntryStub(coord)
        captured = []
        asyncio.run(self.mod.async_setup_entry(None, entry, captured.extend))
        self.assertEqual(len(captured), 3)
        power, bmc, warning = captured
        self.assertEqual(warning._attr_device_class, DeviceClassStub.PROBLEM)
        self.assertNotEqual(power._attr_unique_id, bmc._attr_unique_id)
        self.assertFalse(power.is_on)  # Chassis is physically OFF.
        self.assertTrue(bmc.is_on)   # But IPMI communication works.
        self.assertEqual(bmc._attr_device_class, DeviceClassStub.CONNECTIVITY)
        self.assertEqual(bmc._attr_entity_category, "diagnostic")

        coord.last_update_success = False
        self.assertFalse(bmc.is_on)
        self.assertTrue(bmc.available)  # The diagnostic must not disappear.
        self.assertFalse(power.available)
        coord.last_update_success = True
        self.assertTrue(bmc.is_on)
        self.assertTrue(power.available)
        self.assertFalse(power.is_on)  # No guessing power from connectivity.

    def test_acpi_button_no_longer_disabled_by_default(self):
        source = (ROOT / "button.py").read_text()
        parsed = ast.parse(source)
        acpi = next(node for node in parsed.body
                    if isinstance(node, ast.ClassDef)
                    and node.name == "IpmiCoreGracefulShutdownButton")
        assignments = {target.id for stmt in acpi.body
                       if isinstance(stmt, ast.Assign)
                       for target in stmt.targets if isinstance(target, ast.Name)}
        self.assertNotIn("_attr_entity_registry_enabled_default", assignments)
        self.assertIn("_attr_translation_key", assignments)


if __name__ == "__main__":
    unittest.main()
