"""Explicit bounded KRig certificate-policy probe against a local test server.

No work/jobs are supplied and no trust roots are installed. This probes chain
rejection only; hostname validation remains a separate gate. Never run it while
another heavy GPU workload is active, because the vendor may initialize CUDA.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit
from payout_policy import fetch, remaining_seconds
from run_guarded import run, write_json, manual_cancel_token

KRIG_SHA256='61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f'

def classify(state):
    if state.get('client_payload_bytes',0)>0:return 'accepted-untrusted-certificate'
    alerts=' '.join(state.get('server_errors',[])).lower()
    explicit=any(x in alerts for x in ('alert_unknown_ca','alert_bad_certificate','alert_certificate_unknown'))
    if explicit:return 'rejected-untrusted-certificate'
    return 'inconclusive'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',required=True);p.add_argument('--config',required=True)
    p.add_argument('--output',required=True);p.add_argument('--deadline-state',required=True)
    p.add_argument('--seconds',type=int,default=35)
    a=p.parse_args()
    initial_cancel=manual_cancel_token()
    if os.name!='nt':p.error('Windows workstation only; no GPU or certificate action taken')
    if not 20<=a.seconds<=60:p.error('Certificate probe is limited to 20..60 seconds')
    binary=Path(a.binary).resolve(strict=True)
    with binary.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=KRIG_SHA256:raise ValueError('Expected pinned KRig 1.5.12 binary')
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8-sig'))
    pool=urlsplit(cfg['pool'])
    if pool.scheme!='stratum+ssl' or pool.hostname!='prl-hk.kryptex.network' or pool.port!=8048:raise ValueError('Expected original TLS pool configuration')
    if remaining_seconds(a.deadline_state)<a.seconds:raise RuntimeError('Original experience budget is insufficient; no process started')
    if fetch(cfg['wallet'])['goal_reached']:raise RuntimeError('First payout goal already reached; no process started')
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    state={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Local self-signed chain-rejection probe only; no jobs, shares, revenue, private wallet keys or trust-store changes','hostname_policy':'not tested by this probe','tls_handshakes':0,'client_payload_bytes':0,'server_errors':[]}
    openssl=Path('D:/Apps/Git/usr/bin/openssl.exe')
    if not openssl.is_file():raise RuntimeError('Existing OpenSSL CLI is required')
    stop=threading.Event();server=socket.socket();server.bind(('127.0.0.1',0));server.listen(2);server.settimeout(.5)
    port=server.getsockname()[1]
    try:
        with tempfile.TemporaryDirectory(prefix='local-cert-',dir=out) as td:
            root=Path(td);cert=root/'cert.pem';key=root/'key.pem'
            subprocess.run([str(openssl),'req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(key),'-out',str(cert),'-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True,timeout=20,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
            def serve():
                while not stop.is_set():
                    try:conn,_=server.accept()
                    except socket.timeout:continue
                    except OSError:return
                    try:
                        conn.settimeout(5)
                        with context.wrap_socket(conn,server_side=True) as tls:
                            state['tls_handshakes']+=1
                            state['client_payload_bytes']+=len(tls.recv(65536))
                            if state['client_payload_bytes']:(out/'stop.request').touch()
                    except (ssl.SSLError,OSError) as exc:state['server_errors'].append(type(exc).__name__+': '+str(exc))
                    finally:conn.close()
            thread=threading.Thread(target=serve,name='local-certificate-policy-probe',daemon=True);thread.start()
            try:
                command=[str(binary),'--coin','pearl','--url',f'stratum+ssl://localhost:{port}','--user',cfg['wallet']+'/'+cfg['worker'],'--devices-pci','01:00.0','--no-rocm','--no-intel','--no-tui','--log-level','info']
                code=run(SimpleNamespace(command=command,output=str(out),seconds=a.seconds,power=220,initial_manual_cancel=initial_cancel))
            finally:
                stop.set();server.close();thread.join(timeout=8)
            state.update(result=classify(state),guard_exit_code=code,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            write_json(out/'certificate-policy-result.json',state)
            print(json.dumps(state))
            return 0 if state['result']=='rejected-untrusted-certificate' and code==0 else 2 if state['result']=='accepted-untrusted-certificate' else 1
    finally:
        stop.set();server.close()

if __name__=='__main__':raise SystemExit(main())
