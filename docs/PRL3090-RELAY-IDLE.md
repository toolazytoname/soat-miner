# Duplex idle deadline and the PRL3090 comparison

The relay now measures inactivity across the connection as a whole. Traffic in either direction moves the shared idle deadline. Certificate-chain verification, hostname verification, TLS 1.2 minimum, loopback-only listening and the absence of a plaintext upstream fallback are unchanged. No application payload logging was added.

The old relay applied a separate 300-second read timeout to each direction. That can disconnect a healthy incoming stream when the miner has not submitted a share, or a healthy outgoing stream when the server has not sent data recently.

## Evidence

A local TLS fixture with a trusted temporary localhost certificate sends one-way heartbeats for longer than the idle period. The original relay fails the incoming-traffic case while the fixed relay passes incoming-only traffic, outgoing-only traffic and a genuinely silent-connection timeout. The deployed manager copy also passes all six existing certificate/hostname/endpoint tests.

The complete manager CPU suite passes 59 cases in normal Python and 59 under -O. Three additional duplex-idle cases pass in each mode against the deployed copy. No GPU workload, permanent trust-store change, wallet signing or real-pool submission occurs in these tests.

Field timing is consistent with the bug: the first A1 share was reported at 127.419 seconds and an idle interruption appeared around 428.2 seconds, followed by another approximately 302 seconds later. This is an inference, not proof that every observed disconnection has this cause. KRig also reconnected without a relay exception, so other miner/pool reconnect behavior remains possible.

## First comparison round retained, not promoted

The original fixed analysis window is the final 180 seconds of the planned 720-second case, measured from the recorded session start. Extra observations and operator stop latency remain in the raw data and do not move that window.

| First round | Result |
| --- | --- |
| Source A1 | 51.3665 T MAC/s, 219.7968 W average GPU power; stable; 1 accepted, 0 rejected |
| KRig B | 15.28 seconds of zero reported rate in the final window; core range 12 C, hotspot range 17.75 C; 3 accepted, 0 rejected |
| Source A2 | Not run after B failed the stability gate |

B does not pass the predeclared thermal gate. This round is invalid for announcing a performance percentage. The accepted shares demonstrate connectivity; the small counts do not establish an income comparison.

The fix is vendored into the manager before a new complete source/KRig/source round. Both miners retain their pinned binaries, the original pool, wallet, PPS+ mode, absolute mining deadline and 220 W cap. KRig's localhost fee is explicitly acknowledged in RAM only by the one-case entry. The normal production configuration remains SOAT with that fee disabled.

Evidence remains on Windows under D:/AI/Playgrounds/soat-miner/20261028-prl3090/closed-source-comparison. The original matched-performance directory and all failed receipts are retained. The fresh round is separate; the first result is not overwritten or relabeled as a pass.

This is a host-transport correction. It does not change CUDA proof computation, and it does not increase the separately measured 9.709% kernel gain over original SOAT.
