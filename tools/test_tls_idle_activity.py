"""CPU-only TLS fixture: traffic in either direction keeps an active relay alive."""
import argparse,importlib.util,pathlib,socket,socketserver,ssl,subprocess,tempfile,threading,time,unittest
parser=argparse.ArgumentParser(add_help=False);parser.add_argument("--relay",type=pathlib.Path);opts,rest=parser.parse_known_args()
source=opts.relay or pathlib.Path(__file__).with_name("tls_relay.py")
spec=importlib.util.spec_from_file_location("relay_under_test",source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);TlsRelay=module.TlsRelay
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with self.server.context.wrap_socket(self.request,server_side=True) as stream:
                stream.settimeout(2)
                if stream.recv(1)!=b"A":return
                self.server.activity_started.set()
                if self.server.mode=="heartbeats":
                    for _ in range(12):stream.sendall(b"H");time.sleep(.05)
                    if stream.recv(1)==b"B":stream.sendall(b"K")
                elif self.server.mode=="client-heartbeats":
                    for _ in range(12):
                        if stream.recv(1)!=b"H":return
                    stream.sendall(b"K")
                elif self.server.mode=="delayed-response":
                    time.sleep(.7);stream.sendall(b"K")
                else:time.sleep(.7)
        except (OSError,ssl.SSLError):pass
class SharedIdleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=pathlib.Path(cls.temp.name);cls.key=cls.root/"fixture.key";cls.cert=cls.root/"fixture.crt"
        command=["D:/Apps/Git/usr/bin/openssl.exe","req","-x509","-newkey","rsa:2048","-nodes","-keyout",str(cls.key),"-out",str(cls.cert),"-days","1","-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost"]
        r=subprocess.run(command,capture_output=True,timeout=15)
        if r.returncode:raise RuntimeError("Temporary TLS fixture generation failed")
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def server(self,mode):
        server=Server(("127.0.0.1",0),Handler);server.mode=mode;server.activity_started=threading.Event()
        server.context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server.context.load_cert_chain(self.cert,self.key)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        context=ssl.create_default_context(cafile=str(self.cert))
        return server,context
    def test_incoming_heartbeats_keep_silent_client_direction_open(self):
        server,context=self.server("heartbeats")
        with TlsRelay("localhost",server.server_address[1],context=context,idle_seconds=.2,receipt=self.root/(server.mode+"-receipt.json")) as relay:
            with socket.create_connection(("127.0.0.1",relay.local_port),timeout=2) as client:
                client.settimeout(5);client.sendall(b"A");self.assertTrue(server.activity_started.wait(5));data=b""
                while len(data)<12:
                    part=client.recv(12-len(data))
                    if not part:raise AssertionError("Active upstream traffic was cut off by the client-direction idle timer")
                    data+=part
                client.sendall(b"B");self.assertEqual(client.recv(1),b"K")
    def test_outgoing_heartbeats_keep_silent_server_direction_open(self):
        server,context=self.server("client-heartbeats")
        with TlsRelay("localhost",server.server_address[1],context=context,idle_seconds=.2,receipt=self.root/(server.mode+"-receipt.json")) as relay:
            with socket.create_connection(("127.0.0.1",relay.local_port),timeout=2) as client:
                client.settimeout(5);client.sendall(b"A");self.assertTrue(server.activity_started.wait(5))
                for _ in range(12):client.sendall(b"H");time.sleep(.05)
                self.assertEqual(client.recv(1),b"K")
    def test_legitimate_quiet_job_stays_connected_with_tcp_keepalive(self):
        server,context=self.server("delayed-response")
        with TlsRelay("localhost",server.server_address[1],context=context,idle_seconds=None,receipt=self.root/"quiet-job.json") as relay:
            with socket.create_connection(("127.0.0.1",relay.local_port),timeout=2) as client:
                client.settimeout(5);client.sendall(b"A");self.assertTrue(server.activity_started.wait(5))
                self.assertEqual(client.recv(1),b"K")
                self.assertTrue(relay.state["tcp_keepalive"]["enabled"])
                self.assertIsNone(relay.state["application_idle_seconds"])
    def test_invalid_application_idle_deadlines_are_rejected(self):
        for value in (0,-1,float("nan"),float("inf")):
            with self.subTest(value=value),self.assertRaises(ValueError):TlsRelay("localhost",8048,idle_seconds=value)
    def test_default_does_not_require_finding_a_share_before_idle_deadline(self):
        relay=TlsRelay("localhost",8048)
        self.assertIsNone(relay.idle_seconds)
    def test_both_directions_silent_still_time_out(self):
        server,context=self.server("silent")
        with TlsRelay("localhost",server.server_address[1],context=context,idle_seconds=.2,receipt=self.root/(server.mode+"-receipt.json")) as relay:
            with socket.create_connection(("127.0.0.1",relay.local_port),timeout=2) as client:
                client.settimeout(5);client.sendall(b"A");self.assertTrue(server.activity_started.wait(5));started=time.monotonic()
                self.assertEqual(client.recv(1),b"");self.assertLess(time.monotonic()-started,1.5)
if __name__=="__main__":unittest.main(argv=[__file__,*rest])
