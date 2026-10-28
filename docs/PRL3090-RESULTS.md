# RTX 3090 results and limits

Measured on 2026-10-28: one RTX 3090 24 GB, Windows, NVIDIA driver 581.29, native SM86 SASS, CUDA compiler 13.1.115, MSVC 19.44, a 220 W board-power cap, automatic clocks and fans. Source baseline: `blindrun/soat-miner@48defc8dcb697cb64d8d1702c35efb57112b57ac`. Results apply to this machine and this short experiment.

## Correctness and transport

- Four original K32/async transcript comparisons passed.
- Twelve corrected K64/K32/async/SM86-candidate comparisons passed at 1024x1024 and 4096x32768, with K=2048, rank=128 and zero differing transcript words.
- Eleven host-only guard checks, four local TLS checks and six payout/deadline checks passed.
- Three CPU CTest targets passed, including the upstream Pearl pool payload/target tests after a portable C++ fix for MSVC.
- A 600-second source-miner pool probe used the original PRL Kryptex pool over verified TLS 1.3. It recorded **3 accepted shares, 0 rejected**, including a verified reconnect. The guard stopped the child at its duration limit and restored the original 370 W cap. The pool wallet and settlement mode were preserved. This establishes short compatibility, not long-term stability or a completed payout experience.

## First configuration comparison

All rates below are the miner's own synthetic **T MAC/s** counter; no shares are produced in these benchmark runs.

| Run | Mean rate | Core temperature in the reporting window | Selected configuration |
| --- | ---: | --- | --- |
| Original compute, initial run | 47.96 | warming toward 74 C | ptx K32 4x4/4x2 |
| Patched build, automatic selection | 48.23 | 72-74 C | 2 stages, group 8, K64 |
| SM86 candidates only | 49.12 | 68-72 C | 2 stages, group 8, K64 |
| Original compute, pinned repeat | 47.53 | 74-75 C | ptx K32 4x4/4x2 |

The thermal windows differ, particularly for the candidates-only run. The small apparent gain is **not a proven speedup**. Prior KRig observations were about 59 T MAC/s at 220 W, but those observations are not a matched live A/B test. The source implementation is retained for investigation, and is not silently substituted for a faster production backend.

## Next gate

Sample actual preparation/GEMM/scan/readback costs and optimize the dominant stage before another controlled comparison. Keep both positive and negative results. Every arithmetic or scheduling change must preserve transcript equality and accepted pool proofs. Hardware-counter profiling may require additional tooling; no driver, clock, voltage, security or global CUDA change was made for these measurements.

Raw receipts, telemetry and executable hashes remain in `D:\AI\Playgrounds\soat-miner\20261028-prl3090`; they are not committed as model-independent performance claims or bundled binaries.


## Deeper resource and occupancy experiments (2026-10-28)

The opt-in sampled stage profiler measured GEMM at 10.37--10.71 ms of 11.14--11.51 ms attempt wall time on this RTX 3090 at 220 W: approximately 93%. Preparation was about 0.56--0.57 ms; scan and readback were much smaller. This is a measured stage breakdown, not a performance claim from another GPU or from theoretical Tensor Core peak.

A new `test-pearl-kernel-resources` executable queries compiled attributes and CUDA theoretical occupancy (not measured active occupancy):

| Variant | Threads | Registers/thread | Dynamic shared/block | Resident blocks/SM | Theoretical occupancy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original K32, 256x128 | 512 | 128 | 55,296 B | 1 | 33.33% |
| SM86 S2 K64, 128x128 | 256 | 126 | 40,960 B | 2 | 33.33% |
| SM86 S3 K64, 128x128 | 256 | 142 | 61,440 B | 1 | 16.67% |
| S2 K64, 64x128 | 256 | 90 | 30,720 B | 2 | 33.33% |
| S2 K64, 64x128, min 3 blocks | 256 | 79 | 30,720 B | 3 | 50.00% |
| S2 K32, 64x128, min 3 blocks | 256 | 80 | 18,432 B | 3 | 50.00% |
| Fixed mining K/rank, S2 K64, 128x128 | 256 | 124 | 40,960 B | 2 | 33.33% |

