"""Bounded real CUDA miner / loopback mock: work -> 50 s no job -> work.

Run elevated on the logged-in Windows desktop, after stopping other GPU work.
This never contacts a real pool or credits shares; its target is deliberately
infeasible. The existing run_guarded lease/thermal/manual-stop/power guard owns
the exact miner child. The mock only retires work via an invalid notify, which
must not be mined. Never use a successful mock as evidence of pool earnings.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import threading
import time
from types import SimpleNamespace

from run_guarded import run, write_json


def records(path):
    if not path.exists():
        return []
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 65536))
        lines = stream.read().decode('utf-8', errors='replace').splitlines()
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get('algo') == 'pearl-pow' and 'rate' in row:
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    exe = Path(args.exe).resolve(strict=True)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    guard = out / 'guard'
    guard.mkdir()
    log = guard / 'child.log'
    state = {'scope': 'loopback mock; CUDA work, no paid shares or external pool',
             'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'errors': [], 'zero_samples': []}
    done = threading.Event()
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    server.settimeout(45)
    port = server.getsockname()[1]

    def send(conn, payload):
        conn.sendall((json.dumps(payload) + '\n').encode())

    def job(conn, tag, byte):
        send(conn, {'id': None, 'method': 'mining.notify', 'params': {
            'job_id': tag, 'header': byte * 76, 'target': '0' * 63 + '1',
            'height': 1, 'cert_version': 3}})

    def await_positive(after_uptime=-1):
        until = time.monotonic() + 40
        while not done.is_set() and time.monotonic() < until:
            for row in reversed(records(log)):
                if row.get('rate', 0) > 10 and row.get('uptime_s', -1) > after_uptime:
                    return row
            time.sleep(0.2)
        raise RuntimeError('No fresh positive CUDA statistics within 40 seconds')

    def serve():
        try:
            with server:
                conn, peer = server.accept()
                with conn:
                    if peer[0] != '127.0.0.1':
                        raise RuntimeError('Mock accepted a non-loopback client')
                    conn.settimeout(15)
                    data = b''
                    while b'\n' not in data:
                        part = conn.recv(4096)
                        if not part or len(data) + len(part) > 16384:
                            raise RuntimeError('Missing or oversized mock authorize request')
                        data += part
                    auth = json.loads(data.split(b'\n', 1)[0])
                    if auth.get('method') != 'mining.authorize':
                        raise RuntimeError('Unexpected mock authorize method')
                    send(conn, {'id': auth.get('id'), 'result': True, 'error': None})
                    job(conn, 'mock-before-wait', '01')
                    before = await_positive()
                    state['before_wait'] = before
                    pause_started = int(time.time() * 1000)
                    state['pause_started_unix_ms'] = pause_started
                    # This must retire the previous work, not keep hashing it.
                    send(conn, {'id': None, 'method': 'mining.notify', 'params': {
                        'job_id': 'mock-invalid-retires-work', 'header': '00',
                        'target': '0' * 63 + '1', 'height': 2, 'cert_version': 3}})
                    until = time.monotonic() + 50
                    while not done.is_set() and time.monotonic() < until:
                        time.sleep(0.2)
                    state['zero_samples'] = [r for r in records(log)
                        if r.get('rate') == 0 and r.get('uptime_s', -1) > before['uptime_s']]
                    state['resume_sent_unix_ms'] = int(time.time() * 1000)
                    job(conn, 'mock-after-wait', '02')
                    state['after_wait'] = await_positive(before['uptime_s'])
                    write_json(out / 'mock-result.json', state)
                    (guard / 'stop.request').touch()
                    while not done.wait(0.2):
                        pass
        except Exception as exc:
            state['errors'].append(type(exc).__name__ + ': ' + str(exc))
            write_json(out / 'mock-result.json', state)
            (guard / 'stop.request').touch()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    os.environ['SOAT_PEARL_SHAPE'] = '4096x65536'
    os.environ['SOAT_PEARL_TILE'] = '=ampere large s3 fold k64'
    os.environ.pop('SOAT_PEARL_PROFILE', None)
    code = None
    try:
        code = run(SimpleNamespace(output=str(guard), seconds=180, power=220,
            command=[str(exe), '--algo', 'pearl-pow', '--device', '0', '--pool',
                     '127.0.0.1:' + str(port), '--wallet', 'prl1qq' + 'q' * 56,
                     '--worker', 'local-wait-test', '--plain', '--interval', '5']))
    except Exception as exc:
        state['errors'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        done.set()
        server.close()
        thread.join(timeout=3)
    receipt_path = guard / 'guard-status.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    zeros = state['zero_samples']
    stamps = [r.get('timestamp_unix_ms', 0) for r in zeros]
    if len(zeros) < 3:
        state['errors'].append('No three zero-rate heartbeats during the 50 second wait')
    if any(r.get('backend') != 'CUDA' or r.get('unit') != 'T MAC/s' or
           r.get('accepted') != 0 or r.get('rejected') != 0 for r in zeros):
        state['errors'].append('Waiting altered device, units or mock share counters')
    if any(stamp < state.get('pause_started_unix_ms', 0) or
           stamp > state.get('resume_sent_unix_ms', 0) for stamp in stamps):
        state['errors'].append('Waiting statistics missing their actual emission time')
    if len(set(stamps)) != len(stamps) or not stamps:
        state['errors'].append('Waiting timestamps did not advance')
    if code != 0 or not receipt.get('power_restored') or receipt.get('status') != 'stopped':
        state['errors'].append('Owned guard did not stop and restore the original power limit')
    if state.get('after_wait', {}).get('rate', 0) <= 0:
        state['errors'].append('CUDA work did not resume after a valid job')
    if state.get('after_wait', {}).get('timestamp_unix_ms', 0) < state.get('resume_sent_unix_ms', 0):
        state['errors'].append('Recovered statistics are not a fresh timestamped record')
    state.update(status='passed' if not state['errors'] else 'failed',
                 ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 guard_return_code=code, guard_receipt=str(receipt_path),
                 power_restored=receipt.get('power_restored'))
    write_json(out / 'result.json', state)
    print(json.dumps(state))
    return 0 if state['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
