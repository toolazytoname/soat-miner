"""Host-only tests for the GPU experiment guard: no real GPU calls or child jobs."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import run_guarded as guard


class FakeGpu:
    def __init__(self, hot=False, busy=False):
        self.limit=370
        self.calls=[]
        self.reads=0
        self.hot=hot
        self.busy=busy
    def read(self):
        self.reads+=1
        return dict(PowerLimit=self.limit, Temperature=40, Hotspot=101 if self.hot and self.reads==2 else 50,
                    MemoryJunction=50, MemoryMiB=512, Utilization=80 if self.busy else 0)
    def power(self, watts):
        self.calls.append(watts)
        self.limit=watts


class FakeChild:
    pid=991
    def __init__(self, code=None): self.returncode=code
    def poll(self): return self.returncode


@unittest.skipUnless(os.name=='nt', 'Windows guard')
class GuardTests(unittest.TestCase):
    def setUp(self):
        base=os.environ.get('PEARL_GUARD_TEST_ROOT')
        self.tmp=tempfile.TemporaryDirectory(dir=base)
        self.root=Path(self.tmp.name)
        executable=self.root/'fake-child.txt'
        executable.write_text('test fixture; never executed')
        self.args=argparse.Namespace(command=[str(executable)], output=str(self.root/'run'),seconds=1,power=220)
    def tearDown(self): self.tmp.cleanup()
    def status(self): return json.loads((Path(self.args.output)/'guard-status.json').read_text())
    def run_case(self, gpu, child=None, failure=None, incoming=False, manual=False):
        child=child or FakeChild()
        def launch(*_args,**_kwargs):
            if failure: raise failure
            if manual: (Path(self.args.output)/'stop.request').touch()
            return child
        def stop(proc):
            self.assertIs(proc,child)
            child.returncode=0
            return 'test-owned-child-stop'
        pids=[{1:'dwm.exe'},{1:'dwm.exe',777:'other-engine.exe'}] if incoming else None
        with patch.object(guard,'MiningLease',return_value=contextlib.nullcontext()), patch.object(guard,'Gpu',return_value=gpu), patch.object(guard.subprocess,'Popen',side_effect=launch) as popen, patch.object(guard,'stop_owned',side_effect=stop), patch.object(guard,'gpu_processes',side_effect=pids,return_value={}), patch.object(guard.time,'sleep'):
            return guard.run(self.args),popen
    def test_busy_gpu_never_changes_power_or_starts_child(self):
        gpu=FakeGpu(busy=True)
        with self.assertRaisesRegex(RuntimeError,'GPU is busy'):
            self.run_case(gpu)
        self.assertEqual(gpu.calls,[])
        self.assertFalse((Path(self.args.output)/'child.log').exists())
    def test_failed_child_launch_restores_power(self):
        gpu=FakeGpu()
        with self.assertRaisesRegex(OSError,'test spawn failure'):
            self.run_case(gpu,failure=OSError('test spawn failure'))
        self.assertEqual(gpu.calls,[220,370])
        self.assertTrue(self.status()['power_restored'])
    def test_normal_child_exit_restores_power(self):
        gpu=FakeGpu()
        code,_=self.run_case(gpu,FakeChild(code=0))
        self.assertEqual(code,0)
        self.assertEqual(gpu.calls,[220,370])
        self.assertEqual(self.status()['stop_reason'],'child-exited')
    def test_hotspot_stops_only_owned_child_and_restores(self):
        gpu=FakeGpu(hot=True)
        code,_=self.run_case(gpu)
        self.assertEqual(code,1)
        self.assertTrue(self.status()['stop_reason'].startswith('thermal_Hotspot_'))
        self.assertTrue(self.status()['power_restored'])
        data=(Path(self.args.output)/'telemetry.jsonl').read_text().splitlines()
        self.assertEqual(len(data),1)
        self.assertEqual(json.loads(data[0])['Hotspot'],101)
    def test_manual_stop_request_restores_power(self):
        gpu=FakeGpu()
        code,_=self.run_case(gpu,manual=True)
        self.assertEqual(code,0)
        self.assertEqual(self.status()['stop_reason'],'manual-stop')
        self.assertTrue(self.status()['power_restored'])
    def test_new_gpu_work_yields_without_stopping_that_process(self):
        gpu=FakeGpu()
        code,_=self.run_case(gpu,incoming=True)
        self.assertEqual(code,1)
        self.assertEqual(self.status()['stop_reason'],'other-gpu-process')
        self.assertTrue(self.status()['power_restored'])

    def test_existing_idle_engine_is_not_taken_over(self):
        gpu=FakeGpu()
        with patch.object(guard,'MiningLease',return_value=contextlib.nullcontext()), patch.object(guard,'Gpu',return_value=gpu), patch.object(guard,'gpu_processes',return_value={777:'other-engine.exe'}), patch.object(guard.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(RuntimeError,'Another GPU application'):
                guard.run(self.args)
            popen.assert_not_called()
        self.assertEqual(gpu.calls,[])
    def test_external_power_change_is_preserved(self):
        class ExternalGpu(FakeGpu):
            def read(self):
                if self.reads>=1: self.limit=180
                return super().read()
        gpu=ExternalGpu()
        with self.assertRaisesRegex(RuntimeError,'not restored'):
            self.run_case(gpu)
        self.assertEqual(gpu.calls,[220])
        self.assertEqual(gpu.limit,180)
        self.assertEqual(self.status()['stop_reason'],'external-power-change')
        self.assertEqual(self.status()['external_power_preserved'],180)
    def test_protected_process_name_uses_pid_snapshot(self):
        from types import SimpleNamespace
        result=SimpleNamespace(returncode=0,stdout='123, [Insufficient Permissions]\n456, [Not Found]\n')
        with patch.object(guard.subprocess,'run',return_value=result),patch.object(guard,'process_names',return_value={123:'dwm.exe',456:'other-engine.exe'}):
            self.assertEqual(guard.gpu_processes(),{123:'dwm.exe',456:'other-engine.exe'})

    def test_invalid_limits_do_not_touch_gpu(self):
        self.args.power=370
        with patch.object(guard,'Gpu') as gpu:
            with self.assertRaisesRegex(ValueError,'100..220'):
                guard.run(self.args)
            gpu.assert_not_called()
    def test_lease_blocks_second_process(self):
        with guard.MiningLease():
            code='import sys;sys.path.insert(0,sys.argv[1]);from run_guarded import MiningLease\nwith MiningLease(): pass'
            result=guard.subprocess.run([sys.executable,'-c',code,str(Path(guard.__file__).parent)],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('owns the GPU',result.stderr)

if __name__=='__main__': unittest.main(verbosity=2)
