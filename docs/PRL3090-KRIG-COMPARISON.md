# RTX 3090: open SOAT and closed KRig observations

Measured on 2026-10-29 UTC on one Windows RTX 3090 24 GB, driver 581.29, a 220 W board cap and automatic clocks/fans. The original Kryptex PRL pool, wallet and PPS+ mode were retained. These are real-pool wall-rate observations, including proof/network activity.

## Method and quality

The sequence was open / closed / open. Each case captured at least 720 seconds from its first selected-profile GPU telemetry. The predeclared reporting window was +540 through +720 seconds; later stop latency stays in the raw records. Intentional cooling was excluded from the clock. Rates are time-weighted, retain zero-rate samples and are not extrapolated over missing telemetry. No profiler was attached during these cases.

[Independent unit calibration](PRL3090-UNIT-CALIBRATION.md) established native KRig TH/s = T MAC/s for this pinned device/version/configuration.

| Case | T MAC/s, fixed final 180 s | Mean GPU W | Core/hotspot/memory range C | Accepted / rejected / stale at session end | Strict thermal gate |
| --- | ---: | ---: | --- | --- | --- |
| A1 (soat) | 50.8789 | 219.21 | 2.00 / 3.41 / 0.00 | 1 / 0 / 0 | fail |
| B (krig) | 59.7103 | 219.72 | 0.00 / 0.59 / 0.00 | 4 / 0 / 1 | pass |
| A2 (soat) | 50.7928 | 219.78 | 0.00 / 0.56 / 0.00 | 3 / 0 / 0 | pass |

The bracketing open mean was **50.8358 T MAC/s**, with **0.169%** A1/A2 drift. The closed observation was **59.7103 T MAC/s**; its raw fixed-window rate was **17.46%** higher.

**The complete strict comparison is flagged `comparison_valid: false`.** A1 hotspot range exceeded the 2 C thermal gate; B reported one stale share and failed the clean-share gate. A1 also logged one no-reply submission, recorded separately from pool accepted/rejected counters. This set supports a scoped operational observation; it does not establish a clean, steady-kernel winning percentage or a payout advantage. All three cases stopped normally, their owned processes exited and the original 370 W cap was restored.

The two earlier interrupted rounds remain on Windows. This round used TCP keepalive without an application-message idle cutoff; certificate and hostname verification remained enabled. Raw relay status, shutdown errors, observations and case overruns are retained.

## Fees and selection

Both upstream SOAT and this open fork have **0% developer fee**. The installed KRig 1.5.12 help specifies 0% for Kryptex endpoints and at least 3% elsewhere. It actually logged 3% when connected through the verified localhost relay. The 3% acknowledgement was temporary and in memory for B; the production config file was byte-for-byte unchanged. Open-source licensing and developer-fee policy are separate choices. Pool service fees are separate.

Applying the advertised 3% as a simple work-budget model gives **57.9190 T MAC/s** for the closed observation versus **50.8358** open. This model is not a measured payout. The KRig API is not asserted to separate developer-pool shares; short share counts are compatibility evidence rather than an income estimate.

The selected everyday backend remains the open fork for editable compute source, verified pool compatibility and zero developer fee. The closed binary remains a documented performance reference. The open fork has not demonstrated a speed lead over KRig. Its separately validated **+9.709%** optimization is relative to the preserved original SOAT compute loop; see [controlled source results](PRL3090-RESULTS.md).

## Reproduction and records

- Analysis: `tools/analyze_matched_backends.py`; 15 CPU cases pass in both normal Python and `-O`.
- Source binary SHA-256: `820d7f63ca3d4806f8bb88ab514ed5a5078618c1a4cb0b459cc8c63f47f6f35b`.
- KRig 1.5.12 SHA-256: `61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f`.
- Raw Windows directory: `D:\AI\Playgrounds\soat-miner\20261028-prl3090\closed-source-comparison\matched-performance-03`.
- It contains the plan, A1/B/A2 start and stop receipts, fixed-window summaries, native API observations, unit-calibration reference, unchanged-config receipt and original logs.

The payout experience continues under its original threshold and hard deadline. No completed payout, wall-plug energy measurement or daily-profit estimate is claimed.
