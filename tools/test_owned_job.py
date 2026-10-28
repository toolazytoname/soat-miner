"""Real Windows process ownership tests; CPU sleep children only, no GPU."""
import json,os,pathlib,subprocess,sys,tempfile,time,unittest
from owned_job import OwnedJob
class JobTests(unittest.TestCase):
 def test_inherited_child_is_owned_and_stopped_without_touching_outside(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);marker=td/"child.json"
   code="import subprocess,sys,time,json,pathlib; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path(sys.argv[1]).write_text(json.dumps({'child':p.pid}));time.sleep(60)"
   outside=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],creationflags=subprocess.CREATE_NO_WINDOW)
   try:
    with OwnedJob([sys.executable,"-c",code,str(marker)],td/"job.log") as job:
     end=time.monotonic()+5
     while not marker.exists() and time.monotonic()<end:time.sleep(.05)
     self.assertTrue(marker.exists(),(td/"job.log").read_text(errors="replace"))
     child=json.loads(marker.read_text())["child"]
     self.assertTrue(job.contains(job.pid));self.assertTrue(job.contains(child));self.assertFalse(job.contains(outside.pid));self.assertGreaterEqual(job.active_count(),2)
     job.stop();self.assertEqual(job.active_count(),0);self.assertIsNotNone(job.poll());self.assertIsNone(outside.poll())
   finally:outside.terminate();outside.wait(timeout=5)
 def test_normal_exit_keeps_real_exit_code(self):
  with tempfile.TemporaryDirectory() as td:
   env=os.environ.copy();env["PRL_JOB_TEST"]="round-trip"
   with OwnedJob([sys.executable,"-c","import os;print(os.environ['PRL_JOB_TEST']);raise SystemExit(7)"],pathlib.Path(td)/"log.txt",env=env) as job:
    end=time.monotonic()+5
    while job.poll() is None and time.monotonic()<end:time.sleep(.02)
    self.assertEqual(job.poll(),7);self.assertEqual(job.active_count(),0)
   self.assertEqual((pathlib.Path(td)/"log.txt").read_text().strip(),"round-trip")
if __name__=="__main__":unittest.main(verbosity=2)
