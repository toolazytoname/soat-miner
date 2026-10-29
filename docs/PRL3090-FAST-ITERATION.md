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

C1 is the already-tested ampere warpwide compact s2 fold k64 configuration: a 128x128 block, 128 threads and two shared-memory stages. Its 47.852203 T MAC/s observation was below the bracketing controls and failed the promotion gate. This compact warpwide alternative is covered by the preserved screen; it is not an untested occupancy hypothesis. It did not enter longer confirmation, and this short result is not a paid-work or income estimate. The exact candidate mapping is retained in fast-screen-plan.json and fast-screen/result.json under the Windows warpwide-iteration directory.

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

All 39 relevant Python checks pass in normal and optimized modes, including the new eight preflight load scenarios. Real-pool acceptance and the new matched KRig comparison were pending at preparation commit 9c2c002. They have now completed; the current repaired-app result is documented in PRL3090-KRIG-COMPARISON.md. Earlier observations were not substituted for the new gates. Windows repair evidence is under D:\\AI\\Playgrounds\\soat-miner\\20261029-postmove-krig-comparison and its -02 continuation.


## Warpwide fragment-scheduling follow-up

Two opt-in hypotheses now use the identical current 256-thread, 256x128, K64, three-stage warpwide geometry. The stream-B candidate loads one B fragment and updates all independent A accumulators before loading the next B fragment. It aims to shorten live ranges and interleave shared loads with MMA; fewer registers or a speed increase are hypotheses, not observed results. The early-copy candidate uses the existing prefetch path with this exact warpwide geometry, separating it from the previously rejected 512-thread candidates. Default template selection and production app are unchanged.

Native SM86 compilation completed in 43.7 seconds, before the current KRig fixed measurement window (selected-profile seconds 66..107; measured window begins at 420). Experimental miner SHA-256 is ceb7eadd7e9fc20bd5e070a223dc249618b5761956738c198581fc1227f38b1f. The current original-pool comparison continues using the immutable aa693 repaired app; the experimental app had not run on GPU at preparation commit e8c351e. Its subsequent complete validation is recorded below.

Before timing, both candidates and the recompiled control require all three full transcript-buffer checks against the independent oracle plus actual resource inspection. A bounded warmed screen will bracket two candidates with three controls. Only an observed >=3% throughput and GPU-efficiency gain, stable temperatures and <=2% control spread qualifies for longer A/B/A confirmation. Any production change additionally requires real-pool acceptance. Negative results are retained; no automatic promotion or retry is installed.

The experiment guard now waits up to 30 seconds for an idle sample before child launch or power change, checking manual cancellation, temperatures, original power-limit validity and non-desktop GPU clients on every sample. This addresses the same transient startup effect as the production manager without widening the conservative idle thresholds. Six additional host scenarios bring the relevant normal/-O checks to 45 each. The current GPU suite must finish before any candidate GPU work starts. Evidence and the exact compiled-source manifest stay in D:\\AI\\Playgrounds\\soat-miner\\20261029-streamb-iteration.


The final matched-control attempt was interrupted during cooldown when the user opened the local Orca chat application. Its actual D:\Apps\Orca\Orca.exe path, valid SignPath Foundation signature, product metadata and Chromium GPU-renderer command were checked. Orca joins the existing desktop chat/browser classification. No mining child or measurement window had started in that interrupted control; its receipts are retained. Completed A1 and KRig B data are reused, and only the unstarted final control is explicitly resumed after this narrow fix. Model servers and other non-desktop GPU applications still trigger the existing yield guard.


### Full-buffer gate for the scheduling follow-up

All ten guarded cases passed: resource inspection, then three shapes each for the rebuilt control, streamed-B candidate and warpwide early-copy candidate. Every transcript comparison reported zero differing words, every child exited 0, and every guard restored the original power. The largest shape checks 1,048,576 transcript tiles per variant. No other owned GPU child remained after the suite.

| Variant | Registers/thread | Local bytes/thread | Dynamic shared bytes | Resident blocks/SM |
| --- | ---: | ---: | ---: | ---: |
| Recompiled warpwide control | 210 | 0 | 92160 | 1 |
| Streamed B | 210 | 0 | 92160 | 1 |
| Warpwide early copy | 209 | 0 | 92160 | 1 |

