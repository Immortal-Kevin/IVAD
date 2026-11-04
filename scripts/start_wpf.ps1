param([Parameter(Mandatory=$true)][string]$Workspace,[string]$Project)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$boundary=[IO.Path]::GetFullPath($Workspace)
if($boundary.StartsWith($repo,[StringComparison]::OrdinalIgnoreCase)){throw 'Data workspace must be outside program directory'}
New-Item -ItemType Directory -Force -Path $boundary | Out-Null
$env:IVAD_IDS_CONTROLLED_ROOT=$boundary
$env:IVAD_NVIDIA_BRIDGE='1'
$env:IVAD_NVIDIA_PYTHON=Join-Path $repo '.venv-media-native-v2/Scripts/python.exe'
$env:IVAD_IPC_TOKEN=[Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N')
$env:PYTHONUTF8='1'
$exe=Join-Path $repo 'wpf_intel/build/dev/Ivad.Annotator.Dev.exe'
if(-not (Test-Path -LiteralPath $exe)){throw 'Run wpf_intel/scripts/build.ps1 first'}
Push-Location $repo
try{if($Project){& $exe --open-project $Project}else{& $exe}}finally{Pop-Location}
