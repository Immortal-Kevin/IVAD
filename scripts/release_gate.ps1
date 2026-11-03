# SPDX-License-Identifier: Apache-2.0
param([switch]$Integrated,[string]$OutputDirectory='build/integrated-release-20261103',[string]$EvidenceDirectory='integration/20261103/gate')
$ErrorActionPreference='Stop'
if($Integrated){& (Join-Path $PSScriptRoot 'integration_gate.ps1') -OutputDirectory $OutputDirectory -EvidenceDirectory $EvidenceDirectory;exit $LASTEXITCODE}
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
 $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
 & ./scripts/build.ps1 -Tests *> "governance/evidence/build-test-$stamp.log"
 $exe=Join-Path $root 'build/dev/Ivad.Annotator.Dev.exe'
 $refs=[System.Reflection.Assembly]::LoadFile($exe).GetReferencedAssemblies() | ForEach-Object { @{Name=$_.Name;Version=$_.Version.ToString();scope='external Windows .NET Framework assembly; not redistributed'} }
 $refs | ConvertTo-Json -Depth 5 | Set-Content governance/evidence/assembly_references.json -Encoding utf8
 $last=(Get-Content build/test-data/latest.txt -Raw).Trim()
 $uiOutput=Join-Path $last 'wpf-checks'
 $ui=Start-Process -FilePath $exe -ArgumentList @('--ui-check',('"'+$uiOutput+'"'),('"'+(Join-Path $last 'full.ids.zip')+'"')) -WindowStyle Hidden -PassThru
 if(-not $ui.WaitForExit(60000)){$ui.Kill();throw 'WPF内部控件检查超时（非真实GUI验收）'}
 if($ui.ExitCode -ne 0){throw "WPF内部控件检查失败：$uiOutput/results.json"}
 $source=Join-Path $last 'source'
 $shot=Join-Path $root 'governance/evidence/annotator-smoke.png'
 if(Test-Path -LiteralPath ($shot+'.error.txt')){Remove-Item -LiteralPath ($shot+'.error.txt')}
 $p=Start-Process -FilePath $exe -ArgumentList @('--smoke',('"'+$shot+'"'),('"'+$source+'"')) -WindowStyle Hidden -PassThru
 if(-not $p.WaitForExit(20000)){$p.Kill();throw 'UI启动测试超时'}
 if(Test-Path -LiteralPath ($shot+'.error.txt')){throw 'UI模拟流程失败，见error日志'}
 & .venvs/intel_infer/Scripts/python.exe -X utf8 scripts/governance/generate_documents.py
 if($LASTEXITCODE -ne 0){throw '合规材料生成失败'}
 & .venvs/intel_infer/Scripts/python.exe -X utf8 scripts/governance/release_gate.py
 if($LASTEXITCODE -ne 0){throw 'Release Gate发现工程失败；详情见governance/RELEASE_READINESS.md'}
 if(Test-Path -LiteralPath 'governance/evidence/portable-candidate.json'){
  & .venvs/intel_infer/Scripts/python.exe -X utf8 scripts/governance/portable_package.py verify
  if($LASTEXITCODE -ne 0){throw '实际便携ZIP内容审计失败'}
 }
} catch {
 $failure=@{recorded_utc=[DateTime]::UtcNow.ToString('o');engineering_status='FAIL';release_frozen=$true;products=@{Annotator='BLOCKED';'Full/NVIDIA'='BLOCKED'};error=$_.ToString();build_log="governance/evidence/build-test-$stamp.log"}
 $failure | ConvertTo-Json -Depth 6 | Set-Content governance/evidence/release_gate.json -Encoding utf8
 $failure | ConvertTo-Json -Depth 6 | Set-Content "governance/evidence/gate-failure-$stamp.json" -Encoding utf8
 @("# Release Readiness — 本次执行失败",'', 'Annotator: **BLOCKED**；正式发行冻结保持。', '', $_.ToString(), '', "原始日志：evidence/build-test-$stamp.log。上一轮PASS不能替代本轮结果。") | Set-Content governance/RELEASE_READINESS.md -Encoding utf8
 throw
} finally {Pop-Location}