The streamed-B source rewrite did not reduce the compiled register count. Neither these resources nor theoretical occupancy prove a speed improvement. The separately predeclared 360-second warmup plus five 90-second A0/C1/A1/C2/A2 cases has completed; all controls use the same rebuilt binary. Neither candidate qualified, as detailed below. A qualifying candidate must later confirm against the actual deployed aa693 app, so a changed compiler baseline cannot masquerade as a production gain. Production remained unchanged throughout this bounded screen.


### Screening outcome: neither candidate promoted

| Case | Exact tile | T MAC/s | Mean GPU W |
| --- | --- | ---: | ---: |
| A0 | ampere warpwide large s3 fold k64 | 53.913798 | 219.807 |
| C1 | ampere warpwide streamb large s3 fold k64 | 53.627866 | 219.821 |
| A1 | ampere warpwide large s3 fold k64 | 53.849834 | 219.788 |
| C2 | ampere warpwide early large s3 fold k64 | 53.420959 | 219.801 |
| A2 | ampere warpwide large s3 fold k64 | 53.763984 | 219.804 |

All final 30-second windows passed the <=2 C thermal range gate. The three controls span 0.278651%, within the 2% limit. Against their respective adjacent controls, streamed B observed **-0.471310% throughput / -0.481622% GPU efficiency**, and early copy **-0.717288% / -0.719306%**. Neither met the predeclared >=3% gain requirement, so neither enters long confirmation or production. These small negative observations are not claimed as precise causal regression estimates or proof that every related schedule is slower.

The compiler still used 210 registers for streamed B, the same as the control; early copy used 209. All had zero local-memory bytes and one resident block/SM. Correct outputs and fewer source-level live fragments did not establish a performance gain.

All six guarded stages (warmup plus five cases) stopped on their fixed durations and restored power. The one-shot task ended successfully, no owned GPU child remained, and the default production configuration was byte-for-byte unchanged. The five completed temporary comparison/proof/screen task definitions were exported and removed; normal mining, recovery and panel tasks remain. All source and evidence stay available for later investigation.

One original bounded real-pool session then resumed using the unchanged aa693 repaired app, 220 W, automatic clocks/fans and original wallet/pool/deadline. At 05:44 UTC the actual CUDA process and fresh statistics were verified, with 3 accepted shares, zero rejected/stale, and one authenticated TLS session without failures. This is a current-session compatibility check, not a completed payout or a new performance percentage. Evidence: D:\\AI\\Playgrounds\\soat-miner\\20261029-streamb-iteration\\production-resume-verification.json.


## NVAPI initialization must survive Python optimization

A read-only audit found that NVAPI initialization and GPU enumeration were executed inside assert expressions. Python -O removes those expressions entirely, so the old optimized interpreter skipped both required calls and retained an invalid handle. A fake-driver regression reproduced the failure in both repositories before correction, without hardware or power calls.

Both telemetry modules now execute initialization and enumeration unconditionally, reject their error codes or a GPU count other than one with RuntimeError, and explicitly require the memory-junction sensor. Seven fake-driver checks cover required call execution, initialization failure, enumeration failure, zero/multiple GPUs, missing junction sensor and read-only sampling. All 89 manager host checks and 52 relevant source-tool checks pass in normal Python and -O.

Four actual read-only samples (both modules, normal and -O) then passed against the installed driver. They only initialized/read telemetry, never called the power setter or started a CUDA workload. The original mining process PID and creation time remained identical throughout, and its 220 W cap and accepted-share progress were preserved. The already running normal-mode miner/controller was not restarted; future controller/tool launches load the corrected initialization. This reliability repair changes no CUDA kernel, binary, throughput claim, fee policy or deadline.

Windows evidence: D:\\AI\\Playgrounds\\RainbowMiner\\20261029-telemetry-init, including red repro logs, both-mode host results and the actual read-only smoke receipt.


## Synchronous failure-readout correction

A live obsolete-job discard exposed a reporting bug: the run loop incremented hostRejected, but only copied failures into the readout when the source implemented asynchronous poolCounters. Pearl uses synchronous acknowledgements and inherits false, so its JSON failure counter could remain zero after a failed submission. The null-source benchmark path could similarly hide host verification failures. Accepted synchronous results were already tracked separately and remain unchanged.

