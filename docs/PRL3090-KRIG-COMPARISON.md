# RTX 3090: open SOAT and closed KRig comparison

## Current counter-corrected matched run — 2026-10-29 UTC

The declared checks passed for this three-case run. The bracketing open mean was **53.831424 T MAC/s**, versus **59.305502** for KRig. KRig's gross observed full-loop throughput was **10.1689% higher**; the open mean was **9.2303% lower** using KRig as denominator. The open fork has not demonstrated a speed lead over KRig.

| Case | Backend | Normalized T MAC/s | Mean GPU W | Core / hotspot / memory range C | Accepted at session stop |
| --- | --- | ---: | ---: | --- | ---: |
| A1 | Open SOAT | 53.981950 | 219.787 | 1.00 / 1.25 / 2.00 | 2 |
| B | KRig 1.5.12 | 59.305502 | 219.679 | 1.00 / 0.62 / 2.00 | 3 |
| A2 | Open SOAT | 53.680898 | 219.779 | 1.00 / 0.78 / 2.00 | 7 |

One Windows RTX 3090 24 GB, driver 581.29, 220 W board cap, automatic clocks/fans, original real pool/wallet/PPS+ mode. Each case collected at least 600 seconds from its first selected-profile telemetry; the predeclared reporting window is exactly +420..+600 seconds. Zero-rate waiting is retained. Cooling is outside the measurement clock; collection/stop overruns do not move the window. No profiler was attached.

All thermal ranges were <=2 C, source-control drift was 0.557690% (limit 3%), and each case had accepted shares. Both open cases had zero combined client failures, zero independent failure-log events, zero obsolete-job-not-sent events and zero no-reply events. KRig's API reported zero rejected and stale shares. Source stale is a compatibility placeholder, not an independently measured stale count; no zero-stale claim is inferred from that field. The combined source failure field includes local verification failures, obsolete unsent work, uncertain no-reply outcomes and explicit negative replies, so it is not a pool-only rejection count.

Each planned stop verified exact owned processes exited, the task finished successfully and the original 370 W cap was restored. Production config and both executable hashes were unchanged across the comparison. Short share counts establish compatibility, not a precise income comparison; KRig's API is not asserted to distinguish developer-pool shares.

## Version, calibration and fees

Open app SHA-256: 41263293ace4ac4a9901ceb6538adc59d17e0fcb95586f4f48970e8d549d2f54.
KRig 1.5.12 SHA-256: 61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f.

The open app is a native SM86 build, shape 4096x65536, warpwide large S3 fold K64, K2048/rank128. The synchronous/null-source counter fix passed 13 CPU protocol checks and 55 related tool checks in each of normal Python and -O, four matching GPU proof/resource cases, and the two real-pool cases above. The host reporting fix does not change GPU math, proof wire semantics or rate accounting.

[Prior independent hardware calibration](PRL3090-UNIT-CALIBRATION.md) established KRig native TH/s = T MAC/s for the pinned device/version/configuration. The current linkage checks unchanged work accounting and matching full-buffer proofs. This is a transferred calibration, not a fresh independent hardware counter capture of this binary.

SOAT upstream and this fork have 0% developer fee. KRig acknowledged 3% for this verified localhost TLS route, in RAM for B only; the legitimate native recognized-Kryptex reference is advertised as 0%. At 3%, arithmetic fee-adjusted KRig work is 57.526337 T MAC/s, 6.8639% above the open mean. This is not measured payout. Pool service fees are separate.

Management, compute and TLS verification all run on Windows. The fee is not a Mac forwarding charge. The selected daily backend remains open SOAT for editable compute ownership, authenticated transport and zero developer fee. KRig remains the faster observed alternative. Neither wall-plug power nor daily net earnings were measured.

## Retained history and optimization scope

The earlier aa693 app comparison under 20261029-postmove-krig-comparison-04 remains needs_review: its observed 53.599876 versus 57.676079 T MAC/s values are preserved, but A2 had one locally obsolete proof discarded before submission that the old combined counter missed. The earlier all-gates-passed classification was withdrawn; the old 7.6049% observation is not relabeled as a clean confirmed result. No obsolete proof was sent and that event alone is not evidence of invalid GPU math or a pool rejection. The fresh run above uses the repaired counter plus independent log checking.

An older 50.8358 versus 59.7103 T MAC/s set also remains flagged: A1 exceeded the hotspot stability gate, B reported one stale share and A1 logged one no-reply submission. Original logs, summaries and corrections remain retained.

The separately validated +9.709% and subsequent +3.4216% improvements are against their respective previous open-source baselines, not KRig; do not add the percentages. Two early-copy candidates were slower by approximately 5.5–5.7%. Two later scheduling candidates passed all ten GPU checks but observed -0.47% and -0.72% in a stable warmed screen and did not reach the predeclared +3% promotion gate. Neither replaced production.

## Reproduction and bounded experience

Analysis tool: tools/analyze_matched_backends.py. Current Windows records: D:\AI\Playgrounds\soat-miner\20261029-submission-readout\matched, including the original plan, start/stop receipts, fixed-window results, comparison-summary.json and comparison-quality.json. Protocol/build/proof/deployment records are in the parent directory; raw telemetry and miner logs remain in the case run directories listed by the summaries.

Original wallet, pool, 1 PRL threshold and absolute deadline (2026-10-30 06:52:36 +08:00) remain unchanged. The payout experience is still pending. No auto-retry, boot trigger, currency conversion or completed payout is claimed.