All listed kernels report zero local bytes per thread. The optional launch bound constrains registers; smaller blocks reduce reuse, so a higher occupancy is not proof of a faster algorithm. A 240-second first screen still selected the existing S2 128x128 configuration, rather than one of the smaller-block candidates. Its approximately 49.88 T MAC/s tail mean is a synthetic warm-up screen; it is not a matched A/B/A gain or paid pool hashrate.

Eight additional candidates were checked against the independent synchronous transcript oracle at both 1024x1024 and 4096x65536, with K=2048 and rank=128: four smaller block/stage variants, two minimum-residency variants, and two fixed-mining-parameter variants. All 16 complete-buffer comparisons had zero differing words, and each guarded run restored the original cap. The fixed specialization returns without a transcript on incompatible K/rank/write-C arguments so normal tuning and self-checks reject it.

The resource helper and candidates remain experimental and SM86-only in the miner. The template defaults preserve the generic kernel. `SOAT_PEARL_TILE` retains prefix matching and now also supports `=full configuration name` for exact experiment pins. `SOAT_PEARL_PROFILE=1` enables sampled profiling; `0` and unset disable it. An earlier screen had profiling enabled by the old presence-only switch even when set to `0`; that screen is retained and not represented as an uninstrumented comparison.

Matched stable-temperature A/B/A and actual pool validation of the new specializations are still pending at this checkpoint. The earlier successful TLS pool probe used the previously validated generic S2 kernel and does not establish acceptance of every new specialization.

Evidence remains on Windows in `D:\AI\Playgrounds\soat-miner\20261028-prl3090`: `occupancy-correctness-result.json`, `occupancy-b3-correctness-result.json`, `fixed-correctness-result.json`, individual guard receipts, full transcript logs, and preserved build directories. CPU-only CTest runs must use `ctest --test-dir build/prl3090-fixed -LE gpu --output-on-failure`; a broad CTest invocation with GPU tests enabled also runs the small CUDA cases.


## Single-fold candidate (GPU gate passed; throughput still unproven)

An additional opt-in specialization makes one algebraic simplification at fixed mining K/rank: 2048/128 produces exactly sixteen folds, and each of the first sixteen lanes writes its transcript slot once. Thus its old slot is zero, and `rotate_left(0,13) XOR v` equals `v`. Full-warp reduction remains outside the lane predicate. A compile-time branch chooses this path without materializing the generic branch; the generic default is preserved, and a static assertion requires the fixed-mining specialization.

The 128x128 and 64x128/min-three-block variants compiled for SM86 in `build/prl3090-fold`. The subsequent explicit GPU suite passed all six full-buffer comparisons at 256x768, 1024x1024 and 4096x65536 with zero differing words. Speed and pool acceptance remain separate gates. The ongoing A/B/A uses the earlier preserved baseline and fixed-K/rank binaries, not this new build.

`tools/run_correctness_suite.py` is the reusable gate for these candidates. It runs the resource helper and complete-buffer oracle comparisons at 256x768 (a short M swizzle group), 1024x1024, and 4096x65536, with each direct GPU child under the power/temperature/mutex guard. Three hardware-free fault tests confirm that a guard failure, missing power restore, or zero exit without a full-buffer result aborts the suite. The suite is not an extra automatic GPU workload; run it only after the current comparison has ended.


### Static code inspection of the single-fold build

Official CUDA 13.1.115 `cuobjdump` and `nvdisasm` were obtained from the same SHA-256-pinned NVIDIA manifest into `D:\Apps\CUDAInspectors\13.1.1`, without changing the installed compiler, driver or global PATH. `tools/setup_cuda_inspectors.py` and `tools/inspect_singlefold_sass.py` reproduce installation and static inspection. These tools inspect binary files and do not run a GPU workload.