A shared readout helper now always publishes local/synchronous failures, preserves synchronous accepted counts, and adds asynchronous peer counts once when available. This follows the existing combined-counter contract. The JSON rejected field and the manager's compatible RejectedShares field mean **combined client failures**, including local verification, obsolete jobs not sent, unconfirmed/no-reply attempts and synchronous negative pool replies. They are not a pool-only rejection metric. The source UI therefore says “失败/未提交”; KRig retains its native API rejection label. Source stale outcomes are not separately reported and cannot be inferred from a placeholder zero.

A real loopback authorize/notify/submit/negative-ACK fixture reproduced the old 0-versus-1 failure in both Python modes. Thirteen protocol/buffer checks per mode then passed, covering accepted, rejected, accepted-then-rejected, obsolete-not-sent, no-reply, null/bench, synchronous and asynchronous repeated refresh. Fifty-five relevant tool checks per mode pass. The screen rejects nonzero failed-attempt counters and legacy host-verification error logs. The matched analyzer independently checks client failure events even when a legacy counter shows zero. The panel parses in PowerShell 7 and 5.1; its UTF-8 BOM preserves 5.1 Chinese decoding.

The prior matched comparison has been corrected to needs_review: A2 had one local obsolete proof not sent. Gross fixed-window means are retained, but the strict all-failures-zero gate was not met. The two positive source optimization experiments (+9.709% and +3.42%) were separately audited from their original logs; all six A/B/A stage logs contain zero host-verification error events and zero nonzero-failure rows. No GPU benchmark was repeated for that audit.

Native SM86 app SHA-256 is 41263293ace4ac4a9901ceb6538adc59d17e0fcb95586f4f48970e8d549d2f54. Resource inspection and all three selected-tile full-buffer comparisons passed with child exit 0, zero differing words and restored power. This is a functional reporting correction; mining/search, proof serialization, pool wire requests, rate accounting, automatic clocks/fans, wallet, pool, fees and original deadline are unchanged. The fresh original-account real-pool comparison has completed with the corrected counters and independent log gate; its declared checks passed. See the [counter-corrected matched report](PRL3090-KRIG-COMPARISON.md) for the fixed windows, actual results and reporting limits. The reporting fix itself makes no speed-improvement claim.

All red/green logs, build receipt, matching GPU proof, historical audit, predeclared fresh plan and deployment records remain under D:\\AI\\Playgrounds\\soat-miner\\20261029-submission-readout.


## Resumed register-storage and N256 hypotheses

The user requested continued own-compute optimization toward surpassing KRig. Two opt-in variants keep the current fixed K=2048/rank=128 arithmetic and proof semantics. The scratch variant writes each fold into disjoint unused 16-byte A-row padding, then synchronizes each owner warp before a coalesced transcript epilogue. A compile-time capacity check ensures that padding holds all words; asynchronous copies and matrix loads touch only the first K64 bytes of each padded row. This aims to remove persistent slot registers without adding shared bytes. The N256 variant uses a 128x256 block with 2x4 warps and 4x4 tiles per warp, changing cache reuse relative to the 256x128 control. Both retain 256 threads, three stages and 92,160 shared bytes.

Native SM86 compilation took 48.1 seconds. Twelve relevant CPU checks pass in each of normal and optimized Python. Reduced register count and faster wall throughput remain hypotheses until actual resource/full-buffer checks and warmed screening complete. The default template and pinned production app/configuration are unchanged. All three transcript shapes are required for both candidates and the recompiled control, followed by the existing fixed A0/C1/A1/C2/A2 220 W screen. Only >=3% throughput and GPU-efficiency improvement with stable controls qualifies for longer confirmation. Beating the open control alone is not a win over KRig; eventual matched gross KRig comparison and real-pool acceptance remain required. Evidence: `D:\AI\Playgrounds\soat-miner\20261029-foldscratch-iteration`.

The ten GPU gates have now passed: resource inspection and all three shapes for the recompiled control plus both candidates, including 1,048,576 transcript tiles in each large case, zero differing words and restored power after every child. Actual registers/thread are 210 (control), 211 (scratch), and 207 (N256); all have zero local bytes. The scratch register-reduction hypothesis is therefore not supported. Speed remains unmeasured at this checkpoint.

