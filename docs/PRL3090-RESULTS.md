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
