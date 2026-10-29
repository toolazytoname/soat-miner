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
if __name__=="__main__":unittest.main(verbosity=2)
