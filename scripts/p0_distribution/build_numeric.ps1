param([Parameter(Mandatory=$true)][string]$PrivateRoot)
$ErrorActionPreference='Stop'
# Dependency wheels only. This script does not package IVAD or change freeze state.
$numericRoot=(Resolve-Path -LiteralPath $PrivateRoot).Path
$manifest=Get-Content -LiteralPath (Join-Path $numericRoot 'source-acquisition.json') -Raw | ConvertFrom-Json
foreach($entry in $manifest){
 $archive=Join-Path $numericRoot ($entry.name+'-'+$entry.version+'.tar.gz')
 if((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256){throw 'Source archive hash mismatch'}
}
if(Test-Path R:\){throw 'R drive already exists; refusing to replace it'}
& subst.exe R: $numericRoot
if($LASTEXITCODE -ne 0){throw 'Temporary build drive could not be created'}
try {
 # f2py splits space-containing paths in this toolchain. The drive mapping changes
 # only the build path; no binary or LICENSE is renamed, removed, or modified.
 $batch=@'
@echo off
call R:\MSVC\VC\Auxiliary\Build\vcvars64.bat
if errorlevel 1 exit /b 1
set "PATH=R:\build-env\Scripts;%PATH%"
set "PKG_CONFIG_PATH=R:\build-env\Library\lib\pkgconfig"
cd /d R:\
R:\build-env\Scripts\python.exe -m pip install Cython==3.3.1
if errorlevel 1 exit /b 1
R:\build-env\Scripts\python.exe -m pip wheel R:\sources\numpy-2.5.4 --no-build-isolation --no-deps -Csetup-args=-Dblas=none -Csetup-args=-Dlapack=none -Csetup-args=-Dallow-noblas=true -w R:\wheels
if errorlevel 1 exit /b 1
R:\build-env\Scripts\python.exe -m pip install Cython==3.2.9 numpy==2.2.6
if errorlevel 1 exit /b 1
R:\build-env\Scripts\python.exe -m pip wheel R:\sources\scipy-1.18.1 --no-build-isolation --no-deps -Csetup-args=-D_without-fortran=true -Csetup-args=-Duse-pythran=false -Csetup-args=-Dblas=mkl-dynamic-lp64-seq -Csetup-args=-Dlapack=mkl-dynamic-lp64-seq -w R:\wheels
'@
 $command=Join-Path $numericRoot 'rebuild-numeric.cmd'
 Set-Content -LiteralPath $command -Value $batch -Encoding ascii
 & cmd.exe /c $command
 if($LASTEXITCODE -ne 0){throw 'Numeric build failed; original runtime remains unchanged'}
} finally { & subst.exe R: /D }
