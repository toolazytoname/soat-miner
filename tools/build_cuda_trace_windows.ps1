[CmdletBinding()]
param(
 [string]$CudaRoot='D:\Apps\CUDA\13.1.1',
 [string]$CuptiRoot='D:\Apps\CUPTI\13.1.115',
 [string]$VsRoot='D:\Apps\VSBuildTools2022'
)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$build=Join-Path $repo 'build\cupti-trace'
$vcvars=Join-Path $VsRoot 'VC\Auxiliary\Build\vcvars64.bat'
foreach($p in @($repo,$build,$vcvars,$CudaRoot,$CuptiRoot)){
 if($p -match '[%"!\r\n&|<>^]'){throw 'Unsupported cmd.exe metacharacter in build path'}
}
foreach($p in @($vcvars,(Join-Path $CuptiRoot 'include\cupti.h'),(Join-Path $CuptiRoot 'lib\cupti.lib'),(Join-Path $CudaRoot 'include\cuda.h'))){
 if(-not(Test-Path -LiteralPath $p)){throw "Missing build prerequisite: $p"}
}
New-Item -ItemType Directory -Path $build -Force | Out-Null
$source=Join-Path $PSScriptRoot 'cuda_activity_trace.cpp'
$dll=Join-Path $build 'cuda-activity-trace.dll'
$cmd=@"
@echo off
set "VSLANG=1033"
call "$vcvars" >nul
if errorlevel 1 exit /b 1
cd /d "$build"
cl /nologo /LD /EHsc /std:c++17 /O2 /MD /utf-8 /DWIN32_LEAN_AND_MEAN /I"$CudaRoot\include" /I"$CuptiRoot\include" "$source" /link /LIBPATH:"$CuptiRoot\lib" cupti.lib /OUT:"$dll"
exit /b %ERRORLEVEL%
"@
$batch=Join-Path $build 'build-trace.cmd'
[IO.File]::WriteAllText($batch,$cmd,[Text.UTF8Encoding]::new($false))
& $env:ComSpec /d /c $batch
if($LASTEXITCODE -ne 0){throw "Trace DLL build failed: $LASTEXITCODE"}
[ordered]@{
 BuiltAt=(Get-Date).ToString('o')
 SourceCommit=(& git -C $repo rev-parse HEAD).Trim()
 SourceChanges=@(& git -C $repo status --short)
 SourceSha256=(Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant()
 Executable=$dll
 Sha256=(Get-FileHash $dll -Algorithm SHA256).Hash.ToLowerInvariant()
 CuptiRoot=$CuptiRoot
 Notes='CPU build only. No injection environment set globally; no GPU work started.'
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $build 'build-receipt.json') -Encoding UTF8
Write-Host "Built $dll"
