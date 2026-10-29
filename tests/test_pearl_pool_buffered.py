"""CPU-only public socket checks: coalesced auth/pushes must not await a new packet."""
import json,os,pathlib,socket,subprocess,threading,time,unittest
EXE=pathlib.Path(os.environ.get("SOAT_POOL_TEST_EXE","build/prl3090-warpwide/test-pearl-pool.exe"))
ACK={"id":1,"error":None,"result":True}
def notify(job_id,header=None):
    return {"id":None,"method":"mining.notify","params":{"job_id":job_id,"header":"00"*76 if header is None else header,"target":"ff"*32,"cert_version":3}}
def wire(messages):return b"".join(json.dumps(x,separators=(",",":")).encode()+b"\n" for x in messages)
class BufferedPoolTests(unittest.TestCase):
    def exchange(self,batches,close_after=False):
        listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1);listener.settimeout(12)
        port=listener.getsockname()[1];release=threading.Event();errors=[]
        def server():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(12);peer.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                    request=b""
                    while not request.endswith(b"\n"):
                        part=peer.recv(4096)
                        if not part:raise EOFError("CPU client closed before authorize")
                        request+=part
                    auth=json.loads(request)
                    if auth.get("method")!="mining.authorize":raise AssertionError("Expected public authorize request")
                    for delay,messages in batches:
                        if delay:time.sleep(delay)
                        peer.sendall(wire(messages))
                    if close_after:return
                    release.wait(11)
            except BaseException as exc:errors.append(str(exc))
            finally:listener.close()
        thread=threading.Thread(target=server,daemon=True);thread.start();start=time.monotonic()
        try:result=subprocess.run([str(EXE),"--fetch-loopback",str(port)],capture_output=True,text=True,timeout=11)
        finally:release.set();thread.join(timeout=2)
        self.assertFalse(thread.is_alive(),"CPU loopback server did not stop");self.assertFalse(errors,errors)
        return result,json.loads(result.stdout.strip()),time.monotonic()-start
    def test_ack_and_first_job_in_one_packet_are_immediately_usable(self):
        result,row,elapsed=self.exchange([(0,[ACK,notify("first")])])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(row["job_id"],"first");self.assertLess(elapsed,2)
    def test_all_coalesced_jobs_are_drained_and_latest_wins(self):
        result,row,elapsed=self.exchange([(0,[ACK,notify("older"),notify("latest")])])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(row["job_id"],"latest");self.assertLess(elapsed,2)
    def test_notify_before_auth_ack_is_retained(self):
        result,row,elapsed=self.exchange([(0,[notify("before"),ACK])])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(row["job_id"],"before");self.assertLess(elapsed,2)
    def test_delayed_job_still_waits_for_socket_data(self):
        result,row,elapsed=self.exchange([(0,[ACK]),(.05,[notify("delayed")])])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(row["job_id"],"delayed");self.assertLess(elapsed,2)
    def test_malformed_job_is_never_promoted(self):
        result,row,_=self.exchange([(0,[ACK,notify("bad",header="invalid")])],close_after=True)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr);self.assertFalse(row["valid"])
if __name__=="__main__":unittest.main(verbosity=2)
