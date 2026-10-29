# RTX 3090: open SOAT and closed KRig observations

## Current repaired-app observations: counter audit correction

**Correction: the earlier all-gates-passed classification is withdrawn.** A subsequent counter audit found one locally obsolete proof that was discarded before submission in A2. The synchronous Pearl path had left its combined failure counter at zero, hiding that event from a counters-only gate. Independent log checking now marks this comparison **needs review**. No obsolete proof was sent, and this event is not evidence of a pool rejection or invalid GPU math.

The measured fixed-window numbers are unchanged. Source A1/A2 average **53.599876 T MAC/s** versus KRig **57.676079**; KRig's observed gross mean is **7.6049% higher**. This is an observed full-loop difference with a disclosed quality flag, not a strict confirmed winning percentage, payout estimate or pure-kernel measurement.

| Case | Backend | Normalized T MAC/s | Mean GPU W | Accepted |
| --- | --- | ---: | ---: | ---: |
| A1 | Open SOAT | 53.307424 | 219.443 | 3 |
| B | KRig | 57.676079 | 219.389 | 2 |
| A2 | Open SOAT | 53.892329 | 219.821 | 7 |

Every interval uses the originally declared +420..+600 seconds from first selected-profile telemetry, including zero-rate waiting. All intervals had zero measured idle time. Core/hotspot/memory ranges pass <=2 C, and source-control drift is 1.097229%, below 3%. All planned stops verified owned processes exited and restored the original 370 W cap. A1 contains zero client failure events; A2 contains one obsolete-job-not-sent event and zero no-reply events. The stricter combined failure gate is therefore false even though the legacy JSON showed rejected=0. Source stale outcomes are not separately reported; they must not be inferred from a placeholder zero alone.

An earlier A2 attempt stopped before mining when a newly opened Orca chat renderer was conservatively classified as another GPU app. Its path/product/signature were checked and the desktop classification corrected. Completed A1/B receipts were reused byte-for-byte, only the unstarted A2 resumed, and all interruption/measurement data remain retained. The subsequent audit correction does not discard or replace any measured case.

Source app: aa693da08d4a79eb3e7e9878020648dec913c12f91a44c07b636001a7a9f0c22. KRig 1.5.12: 61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f. Unit linkage uses prior hardware-verified KRig calibration plus unchanged source work accounting and full-buffer proof; this is not a fresh independent hardware calibration of this source binary.

SOAT upstream and this fork have zero developer fee. KRig's verified localhost test route acknowledged 3% in RAM; its advertised legitimate native recognized Kryptex reference is 0%. Applying 3% to its observed gross work gives 55.945796 T MAC/s as arithmetic only, not measured income. The fee is not a Mac forwarding cost; all mining/management/TLS processes run on Windows.

The open app remains selected for editable compute ownership, not a demonstrated speed lead. Two later scheduling candidates passed full-buffer checks but observed -0.47% and -0.72% in their warmed screen and were not promoted. A separate reporting fix now publishes synchronous/null-source failures and adds independent failure-log guards. Its build/deployment gates are recorded separately; it does not change mining/proof/wire/rate semantics or claim a speed improvement.

Windows observations: D:\AI\Playgrounds\soat-miner\20261029-postmove-krig-comparison-04. Counter regression/audit: D:\AI\Playgrounds\soat-miner\20261029-submission-readout. The original counters-only summary is preserved alongside the corrected summary. Original wallet, pool, payout threshold and absolute deadline remain unchanged.

## Earlier comparison retained as history (quality gates did not all pass)


Measured on 2026-10-29 UTC on one Windows RTX 3090 24 GB, driver 581.29, a 220 W board cap and automatic clocks/fans. The original Kryptex PRL pool, wallet and PPS+ mode were retained. These are real-pool wall-rate observations, including proof/network activity.

### Method and quality

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

### Fees and selection

Both upstream SOAT and this open fork have **0% developer fee**. The installed KRig 1.5.12 help specifies 0% for Kryptex endpoints and at least 3% elsewhere. It actually logged 3% when connected through the verified localhost relay. The 3% acknowledgement was temporary and in memory for B; the production config file was byte-for-byte unchanged. Open-source licensing and developer-fee policy are separate choices. Pool service fees are separate.

Applying the advertised 3% as a simple work-budget model gives **57.9190 T MAC/s** for the closed observation versus **50.8358** open. This model is not a measured payout. The KRig API is not asserted to separate developer-pool shares; short share counts are compatibility evidence rather than an income estimate.

The selected everyday backend remains the open fork for editable compute source, verified pool compatibility and zero developer fee. The closed binary remains a documented performance reference. The open fork has not demonstrated a speed lead over KRig. Its separately validated **+9.709%** optimization is relative to the preserved original SOAT compute loop; see [controlled source results](PRL3090-RESULTS.md).

### Reproduction and records

- Analysis: `tools/analyze_matched_backends.py`; 15 CPU cases pass in both normal Python and `-O`.
- Source binary SHA-256: `820d7f63ca3d4806f8bb88ab514ed5a5078618c1a4cb0b459cc8c63f47f6f35b`.
- KRig 1.5.12 SHA-256: `61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f`.
- Raw Windows directory: `D:\AI\Playgrounds\soat-miner\20261028-prl3090\closed-source-comparison\matched-performance-03`.
- It contains the plan, A1/B/A2 start and stop receipts, fixed-window summaries, native API observations, unit-calibration reference, unchanged-config receipt and original logs.

The payout experience continues under its original threshold and hard deadline. No completed payout, wall-plug energy measurement or daily-profit estimate is claimed.