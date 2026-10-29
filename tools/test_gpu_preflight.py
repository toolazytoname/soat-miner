"""Host-only startup load scenarios; no GPU process or power change."""
import unittest
from run_guarded import gpu_busy_before_start
class PreflightTests(unittest.TestCase):
    def sample(self,**changes):
        data=dict(Utilization=34,MemoryMiB=1091,Power=17.9,CoreClockMHz=225,MemoryClockMHz=405)
        data.update(changes);return data
    def test_observed_idle_desktop_percentage_is_not_a_compute_load(self):
        self.assertFalse(gpu_busy_before_start(self.sample()))
    def test_high_power_gpu_work_is_refused(self):
        self.assertTrue(gpu_busy_before_start(self.sample(Power=180,CoreClockMHz=1500,MemoryClockMHz=9501)))
    def test_low_power_alone_does_not_excuse_active_clocks(self):
        self.assertTrue(gpu_busy_before_start(self.sample(CoreClockMHz=900,MemoryClockMHz=9501)))
    def test_normal_low_utilization_keeps_existing_behavior(self):
        self.assertFalse(gpu_busy_before_start(self.sample(Utilization=2,CoreClockMHz=1000,MemoryClockMHz=9501)))
    def test_existing_memory_limits_are_preserved(self):
        self.assertTrue(gpu_busy_before_start(self.sample(Utilization=0,MemoryMiB=3000)))
        self.assertTrue(gpu_busy_before_start(self.sample(Utilization=0,MemoryMiB=2200),memory_limit=2048))
    def test_source_stricter_utilization_threshold_is_preserved(self):
        data=self.sample(Utilization=12,Power=100,CoreClockMHz=1000,MemoryClockMHz=9501)
        self.assertFalse(gpu_busy_before_start(data))
        self.assertTrue(gpu_busy_before_start(data,utilization_limit=10,memory_limit=2048))
    def test_missing_or_invalid_busy_state_fails_closed(self):
        for key in ("Power","CoreClockMHz","MemoryClockMHz"):
            data=self.sample();data.pop(key)
            with self.subTest(key=key):self.assertTrue(gpu_busy_before_start(data))
        for key in ("Utilization","MemoryMiB","Power","CoreClockMHz","MemoryClockMHz"):
            for value in (float("nan"),-1,True):
                with self.subTest(key=key,value=value):self.assertTrue(gpu_busy_before_start(self.sample(**{key:value})))
    def test_high_percentage_with_only_part_of_idle_conditions_is_refused(self):
        for change in (dict(Power=60),dict(CoreClockMHz=800),dict(MemoryClockMHz=9501)):
            with self.subTest(change=change):self.assertTrue(gpu_busy_before_start(self.sample(**change)))
class ExperimentStartupWaitTests(unittest.TestCase):
    def reading(self, **changes):
        sample=dict(Utilization=37,MemoryMiB=1113,Power=19.96,
                    CoreClockMHz=450,MemoryClockMHz=810,PowerLimit=370,
                    Temperature=40,Hotspot=50,MemoryJunction=44)
        sample.update(changes)
        return sample
    def exercise(self, readings, *, processes=None, tokens=None, ticks=None):
        from contextlib import ExitStack
        from pathlib import Path
        from unittest.mock import Mock,patch
        from run_guarded import wait_for_idle_gpu
        gpu=Mock();gpu.read.side_effect=readings
        with ExitStack() as stack:
            stack.enter_context(patch("run_guarded.gpu_processes",return_value=processes or {}))
            stack.enter_context(patch("run_guarded.manual_cancel_token",side_effect=tokens or [None]*10))
            stack.enter_context(patch("run_guarded.Path.exists",return_value=False))
            sleep=stack.enter_context(patch("run_guarded.time.sleep"))
            if ticks is not None:stack.enter_context(patch("run_guarded.time.monotonic",side_effect=ticks))
            result=wait_for_idle_gpu(gpu,Path("unused-host-fixture"),None)
            gpu.power.assert_not_called()
            return result,sleep.call_count
    def test_transient_desktop_sample_waits_then_returns_idle(self):
        result,sleeps=self.exercise([self.reading(),self.reading(CoreClockMHz=240)])
        self.assertEqual(result[0]["CoreClockMHz"],240);self.assertEqual(sleeps,1)
    def test_persistent_gpu_work_has_bounded_timeout(self):
        with self.assertRaisesRegex(RuntimeError,"GPU is busy"):
            self.exercise([self.reading()],ticks=[0,31])
    def test_manual_cancel_is_checked_during_wait(self):
        with self.assertRaisesRegex(RuntimeError,"Manual stop"):
            self.exercise([self.reading()],tokens=[None,(123,0)])
    def test_incoming_gpu_application_ends_preflight(self):
        with self.assertRaisesRegex(RuntimeError,"Another GPU application"):
            self.exercise([self.reading(CoreClockMHz=240)],processes={99999:"blender.exe"})
    def test_thermal_fault_does_not_wait_for_idle(self):
        with self.assertRaisesRegex(RuntimeError,"thermal_Hotspot"):
            self.exercise([self.reading(Hotspot=101)])
    def test_invalid_original_power_limit_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"Invalid original GPU power limit"):
            self.exercise([self.reading(PowerLimit=float("nan"))])
if __name__=="__main__":unittest.main(verbosity=2)