Within the same `prl3090-fold` binary, the fixed generic 128x128 kernel has 1,052 static SASS instructions; the single-fold version has 1,028. The latter has 16 fewer SHF and 16 fewer LOP3 instructions, but 16 more SEL instructions and several fewer uniform operations. Both use 124 registers and report zero stack/local bytes. This establishes a compiled-code change, not a dynamic instruction saving, correctness proof or speedup. The later six-case GPU validation passed; actual counters were also collected. A matched end-to-end speedup and pool acceptance remain separate questions.


## First stable A/B/A: no demonstrated improvement

At 220 W, with at least three minutes of cooldown before each case and 720 seconds per case, the final 180-second windows were:

| Case | Configuration | Mean synthetic T MAC/s | Temperature window steady | Original cap restored |
| --- | --- | ---: | --- | --- |
| A1 | Original K32, 256x128, 3 stages | 48.0367 | Yes | Yes |
| B | Fixed K/rank, K64, 128x128, 2 stages | 47.8331 | Yes | Yes |
| A2 | Original K32, 256x128, 3 stages | 47.4953 | Yes | Yes |

B was +0.1404% relative to the mean of the bracketing A cases; A1/A2 differed by 1.1334%. This does **not demonstrate a speed gain**. The controlled comparison completed, all three thermal windows passed the stated drift gate, and every case restored 370 W. These are synthetic attempt rates, not pool-credited earnings.

## Measured hardware counters and larger-block experiments

Nsight Compute actually profiled the original, fixed small-block, single-fold small-block and three larger-block candidates. Each profile used the owned job guard, explicit `--clock-control none`, no pool, and restored the original cap. The reports used kernel replay with uncontrolled caches/clocks, so replay duration is not normal mining throughput. The following are diagnostic samples, not a matched speed comparison:

| Kernel | L2 throughput % | Tensor-pipe active % | Long-scoreboard ratio | Math-pipe-throttle ratio |
| --- | ---: | ---: | ---: | ---: |
| Original K32 256x128 S3 | 58.26 | 57.86 | 0.0032 | 3.6595 |
| Fixed K64 128x128 S2 | 87.75 | 69.73 | 2.1900 | 2.3535 |
| Single-fold K64 128x128 S2 | 87.96 | 68.03 | 2.2638 | 2.3887 |
| Fixed K64 256x128 S2 | 53.86 | 54.25 | 2.6704 | 5.3584 |
| Single-fold K64 256x128 S2 | 53.62 | 53.55 | 2.5450 | 5.4679 |
| Single-fold K64 256x128 S3 | 65.94 | 65.22 | 0.0980 | 5.4983 |

The ratio columns are the exact `smsp__average_warps_issue_stalled_*_per_issue_active.ratio` metrics, not percentages. Higher L2 utilization alone does not establish a bottleneck; the substantially higher long-scoreboard value in the small two-CTA case is an additional indication of memory dependency waits. The larger three-stage case retains B reuse and hides much of that wait, so it is selected for the next proper thermal A/B/A rather than declaring its replay time a win.

All three larger 256x128 variants passed nine complete-buffer oracle comparisons (three shapes each), zero differing words. They use 512 threads, 120 registers/thread and zero local/stack bytes; S2 uses 61,440 B dynamic shared memory and S3 uses 92,160 B. Each has one theoretical resident block per SM, 33.33% theoretical occupancy. Their added memory-table profiles reported zero shared bank conflicts, including the LDGSTS counter; no bank-conflict speedup is claimed or implemented from speculation.

Evidence includes `thermal-aba-summary.json`, `singlefold-correctness-active.json`, `large-correctness-active.json`, `ncu-original-active.json`, `ncu-fixed-active.json`, `ncu-singlefold-active.json`, and `ncu-large-active.json` under the Windows run root. Follow each active JSON's output path to immutable receipts, raw CSV, profiler reports and complete verifier output.

`test-pearl-gpu-context` is a separate explicit live-yield test target, not a CTest registration. It performs one 8 MiB memset and idles for 5..30 seconds, allowing the manager's incoming-GPU policy to be tested without a second heavy compute workload.
