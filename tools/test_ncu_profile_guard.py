"""Fault injection for profiler cleanup. No real GPU/process is started."""
import contextlib,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import run_ncu_profile as p
class FakeGpu:
 def __init__(self,mode):self.mode=mode;self.limit=370;self.reads=0;self.powers=[]
 def read(self):
  self.reads+=1
  if self.mode=="sensor_error" and self.reads==2:raise RuntimeError("sensor failure")
  if self.mode=="external_power" and self.reads==2:self.limit=200
  return {"PowerLimit":self.limit,"Temperature":80 if self.mode=="thermal" and self.reads>=2 else 40,"Hotspot":float("nan") if self.mode=="invalid_sensor" and self.reads==2 else 50,"MemoryJunction":50,"Utilization":0,"MemoryMiB":160}
 def power(self,value):self.powers.append(value);self.limit=value
class FakeJob:
 def __init__(self,*unused,**kwargs):self.pid=333;self.stops=0;self.closed=False
 def active_count(self):return 1
 def contains(self,pid):return pid==333
 def stop(self):self.stops+=1
 def poll(self):return 1
 def close(self):self.closed=True
class ProfileTests(unittest.TestCase):
 def run_case(self,mode):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);binary=root/"build/prl3090-fixed/soat-miner.exe";binary.parent.mkdir(parents=True);binary.write_bytes(b"fixture, never executed")
   ncu=root/"ncu.exe";ncu.write_bytes(b"fixture, never executed");receipt=root/"receipt.json";receipt.write_text(json.dumps({"ncu":str(ncu)}));out=root/"out";out.mkdir()
   if mode=="manual":(out/"stop.request").touch()
   gpu=FakeGpu(mode);jobs=[];calls=[0]
   def clients():
    calls[0]+=1
    return {444:"blender.exe"} if mode=="new_gpu" and calls[0]>1 else {}
   def create(*args,**kwargs):job=FakeJob();jobs.append(job);return job
   with patch.object(p,"ROOT",root),patch.object(p,"NCU_RECEIPT",receipt),patch.object(p,"MiningLease",return_value=contextlib.nullcontext()),patch.object(p,"Gpu",return_value=gpu),patch.object(p,"OwnedJob",side_effect=create),patch.object(p,"gpu_processes",side_effect=clients),patch.object(p.signal,"signal"),patch.object(p.time,"sleep"),patch.object(sys,"argv",["test","--output",str(out),"--seconds","15"]):
    code=p.main()
   return code,json.loads((out/"profile-status.json").read_text()),gpu,jobs
 def test_thermal_stop_kills_owned_job_and_restores(self):
  code,s,g,j=self.run_case("thermal");self.assertEqual(code,1);self.assertEqual(s["stop_reason"],"thermal_guard");self.assertTrue(s["power_restored"]);self.assertEqual(g.powers,[220,370]);self.assertTrue(j[0].closed)
 def test_new_gpu_only_stops_our_job(self):
  _,s,g,j=self.run_case("new_gpu");self.assertEqual(s["stop_reason"],"other_gpu_application");self.assertTrue(j[0].closed);self.assertTrue(s["power_restored"])
 def test_external_power_change_is_preserved(self):
  _,s,g,j=self.run_case("external_power");self.assertEqual(s["stop_reason"],"external_power_change");self.assertEqual(g.powers,[220]);self.assertEqual(s["external_power_change_preserved"],200);self.assertTrue(j[0].closed)
 def test_manual_stop_before_launch_does_not_touch_power(self):
  _,s,g,j=self.run_case("manual");self.assertEqual(g.powers,[]);self.assertEqual(j,[]);self.assertIn("manual_stop_before_profile",s["error"])
 def test_non_finite_sensor_fails_closed(self):
  _,s,g,j=self.run_case("invalid_sensor");self.assertEqual(s["status"],"failed");self.assertIn("invalid_gpu_telemetry",s["error"]);self.assertTrue(j[0].closed);self.assertTrue(s["power_restored"])
 def test_sensor_failure_cleans_up_owned_children_and_power(self):
  _,s,g,j=self.run_case("sensor_error");self.assertEqual(s["status"],"failed");self.assertIn("sensor failure",s["error"]);self.assertTrue(j[0].closed);self.assertTrue(s["power_restored"]);self.assertEqual(g.powers,[220,370])
if __name__=="__main__":unittest.main(verbosity=2)
