"""CPU-only fake-driver regression: initialization must not depend on assert."""
import types,unittest
from unittest.mock import Mock,patch
import gpu_telemetry as driver
class FakeGpu(driver.Gpu):
    def __init__(self,init_code=0,enum_code=0,gpu_count=1,sensor_bits=10):
        self.events=[];self.init_code=init_code;self.enum_code=enum_code
        self.gpu_count=gpu_count;self.sensor_bits=sensor_bits
        with patch.object(driver.c,"WinDLL",return_value=types.SimpleNamespace(nvapi_QueryInterface=Mock())):
            super().__init__()
    def fn(self,ident,args):
        if ident==0x0150E828:
            def initialize():
                self.events.append("initialize")
                return self.init_code
            return initialize
        if ident==0xE5AC921F:
            def enumerate_gpus(handles,count):
                self.events.append("enumerate")
                handles[0]=123
                count._obj.value=self.gpu_count
                return self.enum_code
            return enumerate_gpus
        if ident==0x65FE3AAD:
            def thermal(handle,sensor):
                t=sensor._obj
                if handle!=123:return -1
                if t.mask>=(1<<self.sensor_bits):return -1
                for i,value in [(0,70),(1,85),(9,82)]:t.temperatures[i]=value*256
                return 0
            return thermal
        raise RuntimeError("Unexpected driver interface")
class InitializationTests(unittest.TestCase):
    def test_required_initialization_calls_execute_in_this_interpreter_mode(self):
        gpu=FakeGpu()
        self.assertEqual(gpu.events,["initialize","enumerate"])
        self.assertEqual(gpu.handle,123)
        self.assertTrue(gpu.mask&512)
    def test_init_failure_refuses_to_enumerate(self):
        with self.assertRaisesRegex(RuntimeError,"NVAPI initialization failed"):FakeGpu(init_code=-1)
    def test_enumeration_error_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Expected one NVIDIA GPU"):FakeGpu(enum_code=-1)
    def test_no_gpu_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Expected one NVIDIA GPU"):FakeGpu(gpu_count=0)
    def test_multiple_gpus_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Expected one NVIDIA GPU"):FakeGpu(gpu_count=2)
    def test_missing_junction_sensor_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Memory junction sensor"):FakeGpu(sensor_bits=9)
    def test_initialized_read_is_read_only(self):
        gpu=FakeGpu()
        result=types.SimpleNamespace(returncode=0,stdout="220,70,219.8,99,1200,48,1200,9501",stderr="")
        with patch.object(driver.subprocess,"run",return_value=result) as run:
            reading=gpu.read()
        self.assertEqual(reading["Hotspot"],85)
        self.assertEqual(reading["MemoryJunction"],82)
        self.assertEqual(len(run.call_args_list),1)
        command=run.call_args.args[0]
        self.assertTrue(any(v.startswith("--query-gpu=") for v in command))
        self.assertNotIn("-pl",command)
if __name__=="__main__":unittest.main(verbosity=2)
