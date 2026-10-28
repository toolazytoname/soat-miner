"""Loopback-only TCP-to-verified-TLS relay for the upstream Pearl client.

No application payloads, wallets or proofs are logged. Certificate verification
and hostname checking are mandatory. The default trust roots are the Windows
Python/OpenSSL system roots; no insecure or plaintext upstream fallback exists.
TCP keepalive checks peer liveness without requiring a new job or share.
An optional application idle deadline measures inactivity across both directions.
"""
import asyncio
from datetime import datetime, timezone
import json
import math
import socket
from pathlib import Path
import ssl
import threading


class TlsRelay:
    def __init__(self, host, port, *, receipt=None, context=None, idle_seconds=None):
        if not host or '/' in host or ':' in host or not 1 <= int(port) <= 65535:
            raise ValueError('Expected a DNS hostname and a valid TLS port')
        self.host, self.port = host, int(port)
        self.context = context if context is not None else ssl.create_default_context()
        if self.context.verify_mode != ssl.CERT_REQUIRED or not self.context.check_hostname:
            raise ValueError('TLS certificate and hostname verification are mandatory')
        self.context.minimum_version = max(self.context.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.receipt = Path(receipt) if receipt else None
        self.idle_seconds = None if idle_seconds is None else float(idle_seconds)
        if self.idle_seconds is not None and (not math.isfinite(self.idle_seconds) or self.idle_seconds <= 0):
            raise ValueError('Application idle limit must be positive and finite, or None')
        self.ready = threading.Event()
        self.thread = None
        self.loop = None
        self.error = None
        self.local_port = None
        self.state = dict(status='preparing', upstream=f'{host}:{port}', bind='127.0.0.1',
                          certificate_required=True, hostname_check_required=True,
                          sessions=0, active_sessions=0, verified_sessions=0,
                          failed_sessions=0, client_bytes=0, upstream_bytes=0,
                          connection_idle_timeouts=0, application_idle_seconds=self.idle_seconds,
                          tcp_keepalive=None)

    def _save(self):
        if self.receipt:
            self.receipt.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.receipt.with_suffix('.tmp')
            tmp.write_text(json.dumps(self.state, indent=2)+'\n', encoding='utf-8')
            tmp.replace(self.receipt)

    async def _client(self, reader, writer):
        if self.state['active_sessions']:
            writer.close()
            await writer.wait_closed()
            return
        self.state['sessions'] += 1
        self.state['active_sessions'] = 1
        upstream = None
        copies = []
        try:
            # Complete authenticated TLS before forwarding a single client byte.
            remote_reader, upstream = await asyncio.wait_for(asyncio.open_connection(
                self.host, self.port, ssl=self.context, server_hostname=self.host,
                ssl_handshake_timeout=12), timeout=18)
            secure = upstream.get_extra_info('ssl_object')
            peer = upstream.get_extra_info('socket')
            if peer is None:
                raise RuntimeError('Missing upstream TCP socket for keepalive')
            peer.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            keepalive = dict(enabled=bool(peer.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)))
            idle_option = getattr(socket, 'TCP_KEEPIDLE', getattr(socket, 'TCP_KEEPALIVE', None))
            options = [(idle_option, 60, 'idle_seconds'),
                       (getattr(socket, 'TCP_KEEPINTVL', None), 10, 'interval_seconds'),
                       (getattr(socket, 'TCP_KEEPCNT', None), 5, 'probe_count')]
            for option, value, name in options:
                if option is not None:
                    peer.setsockopt(socket.IPPROTO_TCP, option, value)
                    keepalive[name] = peer.getsockopt(socket.IPPROTO_TCP, option)
            self.state['tcp_keepalive'] = keepalive
            self.state.update(verified_sessions=self.state['verified_sessions']+1,
                              tls_version=secure.version(), cipher=secure.cipher()[0])
            self._save()
            clock = asyncio.get_running_loop()
            activity = dict(last=clock.time(), expired=False)
            async def copy(source, destination, field):
                while True:
                    if self.idle_seconds is None:
                        # A valid mining job can be quiet for more than five minutes.
                        # TCP keepalive detects a dead peer without requiring new work/shares.
                        data = await source.read(65536)
                    else:
                        remaining = self.idle_seconds - (clock.time() - activity['last'])
                        if remaining <= 0:
                            if not activity['expired']:
                                self.state['connection_idle_timeouts'] += 1
                                activity['expired'] = True
                            raise TimeoutError('No traffic in either direction before the connection idle limit')
                        try:
                            data = await asyncio.wait_for(source.read(65536), remaining)
                        except asyncio.TimeoutError:
                            # The other direction may have moved this shared deadline.
                            continue
                    if not data:
                        return
                    activity['last'] = clock.time()
                    destination.write(data)
                    await destination.drain()
                    self.state[field] += len(data)
            copies = [asyncio.create_task(copy(reader, upstream, 'client_bytes')),
                      asyncio.create_task(copy(remote_reader, writer, 'upstream_bytes'))]
            finished, _pending = await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
            for task in finished:
                task.result()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.state['failed_sessions'] += 1
            self.state['last_error'] = type(exc).__name__+': '+str(exc)
        finally:
            for task in copies:
                task.cancel()
            if copies:
                await asyncio.gather(*copies, return_exceptions=True)
            for stream in (writer, upstream):
                if stream:
                    stream.close()
                    try:
                        await asyncio.wait_for(stream.wait_closed(), 3)
                    except (Exception, asyncio.CancelledError):
                        pass
            self.state['active_sessions'] = 0
            self._save()

    async def _serve(self):
        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()
        self.clients = set()
        def connected(reader, writer):
            task = asyncio.create_task(self._client(reader, writer))
            self.clients.add(task)
            task.add_done_callback(self.clients.discard)
        server = await asyncio.start_server(connected, host='127.0.0.1', port=0,
                                            limit=131072)
        self.local_port = server.sockets[0].getsockname()[1]
        self.state.update(status='running', local_port=self.local_port,
                          started_at=datetime.now(timezone.utc).isoformat())
        self._save()
        self.ready.set()
        try:
            async with server:
                await self.stop_event.wait()
        finally:
            server.close()
            await server.wait_closed()
            for task in list(self.clients):
                task.cancel()
            await asyncio.gather(*list(self.clients), return_exceptions=True)
            self.state.update(status='stopped', ended_at=datetime.now(timezone.utc).isoformat())
            self._save()

    def _thread_main(self):
        try:
            asyncio.run(self._serve())
        except BaseException as exc:
            self.error = exc
            self.state.update(status='failed', last_error=type(exc).__name__+': '+str(exc))
            self._save()
        finally:
            self.ready.set()

    def __enter__(self):
        self.thread = threading.Thread(target=self._thread_main, name='verified-tls-relay', daemon=True)
        self.thread.start()
        if not self.ready.wait(20) or self.error or self.local_port is None:
            self.__exit__()
            raise RuntimeError('Could not start the loopback TLS relay') from self.error
        return self

    def __exit__(self, *_exc):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.stop_event.set)
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                raise RuntimeError('TLS relay did not stop')
