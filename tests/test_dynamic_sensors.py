"""Offline Home Assistant entity contract tests with minimal runtime stubs."""
from __future__ import annotations
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'ipmi_core'


class CoordinatorEntityStub:
    def __class_getitem__(cls, ignored):
        return cls
    def __init__(self, coordinator):
        self.coordinator = coordinator
    @property
    def available(self):
        return self.coordinator.last_update_success


class SensorEntityStub: pass
class BinarySensorStub: pass
class SensorDeviceClassStub:
    TEMPERATURE='temperature'; VOLTAGE='voltage'; CURRENT='current'; POWER='power'
class BinaryDeviceClassStub:
    POWER='power'; CONNECTIVITY='connectivity'; PROBLEM='problem'


class Entry:
    entry_id='one'
    title='Test BMC'
    def __init__(self, coord):
        self.runtime_data=types.SimpleNamespace(telemetry=coord,coordinator=coord)
        self.cancel=[]
    def async_on_unload(self, callback):
        self.cancel.append(callback)


class Coordinator:
    def __init__(self, data=None):
        self.last_update_success=True
        self.data=data
        self.listeners=[]
    def async_add_listener(self, fn):
        self.listeners.append(fn)
        return lambda: self.listeners.remove(fn)
    def update(self,data):
        self.data=data
        for fn in self.listeners:
            fn()


class EntityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake={}
        def make(name,**items):
            obj=types.ModuleType(name)
            for k,v in items.items(): setattr(obj,k,v)
            fake[name]=obj
        make('homeassistant')
        make('homeassistant.components')
        make('homeassistant.components.sensor',SensorDeviceClass=SensorDeviceClassStub,
             SensorEntity=SensorEntityStub,
             SensorStateClass=types.SimpleNamespace(MEASUREMENT='measurement'))
        make('homeassistant.components.binary_sensor',BinarySensorDeviceClass=BinaryDeviceClassStub,
             BinarySensorEntity=BinarySensorStub)
        make('homeassistant.config_entries',ConfigEntry=Entry)
        make('homeassistant.const',EntityCategory=types.SimpleNamespace(DIAGNOSTIC='diagnostic'))
        make('homeassistant.core',HomeAssistant=object,callback=lambda x:x)
        make('homeassistant.helpers')
        make('homeassistant.helpers.entity_platform',AddEntitiesCallback=object)
        make('homeassistant.helpers.device_registry',DeviceInfo=dict)
        make('homeassistant.helpers.update_coordinator',CoordinatorEntity=CoordinatorEntityStub)
        make('ipmi_core.telemetry_coordinator',IpmiCoreTelemetryCoordinator=Coordinator)
        make('ipmi_core.coordinator',IpmiCoreCoordinator=Coordinator)
        package=sys.modules.get('ipmi_core')
        if package is None:
            package=types.ModuleType('ipmi_core')
            package.__path__=[str(ROOT)]
            fake['ipmi_core']=package
        from ipmi_core.telemetry_models import SensorSample,TelemetrySnapshot
        cls.SensorSample=SensorSample
        cls.TelemetrySnapshot=TelemetrySnapshot
        cls.exports={}
        with patch.dict(sys.modules,fake):
            for name in ('sensor','binary_sensor'):
                spec=importlib.util.spec_from_file_location('ipmi_core.'+name,ROOT/(name+'.py'))
                obj=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(obj)
                cls.exports[name]=obj

    def test_dynamic_discovery_from_initially_off_machine(self):
        coord=Coordinator(self.TelemetrySnapshot({},()))
        entry=Entry(coord)
        output=[]
        asyncio.run(self.exports['sensor'].async_setup_entry(None,entry,output.extend))
        self.assertEqual(output,[])
        self.assertEqual(len(entry.cancel),1)
        sample=self.SensorSample('stablekey','System Fan','RPM',600,1)
        coord.update(self.TelemetrySnapshot({'stablekey':sample},('System Fan',)))
        self.assertEqual(len(output),1)
        self.assertTrue(output[0].available)
        self.assertEqual(output[0].native_value,600)
        self.assertEqual(output[0].extra_state_attributes,{'bmc_health':'warning'})
        self.assertEqual(output[0]._attr_native_unit_of_measurement,'RPM')
        self.assertEqual(output[0]._attr_state_class,'measurement')
        coord.update(self.TelemetrySnapshot({'stablekey':sample},('System Fan',)))
        self.assertEqual(len(output),1)
        coord.update(self.TelemetrySnapshot({},()))
        self.assertFalse(output[0].available)
        self.assertIsNone(output[0].native_value)
        entry.cancel[0]()
        self.assertEqual(coord.listeners,[])

    def test_temperature_voltage_device_classes(self):
        mod=self.exports['sensor']
        coord=Coordinator(None)
        entry=Entry(coord)
        samples=[self.SensorSample('tmp','CPU Temp','°C',34,0),
                 self.SensorSample('volt','12V','V',12.064,0)]
        a,b=[mod.IpmiCoreMetricSensor(entry,x.key,x) for x in samples]
        self.assertEqual(a._attr_device_class,'temperature')
        self.assertEqual(b._attr_device_class,'voltage')
        self.assertEqual(b._attr_suggested_display_precision,3)

    def test_hardware_warning_alert_persists_and_off_does_not_mean_ok(self):
        mod=self.exports['binary_sensor']
        sample=self.SensorSample('fan','System Fan','RPM',600,1)
        c=Coordinator(self.TelemetrySnapshot({'fan':sample},('System Fan',)))
        entity=mod.IpmiCoreHardwareWarningSensor(Entry(c))
        self.assertTrue(entity.available)
        self.assertTrue(entity.is_on)
        self.assertEqual(entity.extra_state_attributes,{'affected_sensors':['System Fan']})
        c.update(self.TelemetrySnapshot({},()))
        self.assertFalse(entity.available)
        c.update(self.TelemetrySnapshot({},('Chassis Intru',)))
        self.assertTrue(entity.available)
        self.assertTrue(entity.is_on)
        c.last_update_success=False
        self.assertFalse(entity.available)

if __name__=='__main__':unittest.main()
