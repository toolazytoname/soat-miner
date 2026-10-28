# Transport liveness for quiet PRL mining jobs

Production uses TCP keepalive without an application-traffic idle cutoff. A valid job can remain quiet for more than five minutes while the GPU continues computing. Absence of a new notification or winning share is not proof that the TCP connection is dead.

On this Windows host the upstream socket reads back SO_KEEPALIVE enabled, a 60-second idle setting, 10-second probe interval and five probes. These are per-socket options, not global network settings. The settings and a healthy quiet connection were tested; a blackholed-network timing experiment was not performed.

An explicit optional application idle limit remains available. When enabled, traffic in either direction moves its shared deadline. Production explicitly chooses None. TLS handshake limits, certificate-chain and hostname verification, TLS 1.2 minimum, loopback-only listening and the lack of a plaintext upstream fallback remain in place. The original mining deadline, payout threshold, thermal protections, manual stop and GPU coexistence guard are separate and unchanged.

## Validation

The old per-direction idle timer fails a local TLS heartbeat fixture. The intermediate shared timer fixed one-direction activity but retained a five-minute application cutoff. A second real-pool KRig case then recorded one connection_idle_timeouts event during valid mining work.

The current fixture checks incoming-only activity, outgoing-only activity, an explicitly requested idle timeout, a legitimate quiet job with TCP keepalive, the no-cutoff production default and invalid idle-limit values. All six pass in normal Python and under -O. The manager passes 60 CPU cases in each mode, including strict certificate/hostname/endpoint checks and the production factory policy. The deployed relay passes the six additional transport cases in each mode: 66 checks per mode in total.

The local certificates are temporary test material. No permanent trust-store changes, driver changes, GPU work, wallet signing or real-pool submissions occur in these CPU tests. No application payload logging was added.

## Retained comparison rounds

| Round | Retained finding |
| --- | --- |
| Original per-direction timer | A1: 51.3665 T MAC/s, 219.7968 W, stable; B failed thermal stability after an interruption; no A2 |
| Shared application timer | A1: 51.5685 T MAC/s, 219.7815 W, stable; B recorded one idle cutoff, 15.30 seconds of zero rate in its final window and a 12 C core range; no A2 |
| TCP keepalive, no application cutoff | New complete source/KRig/source round; no winning percentage before all cases pass |

The first A1 share timing (127.419 seconds) and interruption around 428.2 seconds were consistent with the old 300-second direction timer. That correlation was an inference. The later retained idle-timeout counter is direct evidence of a local cutoff; other miner/pool reconnect causes are still possible.

Every new case uses the first selected-profile GPU telemetry timestamp as its measurement origin, excluding intentional cooldown. The fixed measurement is +540 through +720 seconds. Extra observations and operator stop latency are retained and do not move the measurement window. Legacy rounds keep their recorded analysis rules.

A case interrupted inside its fixed window is not promoted as a controlled performance win. Miner-reported accepted shares demonstrate connectivity, and the small sample is not an income comparison. Both pinned compute binaries, the original pool, public wallet, PPS+ mode and 220 W cap are preserved. KRig's localhost developer fee is explicitly acknowledged in RAM for its case; the default configuration remains SOAT with that fee disabled.

Evidence stays under D:/AI/Playgrounds/soat-miner/20261028-prl3090/closed-source-comparison on Windows. Failed rounds and receipts remain separate from the new round.

These are host-transport and measurement corrections. They do not change the CUDA proof computation or increase the separately established 9.709% kernel gain over original SOAT.

Reference: [Python 3.12 socket options and Windows support](https://docs.python.org/3.12/library/socket.html).
