# Faster RTX 3090 kernel iteration

The workflow builds only the miner and two kernel-verification targets, checks complete transcript buffers, screens candidates at the same power, then confirms a material candidate and tests a real pool share. Production configuration changes are a separate final action.

## First warmed screen, 2026-10-29 UTC

- Native SM86 build: 39 seconds for the three required targets.
- Both warpwide candidates passed all six complete-buffer comparisons: 256x768, 1024x1024 and 4096x65536, K=2048 and rank=128; zero differing words.
- GPU board cap 220 W, automatic clocks/fans, one 300-second warmup followed by 60-second A0/C1/A1/C2/A2 cases. Final 30-second means use aligned fresh statistics and GPU telemetry.
- Controls must stay within 2% and each thermal window within 2 C. A candidate needs at least 3% observed throughput and GPU-efficiency gain to enter longer confirmation.

| Case | T MAC/s | GPU W | Thermal window steady |
| --- | ---: | ---: | --- |
| A0 | 50.8836 | 219.77 | True |
| C1 | 47.8522 | 219.72 | True |
| A1 | 51.3437 | 219.76 | True |
| C2 | 53.7816 | 219.79 | True |
| A2 | 51.6456 | 219.79 | True |

Control spread: 1.498%. C1 was -6.381% slower than its bracketing controls and is rejected. C2 was 4.441% faster, with 4.436% higher board-GPU efficiency. These are short screening observations.

C2 uses a 256-thread 256x128 block with 4x4 tiles per warp, rather than the previous 512-thread 4x2-per-warp configuration. It compiles to 210 registers/thread with zero local bytes, versus 120 previously. Both use 92,160 dynamic shared bytes and one theoretical block per SM. The candidate has fewer resident warps; theoretical occupancy alone did not predict this screen.

## Controlled confirmation and deployment

The selected candidate enters a predeclared continuously warmed A/B/A: 300 seconds warmup, three 240-second cases, fixed final 180 seconds per case, sensor range <=2 C and A-control drift <=2%. A failed quality gate keeps the result provisional. Confirmed throughput and efficiency both need at least 3% improvement. This measures a complete synthetic attempt loop; accepted pool work and income are separate measurements.

The real-pool candidate entry in the separate manager repository requires the completed material confirmation, exact miner hash and matching full-buffer verifier records. The choice stays in RAM, preserves original wallet/pool/deadline, stops at the first accepted share or five mining minutes, and retains manual/thermal/GPU-yield guards. The default production file is not written.

## Confirmed result and pool trial

The confirmation completed at 2026-10-29 01:29 UTC. Every fixed final 180-second window passed the declared 2 C limits.

| Case | T MAC/s | GPU W | Steady |
| --- | ---: | ---: | --- |
| A1 previous validated tile | 51.306869 | 219.767 | True |
| B warpwide large S3 | 53.075287 | 219.798 | True |
| A2 previous validated tile | 51.331796 | 219.758 | True |

A-control drift was 0.048583%. Against the bracketing controls the confirmed full-attempt throughput gain was **3.421624%** and board-GPU efficiency gain **3.405156%**. These gains compare our new and previous open kernels. They do not establish a win over KRig, accepted-share income or whole-system energy savings.

The identical binary was copied to the versioned app directory, SHA-256 `3151d5fa90a2d43a1dfc4d99f7de3ac7b2585db0e74ca9d5fe9e94bca35a8406`. A separate RAM-only trial on the original certificate- and hostname-verified Kryptex PRL route obtained one accepted share, zero rejected/stale shares and zero unconfirmed submission events. It stopped automatically after that acceptance; the owned processes exited and the original 370 W limit was restored. Production configuration stayed byte-for-byte unchanged during the trial.

The pool sent its first job after about 58 seconds; four startup no-job warnings are retained. The TLS receipt also records one connection reset at trial shutdown. This is a compatibility test, not a stable pool-rate or profitability measurement. Full raw receipts remain in the Windows experiment directory.

## Rejected early-copy follow-up

