[CmdletBinding()]
param(
    [string]$CudaRoot = 'D:\Apps\CUDA\13.1.1',
    [string]$VsRoot = 'D:\Apps\VSBuildTools2022',
    [string]$BuildDirectory = '',
    [switch]$GpuTests,
    [switch]$AmpereCandidates,
    [switch]$KernelIteration
)
$ErrorActionPreference = 'Stop'
if ($KernelIteration -and -not $GpuTests) { throw 'KernelIteration requires GpuTests so the correctness targets exist.' }
$targetOption = if ($KernelIteration) { '--target soat-miner test-pearl-mining-shape test-pearl-kernel-resources' } else { '' }
$repoRoot = Split-Path $PSScriptRoot -Parent
if (-not $BuildDirectory) { $BuildDirectory = Join-Path $repoRoot 'build\prl3090-baseline' }
$vcvars = Join-Path $VsRoot 'VC\Auxiliary\Build\vcvars64.bat'
$cmake = Join-Path $repoRoot '.venv\Lib\site-packages\cmake\data\bin\cmake.exe'
$ninja = Join-Path $repoRoot '.venv\Scripts\ninja.exe'
$nvcc = Join-Path $CudaRoot 'bin\nvcc.exe'
foreach ($path in @($repoRoot,$BuildDirectory,$vcvars,$cmake,$ninja,$nvcc)) {
    if ($path -match '[%"!\r\n&|<>^]') { throw 'Build paths must not contain cmd.exe metacharacters.' }
}
foreach ($path in @($vcvars,$cmake,$ninja,$nvcc)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing build tool: $path" }
}
New-Item -ItemType Directory -Path $BuildDirectory -Force | Out-Null
$gpuOption = if ($GpuTests) { 'ON' } else { 'OFF' }
$ampereOption = if ($AmpereCandidates) { 'ON' } else { 'OFF' }
$command = @"
@echo off
set "VSLANG=1033"
set "CL=/utf-8"
call "$vcvars" >nul
if errorlevel 1 exit /b 1
set "PATH=$CudaRoot\bin;%PATH%"
"$cmake" -S "$repoRoot" -B "$BuildDirectory" -G Ninja -DCMAKE_MAKE_PROGRAM="$ninja" -DCMAKE_CUDA_COMPILER="$nvcc" -DCUDAToolkit_ROOT="$CudaRoot" -DCMAKE_CUDA_ARCHITECTURES=86-real -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DSOAT_PEARL_ONLY_BUILD=ON -DSOAT_ENABLE_PEARL_GPU_TESTS=$gpuOption -DSOAT_EXPERIMENTAL_SM86_TILES=$ampereOption
if errorlevel 1 exit /b 1
"$cmake" --build "$BuildDirectory" --parallel 1 $targetOption
exit /b %ERRORLEVEL%
"@
$commandFile = Join-Path $BuildDirectory 'build-prl3090.cmd'
[IO.File]::WriteAllText($commandFile,$command,[Text.UTF8Encoding]::new($false))
& $env:ComSpec /d /c $commandFile
if ($LASTEXITCODE -ne 0) { throw "Build failed: $LASTEXITCODE" }
$exe = Join-Path $BuildDirectory 'soat-miner.exe'
$receipt = [ordered]@{
    BuiltAt = (Get-Date).ToString('o')
    SourceCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
    SourceChanges = @(& git -C $repoRoot status --short)
    CudaCompiler = $nvcc
    Architecture = '86-real'
    ExperimentalSm86Tiles = [bool]$AmpereCandidates
    Executable = $exe
    Sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    Notes = 'Build only; no miner, benchmark or GPU test was started.'
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $BuildDirectory 'build-receipt.json') -Encoding UTF8
Write-Host "Built $exe"
