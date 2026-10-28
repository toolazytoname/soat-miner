# RTX 3090 counter profiling preparation

The portable NVIDIA Nsight Compute tool was extracted on Windows only. Its [official CUDA 13.1.1 redistribution manifest](https://developer.download.nvidia.com/compute/cuda/redist/redistrib_13.1.1.json) pins the Windows 2025.4.1.2 archive at SHA-256 `cb26a33427f34606b063166538f00f8eced3e0bc1c5bc21c1385d0e270ceefab`. `ncu --version` reports public-release 2025.4.1.0, build 37053803. The CLI Authenticode signature is Valid, NVIDIA Corporation. No driver, registry, system PATH or security changes were made. Installation receipt: `D:\Apps\NsightCompute\2025.4.1.2\install-receipt.json`; archive: `D:\Downloads\Installers\NsightCompute\2025.4.1.2`.

`tools/setup_portable_ncu.py` reproduces the official ZIP retrieval and checksum verification. It refuses to overwrite an existing install. No profiler or GPU benchmark is automatically launched by installation.

## Owned process tree

A profiler launches a GPU child. The ordinary direct-child experiment guard must not wrap this tree. `tools/owned_job.py` instead creates the root suspended, assigns it to a kill-on-close Windows Job Object, then resumes it. Inherited children remain in the job; no breakaway is enabled. Stop acts on that job only. Two real Windows process tests verify the expected child membership, cleanup of inherited children, survival of an unrelated CPU process, normal exit status and environment round-trip. Python virtual-environment redirectors can add more processes, so the guard does not assume exactly two PIDs.

This follows the documented [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) and [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject) behavior. The controller waits for both zero active job processes and the parent process exit signal before treating cleanup as finished.

## Bounded profiling entry

`tools/run_ncu_profile.py` shares the mining mutex, refuses a busy GPU, uses at most 220 W, and monitors core/hotspot/memory temperatures and new GPU applications. A manual stop is either its output `stop.request` or a newly updated `D:\Apps\KRig\Runtime\cancel.request`. All owned profiler/target children are stopped before restoring the initial board cap; an external cap change is preserved. Six hardware-free fault checks cover thermal/manual/GPU conflict/sensor failure/non-finite sensor/external power cases. These are separate from the real child-process tests.

The CLI explicitly passes `--clock-control none`, `--cache-control none`, kernel replay, one selected GEMM launch after 64 matching launches, and `--kill yes`. See [NVIDIA CLI documentation](https://docs.nvidia.com/nsight-compute/2025.4/NsightComputeCli/index.html). Counter replay is instrumentation; its duration and throughput must not be sold as normal mining hashrate. The target is the existing synthetic benchmark, with no pool or wallet.

```powershell
.\.venv\Scripts\python.exe tools\test_owned_job.py
.\.venv\Scripts\python.exe tools\test_ncu_profile_guard.py
.\.venv\Scripts\python.exe tools\run_ncu_profile.py --output D:\AI\Playgrounds\soat-miner\YOUR-RUN\ncu-fixed --check-only
```

Remove `--check-only` only when prior GPU work has ended and this explicit profile is intended. Use a fresh output directory. A successful run requires the report file and a clean, restored-power exit, and exports counter CSV for inspection. Counter permission or driver compatibility errors are recorded; the tool does not loosen driver security or change the driver to hide such errors.

At this preparation checkpoint, the actual profiler has **not run**. A/B/A source comparison is still in progress. Actual hardware counter results and any resulting optimization require subsequent validation.