The next opt-in prototype issued future `cp.async` groups after the recycled-stage barrier and before current-stage arithmetic, retaining the original tail empty groups. Both 512-thread large-block S2/S3 forms, plus the current warpwide control, passed all nine full-buffer comparisons. Resource inspection was the tenth successful guarded case. Both new forms use 122 registers/thread, zero local bytes and one theoretical CTA per SM.

One predeclared warmed 220 W screen compared these replacements against the current daily 256-thread warpwide tile:

| Case | T MAC/s | GPU W | Thermal window steady |
| --- | ---: | ---: | --- |
| A0 warpwide control | 54.001626 | 219.813 | True |
| C1 early large S2 | 50.579573 | 219.776 | True |
| A1 warpwide control | 53.272989 | 219.774 | True |
| C2 early large S3 | 50.475663 | 219.772 | True |
| A2 warpwide control | 53.586291 | 219.797 | True |

Control spread was 1.367741%, within the 2% gate. C1/C2 throughput was respectively **5.700761% / 5.528724% lower** than their bracketing controls; GPU efficiency was 5.693189% / 5.523039% lower. Neither is promoted or sent to long confirmation. The already confirmed and pool-accepted warpwide app remains selected.

These compare different warp layouts as potential daily replacements. They do not isolate the causal effect of early copies or rule out all other pipeline arrangements. The original pipeline remains the default template path; the experimental early-copy path is opt-in. Full Windows evidence: `D:\AI\Playgrounds\soat-miner\20261029-prefetch-iteration`.

## Counter snapshot for the selected warpwide kernel

A separate bounded diagnostic of the exact confirmed binary completed, with owned processes exited and original power restored. Nsight Compute used `--clock-control none` and `--cache-control none`; the kernel replay reported 1.729401 GHz, 63.005915% Tensor-pipe activity, 64.073964% L2 throughput and zero recorded shared-memory bank conflicts. Per-issue-active stall ratios were math-pipe throttle 2.578153, wait 1.981476, long-scoreboard 0.371641 and barrier 0.230178.

This snapshot supports investigating instruction scheduling and overlap before speculative bank-conflict fixes. It does not prove a unique bottleneck or remaining achievable percentage. Instrumented replay clocks/times differ from ordinary warmed 220 W mining, so neither the 6.014080 ms replay nor cross-profile clock differences replace the controlled throughput result. The full profiler report and selected metrics stay under the Windows follow-up directory.

## Commands

Build the bounded target set on Windows:

```powershell
& D:\Apps\PowerShell\7\pwsh.exe -NoProfile -File .\tools\build_prl3090_windows.ps1 -BuildDirectory D:\Projects\toolazytoname\soat-miner\build\prl3090-warpwide -GpuTests -AmpereCandidates -KernelIteration
```

Run `tools/run_correctness_suite.py` with `--build prl3090-warpwide` and the selected `--variants`. Use a new output directory. GPU work runs in the authorized interactive elevated Windows task after the mining session is stopped and power restoration is verified.

`tools/run_fast_screen.py --plan <plan.json> --output <new-run>` uses `mode: screen` or `mode: confirm`. `--check-only` validates the plan and binary/proof linkage without GPU work. Plans and full records for this experiment remain in `D:\AI\Playgrounds\soat-miner\20261029-warpwide-iteration`.

The screen and confirmation runner has seven CPU checks in each of normal Python and `-O`. Original stop/deadline, one-GPU ownership, automatic clocks/fans and power restoration stay in force. No automatic production promotion or repeated benchmark loop is installed.

## Pool-input buffering correction, 2026-10-29

A post-reboot source run stopped with source_telemetry_unavailable before collecting a valid performance window. Its log also contains TLS/auth resets. Two direct verified-TLS probes and two probes through the manager's unchanged verified helper subsequently received authorize success and a complete job promptly; these probes do not establish that all historical resets were caused by the miner.

The host reader had a separate reproducible framing bug. readLine can receive an authorize acknowledgement and a notification together, returning the acknowledgement while retaining the notification in pending_. drain then polled only the kernel socket. If the peer sent no new packet, it ignored the complete buffered job, waited eight seconds and reported no usable work.