Screen preflight exposed a host inspection issue: vendor process paths can use a legacy Windows code page, causing Python UTF-8 decoding to fail. Both managers now query ASCII PIDs and resolve image names through the existing Unicode Toolhelp API. Malformed/non-ASCII PID output and query failures fail closed; a missing name remains an unknown GPU client. No desktop whitelist or load threshold changed. Six new fault checks per repository cover Unicode names, missing PIDs, empty lists and bad responses. Full source tool discovery passes 86 CPU checks and the separate manager passes 97 checks, each in normal and optimized modes. A real read-only process/telemetry scan also passed; this repair changes no compiled CUDA kernel.

The first screen ended during warmup, before any measured case, after one public-pool TLS handshake timeout. Its raw stopped receipt is retained; no performance result is assigned. The owned child exited with code0 and restored370W. Screening now follows the daily controller's existing30-minute continuous API-outage limit: successful reads reset one clock carried across all cases; transient read failures are logged and retried read-only. Manual/deadline/threshold stops remain in force, and this does not restart a GPU child automatically. Five additional host fault checks cover transient failure, the exact30-minute boundary, success reset, noncontinuous outages and threshold stop. Full source-tool discovery now passes91 checks per Python mode. A new complete screen may be explicitly launched after healthy read-only preflight, preserving the same plan, binary and fixed analysis windows.


The screen02 task was externally terminated at an accidentally inherited12-minute Scheduler limit, shorter than its declared16-minute measurement sequence. This was an operator launch configuration error. The two completed partial cases are retained, and the missing control/candidate stages are not treated as complete. The owned job removed the miner when its controller was killed. After verifying all exact owned PIDs gone, an explicit recovery restored the retained220W cap to370W. Original raw status is backed up, and the recovery is labeled separately. Screen03 now uses an explicitly registered and checked35-minute task budget, no triggers, the identical fixed plan/binary, and the original absolute mining deadline. Its result remains pending here.

## Fold-issue overlap and L1-copy hypotheses

Two further opt-in SM86 variants have compiled in43.1 seconds during screen03 warmup, before its fixed reporting windows. They have not run on GPU. The first folds each tile at the last MMA of its rank instead of batching every tile fold after all MMA, testing tensor/ALU scheduling; fixed ordered accumulators and original transcript semantics are retained. The second uses explicit16-byte `cp.async.ca` copies with32-bit shared addresses, retaining group commits, waits and empty tail groups. Exact control SASS already has `LDGSTS.E.BYPASS.128`, so a CG-only rewrite would repeat its policy. CA instead tests possible L1 reuse of adjacent K64 slices against extra cache traffic. The default template path and pinned production app remain unchanged.

Both candidates and their recompiled control require all three complete-buffer oracle shapes plus resource inspection after the existing screen finishes. Each must then pass the same warmed220W screen and longer confirmation before real-pool deployment. Neither static instruction counts nor compilation establishes a speedup. Evidence: `D:\AI\Playgrounds\soat-miner\20261029-foldissue-iteration`.


## Completed scratch/N256 screen result

The corrected screen03 completed successfully with all five fixed reporting windows thermally steady and0.488320% control spread. At220W, A0/C1/A1/C2/A2 were54.129508 /53.403074 /53.866467 /53.748799 /53.921796 T MAC/s. Against their respective bracketing controls, scratch was1.101732% slower (board efficiency1.101334% lower), and N256 was0.269662% slower (efficiency0.273886% lower). Both fail the>=3% promotion gate and are rejected. This is a bounded screen, not proof that every related layout is slower.

Every warmup/case child ended at its prescribed duration, exit0 with original power restoration. The Scheduler task wasReady/result0 and exact owned processes were absent; an actual read confirmed370W before the next proof suite started. No default app/config changed and no speed win over KRig is claimed. First API-aborted and12-minute Scheduler-aborted records remain separate from this complete result. Full evidence: `20261029-foldscratch-iteration/screen-03/result.json` and `screen-decision.json` in the Windows experiment tree. The subsequently compiled fold-issue/cache-A candidates now enter their separate full-buffer verification; no speed claim is made for them yet.


The fold-issue/cache-A suite has now passed all10 GPU gates, including three shapes for each of the two candidates and their recompiled control, zero differing words and restored power after every child. Registers/thread are210(control),218(fold-issue),210(cache-A), all with zero local bytes. The separate warmed screen is running under the explicitly validated35-minute task limit. There is no measured speed improvement for either at this checkpoint.

