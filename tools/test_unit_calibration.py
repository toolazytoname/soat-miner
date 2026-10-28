"""CPU-only safety/protocol checks; no CUDA workload is started."""
import ctypes,json,os,pathlib,socket,struct,tempfile,time,unittest
from unittest.mock import patch
from run_unit_calibration import FixedJob,save
ROOT=pathlib.Path(__file__).resolve().parent.parent
class StatusPublication(unittest.TestCase):
    def test_transient_windows_reader_does_not_abort_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/"status.json";path.write_text('{"old":true}')
            original=pathlib.Path.replace;calls=[]
            def sometimes_busy(source,target):
                calls.append(1)
                if len(calls)<3:raise PermissionError("reader temporarily holds target")
                return original(source,target)
            with patch.object(pathlib.Path,"replace",sometimes_busy),patch("run_unit_calibration.time.sleep"):
                save(path,{"status":"running"})
            self.assertEqual(json.loads(path.read_text()),{"status":"running"})
            self.assertEqual(len(calls),3)
class MockContract(unittest.TestCase):
    def connect(self, mock):
        c=socket.create_connection(("127.0.0.1",mock.port),timeout=2);c.settimeout(2);return c
    def test_authorize_gets_infeasible_job(self):
        mock=FixedJob();mock.start()
        try:
            with self.connect(mock) as c:
                c.sendall(b'{"id":7,"method":"mining.authorize","params":{"wallet":"fixture"}}\n')
                f=c.makefile("rb");reply=json.loads(f.readline());job=json.loads(f.readline())
                self.assertEqual(reply,{"id":7,"result":True,"error":None})
                self.assertEqual(job["params"]["target"],"0"*63+"1")
                self.assertEqual(len(job["params"]["header"]),152)
                self.assertEqual(job["params"]["cert_version"],3)
            self.assertEqual(mock.errors,[])
        finally:mock.close()
    def test_unexpected_submit_never_credited(self):
        mock=FixedJob();mock.start()
        try:
            with self.connect(mock) as c:
                c.sendall(b'{"id":8,"method":"mining.submit","params":{}}\n')
                result=json.loads(c.makefile("rb").readline());self.assertFalse(result["result"]);self.assertIsNotNone(result["error"])
            self.assertIn("Unexpected submit against an infeasible target",mock.errors)
        finally:mock.close()
    def test_owned_child_tcp_reset_is_not_a_protocol_violation(self):
        mock=FixedJob();mock.start()
        try:
            c=self.connect(mock)
            c.sendall(b'{"id":7,"method":"mining.authorize","params":{}}\n')
            f=c.makefile("rb");f.readline();f.readline();f.close()
            c.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack("HH" if os.name=="nt" else "ii",1,0));c.close()
            mock.thread.join(timeout=2)
            self.assertFalse(mock.thread.is_alive());self.assertEqual(mock.errors,[])
        finally:mock.close()
    def test_unknown_handshake_is_failure(self):
        mock=FixedJob();mock.start()
        try:
            with self.connect(mock) as c:c.sendall(b'{"id":9,"method":"wallet.sign","params":{}}\n');c.recv(1024)
            mock.thread.join(timeout=2);self.assertTrue(any("Unsupported mock method" in x for x in mock.errors))
        finally:mock.close()
@unittest.skipUnless(os.name=="nt","Windows injection library")
class PassiveLibrary(unittest.TestCase):
    def setUp(self):
        self.directory=os.add_dll_directory("D:/Apps/CUPTI/13.1.115/lib")
        self.library=ctypes.WinDLL(str(ROOT/"build/cupti-trace/cuda-activity-trace.dll"));self.library.InitializeInjection.restype=ctypes.c_int
    def tearDown(self):self.directory.close()
    def test_without_configuration_is_inactive(self):
        # Run alone in its fresh process; one injection initialization per process.
        with patch.dict(os.environ,{},clear=False):
            os.environ.pop("SOAT_CUDA_TRACE_FILE",None);os.environ.pop("SOAT_CUDA_TRACE_SECONDS",None)
            self.assertEqual(self.library.InitializeInjection(),0)
if __name__=="__main__":unittest.main()