The correction checks for a complete buffered line before polling the socket. A CPU-only public-API loopback regression failed on the old reader in 8.096 seconds, returning no job despite a valid queued notification. After correction, all five socket checks pass in normal Python and -O: coalesced acknowledgement/job, multiple queued jobs with latest winning, notification before acknowledgement, delayed notification, and rejection of malformed work. The existing host protocol checks also pass. No GPU, share submission or wallet secret is needed for these checks.

Build test-pearl-pool in the desired CMake build. Set SOAT_POOL_TEST_EXE to that executable, then run tests/test_pearl_pool_buffered.py; the driver is restricted to 127.0.0.1. Production still requires matching full-buffer GPU verification and real-pool acceptance. Kernel timing, developer-fee policy, original deadline, transport validation and proof format are unchanged. This is an input-availability correction, not a claimed percentage win over KRig.


The repaired native SM86 miner is SHA-256 aa693da08d4a79eb3e7e9878020648dec913c12f91a44c07b636001a7a9f0c22. Resource inspection and selected warpwide full-buffer cases 256x768, 1024x1024 and 4096x65536 all passed with zero differing words, child exit 0 and restored power. The large case covers 1,048,576 transcript tiles. Three successful cases were retained from the first suite; its final large case was refused by startup load checks before launching. Only that refused case was then run separately in an idle state. The original failed suite receipt is preserved, and an explicit aggregate links both sets; the failed suite was not relabeled as successful.

The guard's desktop startup check retains 10% utilization and 2048 MiB limits for experiments. A high reported percentage is excused only with all of board power <=30 W, graphics clock <=405 MHz and memory clock <=810 MHz. Independent unknown GPU-client, thermal and cancellation checks remain in force. This avoids a low-clock desktop false positive without accepting an actively clocked workload. The production manager additionally uses a bounded 30-second idle preflight wait. No GPU algorithm, proof, clock setting, driver or security setting changes in this repair.

All 39 relevant Python checks pass in normal and optimized modes, including the new eight preflight load scenarios. Real-pool acceptance of the newly pinned app and the new matched KRig comparison are still pending at this commit; earlier observations are not substituted for those gates. Windows repair evidence is under D:\\AI\\Playgrounds\\soat-miner\\20261029-postmove-krig-comparison and its -02 continuation.


## Queued warpwide fragment-scheduling experiments

Two opt-in hypotheses now use the identical current 256-thread, 256x128, K64, three-stage warpwide geometry. The stream-B candidate loads one B fragment and updates all independent A accumulators before loading the next B fragment. It aims to shorten live ranges and interleave shared loads with MMA; fewer registers or a speed increase are hypotheses, not observed results. The early-copy candidate uses the existing prefetch path with this exact warpwide geometry, separating it from the previously rejected 512-thread candidates. Default template selection and production app are unchanged.

Native SM86 compilation completed in 43.7 seconds, before the current KRig fixed measurement window (selected-profile seconds 66..107; measured window begins at 420). Experimental miner SHA-256 is ceb7eadd7e9fc20bd5e070a223dc249618b5761956738c198581fc1227f38b1f. The current original-pool comparison continues using the immutable aa693 repaired app; the experimental app has not run on GPU at this commit.

Before timing, both candidates and the recompiled control require all three full transcript-buffer checks against the independent oracle plus actual resource inspection. A bounded warmed screen will bracket two candidates with three controls. Only an observed >=3% throughput and GPU-efficiency gain, stable temperatures and <=2% control spread qualifies for longer A/B/A confirmation. Any production change additionally requires real-pool acceptance. Negative results are retained; no automatic promotion or retry is installed.

The experiment guard now waits up to 30 seconds for an idle sample before child launch or power change, checking manual cancellation, temperatures, original power-limit validity and non-desktop GPU clients on every sample. This addresses the same transient startup effect as the production manager without widening the conservative idle thresholds. Six additional host scenarios bring the relevant normal/-O checks to 45 each. The current GPU suite must finish before any candidate GPU work starts. Evidence and the exact compiled-source manifest stay in D:\\AI\\Playgrounds\\soat-miner\\20261029-streamb-iteration.
