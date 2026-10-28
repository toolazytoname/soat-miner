"""Local TLS transport checks. Test keys are temporary and never user keys."""
import json
import os
from pathlib import Path
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from tls_relay import TlsRelay


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with self.server.context.wrap_socket(self.request,server_side=True) as stream:
                data=stream.recv(65536)
                self.server.received.append(data)
                if data: stream.sendall(data)
        except (ssl.SSLError,ConnectionError,OSError):
            pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True


class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        openssl=os.environ.get('PEARL_TEST_OPENSSL','D:/Apps/Git/usr/bin/openssl.exe')
        if not Path(openssl).is_file():raise unittest.SkipTest('OpenSSL CLI needed for temporary local test certificate')
        cls.tmp=tempfile.TemporaryDirectory(dir=os.environ.get('PEARL_GUARD_TEST_ROOT'))
        cls.root=Path(cls.tmp.name);cls.cert=cls.root/'test-cert.pem';key=cls.root/'test-key.pem'
        subprocess.run([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-days','2',
                        '-keyout',str(key),'-out',str(cls.cert),'-subj','/CN=localhost',
                        '-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True,timeout=20)
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cls.cert,key)
        cls.server=Server(('127.0.0.1',0),Echo);cls.server.context=ctx;cls.server.received=[]
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.tmp.cleanup()
    def context(self):
        return ssl.create_default_context(cafile=str(self.cert))
    def exchange(self,relay,data=b'local-transport-test\n'):
        with socket.create_connection(('127.0.0.1',relay.local_port),timeout=5) as sock:
            sock.sendall(data)
            try:return sock.recv(65536)
            except (ConnectionResetError,ConnectionAbortedError):return b''
    def test_valid_certificate_and_hostname_forward_bytes(self):
        receipt=self.root/'valid-relay.json'
        with TlsRelay('localhost',self.port,context=self.context(),receipt=receipt) as relay:
            self.assertEqual(self.exchange(relay),b'local-transport-test\n')
        self.assertFalse(relay.thread.is_alive())
        state=json.loads(receipt.read_text());self.assertEqual(state['verified_sessions'],1)
        self.assertEqual(state['status'],'stopped');self.assertEqual(state['bind'],'127.0.0.1')
    def test_untrusted_certificate_forwards_no_payload(self):
        before=len(self.server.received)
        with TlsRelay('localhost',self.port) as relay:
            self.assertEqual(self.exchange(relay),b'')
        self.assertEqual(relay.state['verified_sessions'],0)
        self.assertEqual(relay.state['failed_sessions'],1)
        self.assertIn('SSLCertVerificationError',relay.state['last_error'])
        self.assertEqual(len(self.server.received),before)
    def test_hostname_mismatch_forwards_no_payload(self):
        before=len(self.server.received)
        with TlsRelay('127.0.0.1',self.port,context=self.context()) as relay:
            self.assertEqual(self.exchange(relay),b'')
        self.assertEqual(relay.state['verified_sessions'],0)
        self.assertIn('SSLCertVerificationError',relay.state['last_error'])
        self.assertEqual(len(self.server.received),before)
    def test_verification_cannot_be_disabled(self):
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
        with self.assertRaisesRegex(ValueError,'mandatory'):
            TlsRelay('localhost',self.port,context=ctx)

if __name__=='__main__':unittest.main(verbosity=2)
