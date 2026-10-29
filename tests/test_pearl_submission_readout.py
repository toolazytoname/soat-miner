"""Offline loopback protocol/readout checks; dummy proof only, no PoW or GPU."""
import json,os,pathlib,socket,subprocess,threading,unittest
from test_pearl_pool_buffered import ACK,notify,wire
EXE=pathlib.Path(os.environ.get("SOAT_POOL_TEST_EXE",str(pathlib.Path(__file__).resolve().parent.parent/"build/prl3090-submission-stats"/("test-pearl-pool.exe" if os.name=="nt" else "test-pearl-pool"))))
class SubmissionReadoutTests(unittest.TestCase):
    def probe(self,mode):
        run=subprocess.run([str(EXE),"--readout-probe",mode],capture_output=True,text=True,timeout=5)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        return json.loads(run.stdout)
    def exchange(self,replies,mode="--submit-loopback"):
        listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1);listener.settimeout(10)
        port=listener.getsockname()[1];errors=[];requests=[]
        def serve():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(10)
                    file=peer.makefile("rwb",buffering=0)
                    auth=json.loads(file.readline())
                    if auth["method"]!="mining.authorize":raise AssertionError("Wrong authorize")
                    peer.sendall(wire([ACK,notify("fixture-current")]))
                    for reply in replies:
                        raw=file.readline()
                        if not raw:break
                        request=json.loads(raw);requests.append(request)
                        if request["method"]!="mining.submit":raise AssertionError("Wrong method")
                        if reply is None:return
                        peer.sendall(wire([dict(id=request["id"],result=reply,error=None if reply else {"code":23,"msg":"fixture rejection"})]))
            except BaseException as exc:errors.append(str(exc))
            finally:listener.close()
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        run=subprocess.run([str(EXE),mode,str(port)],capture_output=True,text=True,timeout=12)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        return json.loads(run.stdout),requests
    def test_explicit_pool_rejection_updates_failed_count(self):
        row,requests=self.exchange([False])
        self.assertEqual(len(requests),1);self.assertFalse(row["submitted"])
        self.assertEqual(row["accepted"],0);self.assertEqual(row["failed"],1)
    def test_accepted_reply_does_not_increment_failures(self):
        row,requests=self.exchange([True])
        self.assertTrue(row["submitted"]);self.assertEqual(row["accepted"],1);self.assertEqual(row["failed"],0)
    def test_sync_acceptance_survives_a_later_rejection(self):
        row,requests=self.exchange([True,False],mode="--submit-pair-loopback")
        self.assertEqual(len(requests),2);self.assertEqual(row["accepted"],1);self.assertEqual(row["failed"],1)
    def test_obsolete_job_is_counted_locally_and_never_sent(self):
        row,requests=self.exchange([False],mode="--submit-stale-loopback")
        self.assertFalse(requests);self.assertIn("proof not sent",row["error"])
        self.assertEqual(row["failed"],1);self.assertEqual(row["accepted"],0)
    def test_no_reply_is_a_client_failure_not_an_acceptance(self):
        row,requests=self.exchange([None])
        self.assertEqual(len(requests),1);self.assertIn("no reply",row["error"])
        self.assertEqual(row["failed"],1);self.assertEqual(row["accepted"],0)
    def test_benchmark_host_verification_failure_is_visible(self):
        self.assertEqual(self.probe("benchmark"),{"accepted":0,"failed":2})
    def test_sync_source_preserves_acceptance_and_fills_local_failures(self):
        self.assertEqual(self.probe("sync"),{"accepted":11,"failed":2})
    def test_async_pool_counts_and_local_failures_are_not_double_added(self):
        self.assertEqual(self.probe("async"),{"accepted":7,"failed":5})
if __name__=="__main__":unittest.main(verbosity=2)
