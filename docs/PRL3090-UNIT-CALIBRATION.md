# PRL3090: calibrating KRig and SOAT rate units

This receipt applies to the pinned Windows RTX 3090 fixture: KRig 1.5.12 and SOAT executable SHA-256 `820d7f63ca3d4806f8bb88ab514ed5a5078618c1a4cb0b459cc8c63f47f6f35b`. It establishes a rate-unit conversion. The short synthetic runs are not a steady mining benchmark and do not prove earnings.

## Measured work

| Backend | M x N x K, rank | MACs per GEMM launch | NVIDIA INT8 operation count, each of 3 samples |
| --- | --- | ---: | ---: |
| SOAT | 4096 x 65536 x 2048, 128 | 549,755,813,888 | 1,099,511,627,776 |
| KRig | 4096 x 65536 x 4096, 128 | 1,099,511,627,776 | 2,199,023,255,552 |

The `sm__ops_path_tensor_src_int8.sum` count is exactly twice the declared dense matrix MAC work in both cases. We calibrated the conversion on known source work before applying it to KRig.

KRig's own debug statistics give an independent equation. One actual line reports 59.69 iterations/s, 65.63 tmads/s and 65.63 TH/s. Its declared matrix dimensions imply:

```text
59.69 * 4096 * 65536 * 4096 / 1e12 = 65.62984906194944 T MAC/s
```

All six available native statistics rows match this equation within displayed rounding. A separate CUPTI activity capture counts the matching GEMM launches without hardware-counter replay and corroborates the scale. Thus **KRig TH/s converts 1:1 to T MAC/s for this pinned configuration**. Other algorithms, ranks, binaries and configurations require their own check.

## Reproduce

Build the helper on Windows with the existing CUDA 13.1.1 / VS Build Tools environment and the checksum-verified CUPTI 13.1.115 component:

```powershell
.\tools\build_cuda_trace_windows.ps1
.\.venv\Scripts\python.exe .\tools\test_unit_calibration.py -v
.\.venv\Scripts\python.exe .\tools\test_unit_normalization.py -v
.\.venv\Scripts\python.exe .\tools\run_unit_calibration.py --backend soat --mode trace --seconds 30 --output D:\AI\Playgrounds\soat-miner\NEW-RUN --check-only
```

The last command is a CPU preflight. Real captures must run through a bounded, elevated task on the logged-in Windows desktop after stopping other GPU work. The runner acquires the existing mining mutex, pins the executable hash, caps the board at 220 W, checks the original payout/deadline, yields to other GPU clients and restores the previous cap after its owned Windows Job exits. It does not edit production configuration or global injection environment variables.

The CUPTI DLL records launch names, geometries, timestamps and dropped-record counts. It records no CUDA arguments, GPU memory, wallet signing material or kernel machine code. Collection ends on its own timer; it makes no CUDA calls from Windows DLL teardown. Nsight Compute is used separately for three exact operation-count samples. Counter replay timings are never treated as steady mining performance.

The local mock issues an infeasible synthetic target, with no real pool credits. KRig identifies localhost as a 3% developer-fee route; this setting is disclosed and is not bypassed. Real-pool fee-adjusted work is a separate comparison.

Evidence stays on Windows under `D:\AI\Playgrounds\soat-miner\20261028-prl3090\closed-source-comparison`. Run `tools/analyze_unit_calibration.py --root <that-directory> --output <new-summary.json>` against the preserved fixture. The analyzer rejects missing counters, lost records, inconsistent work geometry inside the measured window and an incorrect native rate equation.

The first source capture stopped safely on a Windows status-file sharing conflict. The second produced a complete trace (32,881 kernels, zero dropped records, zero CUPTI errors), but its runner initially classified the expected TCP reset after child termination as a mock error. The original failed receipt is retained. A separate `acceptance-review.json` validates only that raw capture; it is not relabeled as a clean runner execution. Both runner issues have CPU regression coverage. The later source counter, KRig activity and KRig counter runs completed normally, with power restored.

Official references: [CUPTI 13.1.1 Activity API](https://docs.nvidia.com/cupti/13.1.1/main/main.html), [Nsight Compute 2025.4 profiling guide](https://docs.nvidia.com/nsight-compute/2025.4/ProfilingGuide/index.html), [NVIDIA CUDA 13.1.1 component manifest](https://developer.download.nvidia.com/compute/cuda/redist/redistrib_13.1.1.json).