## Deferred warp folds and unsigned unrolled-copy hypotheses

Two additional opt-in variants have compiled in45.4 seconds during that screen warmup, before its reporting windows. Deferred fold splits the eight warps into0..3 and4..7, letting the second group consume its old rank accumulators just after the next staging barrier, before any next-rank update. The final pending rank is explicitly flushed after the loop. This tests cross-warp tensor/ALU phase overlap, distinct from immediate per-tile folding. Actual scheduler benefit is unproven; full transcript equality, especially final word15, is mandatory.

The other variant uses compile-time equal per-thread16-byte slices, unsigned copy indices and explicit unrolling. A static assertion requires both A/B slices to divide the256-thread block exactly. It retains the original cache policy, copy groups, wait/drain behavior and all data. The hypothesis is simpler address lowering, not a claimed gain from static instruction counts. Both keep the original template path and production pin untouched. Three runner fault checks pass per Python mode and the new10-case GPU plan validates without starting GPU work. Evidence: `D:\AI\Playgrounds\soat-miner\20261029-deferredcopy-iteration`. GPU validation waits for the existing screen to finish; no parallel heavy GPU task is started.


## Cache-A short screen and user-requested shutdown (2026-10-29)

The fold-issue/cache-A screen completed before the user requested saving the current work and shutting down Windows. All 10 resource/full-buffer GPU gates passed with zero differing words for the recompiled control and both candidates. The tested SM86 binary is SHA-256 6c43f695caba655e6a997f59c82f2c53b6517ac7e66041297ee3cd7bc033feea, compiled from CUDA source 7c58cc28819ad65e1c02ccb996f5c66a77630fb6.

At 220 W, the predeclared run used 360 seconds of warmup and A0/C1/A1/C2/A2 stages of 120 seconds each. The fixed final 30 seconds of each stage produced:

| Stage | Variant | T MAC/s | Mean GPU W |
| --- | --- | ---: | ---: |
| A0 | Control | 54.415082 | 219.812 |
| C1 | Interleaved fold issue | 52.650538 | 219.808 |
| A1 | Control | 54.150281 | 219.833 |
| C2 | L1 cache-A copy | 57.001979 | 219.817 |
| A2 | Control | 53.909221 | 219.833 |

All final windows passed the <=2 C thermal-range gate; control spread was 0.938358%. Against adjacent controls, fold issue observed -3.006749% throughput and -3.000554% board efficiency, so it was rejected. Cache-A observed **+5.501094% throughput and +5.508809% board efficiency**, qualifying only for longer confirmation. All six guarded stages, including warmup, ended at their prescribed duration with child exit 0 and restored power.

This is a provisional synthetic full-attempt screen relative to the open control. It is not a confirmed gain, a win over KRig, a candidate pool-acceptance result, or measured earnings. The longer A/B/A confirmation did not start: preflight detected foreign GPU clients and no confirmation task was created. The subsequent user pause takes precedence; no clients were killed or added to an allowlist.

Deferred-fold and unsigned unrolled-copy code is separately committed at d3dc28d69fe79423f572bbced0567f077162d85c and compiled into SHA-256 31f2097577c2121391e75ebf7ad7413b66763c20cc35e8976fb84c910e092a3f. Static disassembly/resource inspection is saved, but these variants have not passed GPU correctness or timing. Reduced static instruction counts are not a speed result. A combined unrolled-copy/cache-A variant has not yet been implemented.

The default production app remains SHA-256 41263293ace4ac4a9901ceb6538adc59d17e0fcb95586f4f48970e8d549d2f54 and is stopped. No fee, wallet, pool, original first-payout threshold or absolute deadline was changed. Shutdown preflight found no owned experiment/miner process, no task triggers, and an actual 370 W default/restored cap. No further benchmark was launched.

Windows evidence: D:\AI\Playgrounds\soat-miner\20261029-foldissue-iteration\screen\result.json, proof-review.json, screen-decision.json and shutdown-preflight.json. Follow-up build/static evidence: 20261029-deferredcopy-iteration. Resume from the existing continuation-checkpoint.json only after checking the original deadline and current GPU clients.
