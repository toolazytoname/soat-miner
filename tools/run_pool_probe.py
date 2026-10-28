"""Bounded source-miner pool probe using verified TLS; no automatic restart."""
import argparse
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from run_guarded import run, write_json, manual_cancel_token
from tls_relay import TlsRelay
from payout_policy import fetch, remaining_seconds


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Local JSON with public wallet, pool and worker; never a private key')
    parser.add_argument('--binary', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--deadline-state', help='Existing experience JSON; keeps its original MiningDeadline')
    opts=parser.parse_args()
    initial_cancel=manual_cancel_token()
    if not 30<=opts.seconds<=900:
        parser.error('Pool probes must be 30..900 seconds')
    cfg=json.loads(Path(opts.config).read_text(encoding='utf-8-sig'))
    pool=urlsplit(cfg['pool'])
    if pool.scheme!='stratum+ssl' or not pool.hostname or not pool.port or pool.username or pool.password or pool.path not in ('','/'):
        parser.error('Expected stratum+ssl://HOST:PORT without credentials or path')
    if not isinstance(cfg.get('wallet'),str) or not cfg['wallet'].startswith('prl1'):
        parser.error('A public PRL receive address is required')
    out=Path(opts.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if opts.deadline_state:
        opts.seconds=min(opts.seconds,remaining_seconds(opts.deadline_state))
        if opts.seconds<30:raise RuntimeError('Original experience deadline reached; no GPU work started')
    snapshot=fetch(cfg['wallet'])
    write_json(out/'pool-limit-status.json',snapshot)
    if snapshot['goal_reached']:raise RuntimeError('First payout threshold/record already reached; no GPU work started')
    stop_watch=threading.Event()
    def watch_limit():
        last_ok=time.monotonic()
        while not stop_watch.wait(30):
            try:
                current=fetch(cfg['wallet']);last_ok=time.monotonic()
                write_json(out/'pool-limit-status.json',current)
                if current['goal_reached']:
                    (out/'stop.request').write_text('first-payout-threshold-or-record',encoding='utf-8');return
            except Exception as exc:
                write_json(out/'pool-limit-error.json',dict(error=str(exc)))
                if time.monotonic()-last_ok>=1800:
                    (out/'stop.request').write_text('pool-api-unavailable-30-minutes',encoding='utf-8');return
    watcher=threading.Thread(target=watch_limit,name='read-only-payout-limit',daemon=True)
    watcher.start()
    try:
        with TlsRelay(pool.hostname,pool.port,receipt=out/'tls-status.json') as relay:
            command=[str(Path(opts.binary).resolve()),'--algo','pearl-pow','--device','0',
                     '--pool',f'127.0.0.1:{relay.local_port}','--wallet',cfg['wallet'],
                     '--worker',cfg.get('worker','source-probe'),'--plain','--interval','5']
            code=run(SimpleNamespace(command=command, output=str(out),seconds=opts.seconds,power=220,initial_manual_cancel=initial_cancel))
        accepted=rejected=0
        for line in (out/'child.log').read_text(encoding='utf-8',errors='replace').splitlines():
            try: row=json.loads(line)
            except ValueError: continue
            accepted=max(accepted,int(row.get('accepted',0)))
            rejected=max(rejected,int(row.get('rejected',0)))
        result=dict(exit_code=code,accepted=accepted,rejected=rejected,
                    tls_verified_sessions=relay.state['verified_sessions'],
                    scope='Short compatibility probe only, not a completed payout experience')
        write_json(out/'pool-probe-result.json',result)
        return 0 if code==0 and accepted>0 and rejected==0 and relay.state['verified_sessions']>0 else 1
    except BaseException as exc:
        write_json(out/'pool-probe-error.json',dict(error=type(exc).__name__+': '+str(exc)))
        raise
    finally:
        stop_watch.set();watcher.join(timeout=20)

if __name__=='__main__':
    raise SystemExit(main())
