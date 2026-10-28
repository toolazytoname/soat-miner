"""Fail-closed suite behavior with fake verifier receipts; no GPU/process work."""
import json,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import run_correctness_suite as c
class SuiteTests(unittest.TestCase):
 def run_case(self,mode):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);build=root/"build/prl3090-fold";build.mkdir(parents=True)
   for name in ["test-pearl-kernel-resources.exe","test-pearl-mining-shape.exe"]:(build/name).write_bytes(b"fixture, never run")
   calls=[]
   def run(cmd,**unused):
    calls.append(cmd);dest=pathlib.Path(cmd[cmd.index("--output")+1]);dest.mkdir(parents=True)
    guard={"child_exit_code":0,"stop_reason":"child-exited","power_restored":mode!="restore_failure"}
    (dest/"guard-status.json").write_text(json.dumps(guard))
    text='{"gpu":"fixture"}\n{"configuration":"fixture"}\n' if len(calls)==1 else "not a full-buffer validation"
    (dest/"child.log").write_text(text)
    return subprocess.CompletedProcess(cmd,1 if mode=="guard_failure" else 0)
   out=root/"out"
   with patch.object(c,"ROOT",root),patch.object(c,"CANCEL",root/"cancel.request"),patch.object(c.subprocess,"run",side_effect=run),patch.object(c.time,"sleep"),patch.object(sys,"argv",["test","--output",str(out)]):code=c.main()
   return code,json.loads((out/"result.json").read_text()),len(calls)
 def test_failed_guard_aborts_before_following_case(self):
  code,state,count=self.run_case("guard_failure");self.assertEqual(code,1);self.assertEqual(count,1);self.assertEqual(state["phase"],"failed")
 def test_missing_power_restore_aborts_before_following_case(self):
  code,state,count=self.run_case("restore_failure");self.assertEqual(code,1);self.assertEqual(count,1);self.assertIn("Verifier or guard failed",state["error"])
 def test_exit_zero_without_buffer_report_is_not_a_pass(self):
  code,state,count=self.run_case("missing_report");self.assertEqual(code,1);self.assertEqual(count,2);self.assertIn("Missing complete-buffer success report",state["error"])
if __name__=="__main__":unittest.main(verbosity=2)
