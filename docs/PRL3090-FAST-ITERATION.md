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
