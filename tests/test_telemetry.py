"""Deterministic, offline regression tests for read-only SDR telemetry."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'ipmi_core'

pkg = sys.modules.get('ipmi_core')
if pkg is None:
    pkg = types.ModuleType('ipmi_core')
    pkg.__path__ = [str(ROOT)]
    sys.modules['ipmi_core'] = pkg
for modname in ('const', 'telemetry_models', 'client'):
    if f'ipmi_core.{modname}' not in sys.modules:
        spec = importlib.util.spec_from_file_location(f'ipmi_core.{modname}', ROOT / f'{modname}.py')
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
from ipmi_core.telemetry_models import parse_telemetry_response, TelemetryProtocolError
from ipmi_core.client import IpmiCoreClient, IpmiCoreError

spec = importlib.util.spec_from_file_location('test_ipmi_telemetry_worker', ROOT / 'worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

REQUEST = dict(action='telemetry', host='192.0.2.60', port=623,
               username='operator', password='FAKE_PASSWORD', privlevel=3)


def reading(name, unit, value, health=0, unavailable=0):
    return types.SimpleNamespace(name=name, units=unit, value=value,
                                 health=health, unavailable=unavailable)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.cmd = MagicMock()
        self.module = types.ModuleType('pyghmi.ipmi.command')
        self.module.Command = MagicMock(return_value=self.cmd)
        self.ipmi = types.ModuleType('pyghmi.ipmi')
        self.ipmi.command = self.module
        self.pyghmi = types.ModuleType('pyghmi')
        self.pyghmi.ipmi = self.ipmi
        self.mocker = patch.dict(sys.modules, {
            'pyghmi': self.pyghmi,
            'pyghmi.ipmi': self.ipmi,
            'pyghmi.ipmi.command': self.module,
        })
        self.mocker.start()
        self.addCleanup(self.mocker.stop)

    def test_realistic_bmc_sample_and_warning(self):
        self.cmd.get_sensor_data.return_value = [
            reading('CPU Temp', '°C', 34),
            reading('System Fan', 'RPM', 600, health=1),
            reading('Aux Fan', 'RPM', 1000),
            reading('12V', 'V', 12.064),
            reading('Chassis Intru', '', None),
            reading('FAN1', 'RPM', None, unavailable=1),
        ]
        result = worker.perform(REQUEST)
        self.assertEqual(len(result['sensors']), 4)
        self.assertEqual(result['warnings'], [{'name': 'System Fan', 'health': 1}])
        self.assertEqual([x['name'] for x in result['sensors']], ['CPU Temp','System Fan','Aux Fan','12V'])
        self.assertEqual(self.cmd.get_power.call_count, 0)
        self.cmd.set_power.assert_not_called()
        self.cmd.ipmi_session.logout.assert_called_once()

    def test_off_or_missing_sdr_values_are_never_zero(self):
        self.cmd.get_sensor_data.return_value = [
            reading('CPU Temp','°C',None,unavailable=1),
            reading('System Fan','RPM',None,unavailable=1),
        ]
        self.assertEqual(worker.perform(REQUEST), {'ok': True, 'sensors': [], 'warnings': []})

    def test_reject_hard_off_and_unlisted_operations(self):
        for op in ('off','reset','cycle','raw','clear_sel','set_sensor'):
            with self.subTest(op=op), self.assertRaises(ValueError):
                worker.perform({**REQUEST,'action':op})
        self.module.Command.assert_not_called()

    def test_discrete_intrusion_warning_does_not_create_fake_numeric(self):
        self.cmd.get_sensor_data.return_value = [reading('Chassis Intru','',None,health=2)]
        result = worker.perform(REQUEST)
        self.assertEqual(result['sensors'], [])
        self.assertEqual(result['warnings'], [{'name':'Chassis Intru','health':2}])

    def test_sensor_name_with_controls_is_filtered(self):
        self.cmd.get_sensor_data.return_value = [reading('bad\nname', '°C', 36)]
        self.assertEqual(worker.perform(REQUEST)['sensors'], [])

    def test_invalid_numeric_values_are_filtered(self):
        self.cmd.get_sensor_data.return_value = [
            reading('abc','V',float('nan')),
            reading('def','RPM',True),
            reading('ghi','V',float('inf')),
        ]
        self.assertEqual(worker.perform(REQUEST)['sensors'], [])


class ProtocolTests(unittest.TestCase):
    def test_stable_ids_independent_of_sensor_list_order(self):
        values = [
            dict(name='CPU Temp',unit='°C',value=34,health=0),
            dict(name='System Fan',unit='RPM',value=600,health=1),
            dict(name='VDIMM',unit='V',value=1.497,health=0),
        ]
        a=parse_telemetry_response({'sensors':values,'warnings':[{'name':'System Fan','health':1}]})
        b=parse_telemetry_response({'sensors':list(reversed(values)),'warnings':[{'name':'System Fan','health':1}]})
        self.assertEqual(set(a.sensors), set(b.sensors))
        self.assertEqual(a.warnings, ('System Fan',))
        self.assertIn(600, [r.value for r in a.sensors.values()])
        self.assertTrue(any(r.health == 1 for r in a.sensors.values()))

    def test_duplicate_names_get_unique_keys(self):
        metric={'name':'Temp','unit':'°C','value':20,'health':0}
        data=parse_telemetry_response({'sensors':[metric,metric], 'warnings':[]})
        self.assertEqual(len(data.sensors), 2)

    def test_invalid_entries_not_invented_as_zero(self):
        invalid=[
            {'name':'No Reading','unit':'RPM','value':None,'health':0},
            {'name':'Malformed','unit':'RPM','value':float('nan'),'health':0},
            {'name':'Negative??','unit':'°C','value':False,'health':0},
            {'name':'Invalid Unit','unit':'mph','value':42,'health':0},
            {'name':'newline\n','unit':'V','value':2,'health':0},
            {'name':'Bad Health','unit':'V','value':2,'health':123},
        ]
        data=parse_telemetry_response({'sensors':invalid,'warnings':[]})
        self.assertEqual(len(data.sensors), 0)

    def test_reject_malformed_and_oversized_payload(self):
        for payload in (
            {'sensors':{},'warnings':[]},
            {'sensors':[],'warnings':None},
            {'sensors':[{}]*97,'warnings':[]},
            {'sensors':[],'warnings':[{}]*97},
        ):
            with self.subTest(payload=list(payload)), self.assertRaises(TelemetryProtocolError):
                parse_telemetry_response(payload)

    def test_wrong_health_warnings_filtered(self):
        data=parse_telemetry_response({'sensors':[], 'warnings':[
            {'name':'System Fan','health':1},{'name':'System Fan','health':1},
            {'name':'Other','health':False},
            {'name':'\u0000','health':1}
        ]})
        self.assertEqual(data.warnings, ('System Fan',))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client=IpmiCoreClient('192.0.2.60',623,'operator','FAKE_PASSWORD')

    @patch('ipmi_core.client.subprocess.run')
    def test_read_only_action_and_serialized_worker(self, run):
        run.return_value=subprocess.CompletedProcess([],0,json.dumps({'ok':True,'sensors':[
            {'name':'System Temp','unit':'°C','value':27,'health':0}], 'warnings':[]}), '')
        data=self.client.get_telemetry()
        self.assertEqual(len(data.sensors),1)
        args, kwargs=run.call_args
        self.assertEqual(args[0][1],'-I')
        self.assertEqual(json.loads(kwargs['input'])['action'],'telemetry')
        self.assertEqual(kwargs['timeout'],12)
        self.assertNotIn('FAKE_PASSWORD', repr(args))

    @patch('ipmi_core.client.subprocess.run')
    def test_invalid_worker_output_fails_closed(self, run):
        run.return_value=subprocess.CompletedProcess([],0,'{"ok":true,"sensors":false,"warnings":[]}', '')
        with self.assertRaises(IpmiCoreError):
            self.client.get_telemetry()

    @patch('ipmi_core.client.subprocess.run')
    def test_child_timeout_fails_closed(self, run):
        run.side_effect=subprocess.TimeoutExpired(['python','worker'],12)
        with self.assertRaises(IpmiCoreError):
            self.client.get_telemetry()


if __name__ == '__main__':
    unittest.main()
