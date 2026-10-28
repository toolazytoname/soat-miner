"""Hardware-free cooldown faults: stale WDDM sample, new workload and manual stop."""
import pathlib,tempfile,unittest
from unittest.mock import Mock,patch
import run_thermal_comparison as c
class CoolingTests(unittest.TestCase):
 def run_cooling(self,read,processes=None,stop=False):
  clock=[0.0];g=Mock();g.read.side_effect=read
  with tempfile.TemporaryDirectory() as td,patch.object(c.time,"monotonic",side_effect=lambda:clock[0]),patch.object(c.time,"sleep",side_effect=lambda s:clock.__setitem__(0,clock[0]+s)),patch.object(c,"gpu_processes",return_value=processes or {}),patch.object(c,"new_stop",return_value=stop):
   return c.cooldown(pathlib.Path(td),g,None)
 def sample(self,util=0):return dict(Temperature=40,Hotspot=50,MemoryJunction=50,MemoryMiB=160,Utilization=util)
 def test_stale_wddm_sample_does_not_abort_cooldown(self):
  samples=[self.sample(99),self.sample(99)]+[self.sample() for _ in range(50)]
  result=self.run_cooling(samples);self.assertEqual(result["seconds"],180)
 def test_sustained_busy_gpu_aborts_without_start(self):
  with self.assertRaisesRegex(RuntimeError,"gpu_busy"):self.run_cooling([self.sample(99)]*3)
 def test_new_gpu_application_yields(self):
  with self.assertRaisesRegex(RuntimeError,"other_gpu_application"):self.run_cooling([self.sample()],{999999:"blender.exe"})
 def test_manual_stop_is_checked_before_gpu_poll(self):
  def should_not_poll():raise AssertionError("GPU was polled after manual stop")
  with self.assertRaisesRegex(RuntimeError,"manual_stop"):self.run_cooling(should_not_poll,stop=True)
if __name__=="__main__":unittest.main(verbosity=2)
