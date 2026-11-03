# SPDX-License-Identifier: Apache-2.0
param([string]$OutputDirectory='build/integrated-release-20261103',[string]$EvidenceDirectory='integration/20261103/gate')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$out=[IO.Path]::GetFullPath((Join-Path $root $EvidenceDirectory))
if(Test-Path -LiteralPath $out){throw 'Choose a fresh evidence directory'}
New-Item -ItemType Directory -Path $out | Out-Null
$results=[Collections.Generic.List[object]]::new()
$exe=Join-Path $root ($OutputDirectory+'/IVAD.Annotator.exe')
function Run-OwnTest([string]$Name,[string[]]$TestArgs){
 try{
  $child=Start-Process -FilePath $exe -ArgumentList $TestArgs -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -PassThru
  if(-not $child.WaitForExit(180000)){$child.Kill();throw 'Owned test child timeout'}
  if($child.ExitCode -ne 0){throw "Exit code $($child.ExitCode)"}
  $results.Add(@{name=$Name;status='PASS'})
 }catch{$results.Add(@{name=$Name;status='FAIL';error=$_.ToString()})}
 $results|ConvertTo-Json -Depth 6|Set-Content (Join-Path $out 'commands.json') -Encoding utf8
}
try{& (Join-Path $PSScriptRoot 'build.ps1') -Configuration Release -OutputDirectory $OutputDirectory -Tests *> (Join-Path $out 'build-tests.log');$results.Add(@{name='release-build-service-tests';status='PASS'})}catch{$results.Add(@{name='release-build-service-tests';status='FAIL';error=$_.ToString()})}
if(Test-Path -LiteralPath $exe){
 $last=(Get-Content -LiteralPath (Join-Path $root 'build/test-data/latest.txt') -Raw).Trim()
 Run-OwnTest 'WPF-regressions' @('--ui-check',('"'+$out+'\wpf"'),('"'+$last+'\full.ids.zip"'))
 Run-OwnTest 'H1-H3-transactions' @('--hotfix-check',('"'+$out+'\hotfix"'))
 Run-OwnTest 'H4-H5-selection-queue' @('--h45-check',('"'+$out+'\h45"'))
 Run-OwnTest 'batch-normal-925-regressions' @('--batch-normal-check',('"'+$out+'\batch-normal"'))
 Run-OwnTest 'batch-normal-new-process-reopen' @('--batch-normal-reopen',('"'+$out+'\batch-normal"'))
 Run-OwnTest 'deployment-sequence' @('--deployment-check',('"'+$out+'\deployment"'))
 Run-OwnTest 'deployment-new-process-reopen' @('--deployment-reopen',('"'+$out+'\deployment"'))
 $realVideo=Get-ChildItem -LiteralPath (Join-Path $root 'projects') -File -Filter '*.mp4' | Select-Object -First 1
 if($realVideo){
  Run-OwnTest 'real-video-integration' @('--integration-check',('"'+$out+'\real-video"'),('"'+$realVideo.FullName+'"'))
  Run-OwnTest 'real-video-restart-and-export' @('--integration-reopen',('"'+$out+'\real-video"'))
 }else{$results.Add(@{name='real-video-integration';status='MISSING'})}
 try{
  $refs=[Reflection.Assembly]::LoadFile($exe).GetReferencedAssemblies()|ForEach-Object{@{name=$_.Name;version=$_.Version.ToString()}}
  $refs|ConvertTo-Json|Set-Content (Join-Path $out 'assembly-references.json') -Encoding utf8
  $allowed=@('mscorlib','System','System.Core','System.Web.Extensions','System.IO.Compression','System.IO.Compression.FileSystem','System.Xaml','System.Windows.Forms','System.Drawing','WindowsBase','PresentationCore','PresentationFramework')
  if(@($refs|Where-Object{$_.name -notin $allowed}).Count){throw 'New unreviewed dependency'}
  $results.Add(@{name='changed-dependencies-system-only';status='PASS'})
 }catch{$results.Add(@{name='changed-dependencies-system-only';status='FAIL';error=$_.ToString()})}
}
$failed=@($results|Where-Object{$_.status -ne 'PASS'}).Count
@{scope='Integrated Intel Annotator local x64 release regression; no public distribution/installer/Full audit';failed=$failed;commands=$results;exe=$exe;sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash;native_gui='SEPARATE_ACCEPTANCE_REQUIRED'}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $out 'gate.json') -Encoding utf8
Write-Output "Integrated gate failed commands: $failed; evidence $out"
if($failed){exit 1}else{exit 0}
