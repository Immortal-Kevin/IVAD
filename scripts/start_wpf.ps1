param([Parameter(Mandatory=$true)][string]$Workspace,[string]$Project,[switch]$InitializeWorkspace,[string]$RFWorkerPython)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$argsList=@('-m','ivad_app','--workspace',$Workspace)
if($Project){$argsList+=@('--project',$Project)}
if($InitializeWorkspace){$argsList+='--initialize-workspace'}
if($RFWorkerPython){$argsList+=@('--rf-worker-python',$RFWorkerPython)}
Push-Location $repo
try{& (Join-Path $repo '.venv-media-native-v2/Scripts/python.exe') @argsList}finally{Pop-Location}
