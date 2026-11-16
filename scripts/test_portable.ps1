# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
 & .venvs/intel_infer/Scripts/python.exe -X utf8 scripts/governance/portable_package.py verify
 if($LASTEXITCODE -ne 0){throw 'ZIP审计必须先通过'}
 $candidate=Get-Content governance/evidence/portable-candidate.json -Raw | ConvertFrom-Json
 $testRoot=Join-Path ([IO.Path]::GetTempPath()) ('IVAD 独立部署 '+[Guid]::NewGuid().ToString('N').Substring(0,8))
 if(Test-Path -LiteralPath $testRoot){throw '拒绝复用测试目录'}
 New-Item -ItemType Directory -Path $testRoot | Out-Null
 $extracted=Join-Path $testRoot '软件 中文路径'
 Expand-Archive -LiteralPath (Join-Path $root $candidate.zip) -DestinationPath $extracted
 $app=Join-Path $extracted 'IVAD-Annotator'
 $exe=Join-Path $app 'IVAD.Annotator.exe'
 if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $candidate.binary_sha256){throw '解压EXE hash不符'}
 foreach($line in Get-Content -LiteralPath (Join-Path $app 'checksums.sha256') -Encoding utf8){
  $hash,$name=$line -split '  ',2
  if((Get-FileHash -LiteralPath (Join-Path $app $name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash){throw "解压文件hash不符：$name"}
 }
 function Invoke-Isolated([string]$arguments) {
  $info=[Diagnostics.ProcessStartInfo]::new()
  $info.FileName=$exe;$info.Arguments=$arguments;$info.WorkingDirectory=$testRoot
  $info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
  $info.EnvironmentVariables['PATH']=(Join-Path $env:WINDIR 'System32')+';'+$env:WINDIR
  foreach($key in @('VIRTUAL_ENV','PYTHONPATH','PYTHONHOME','CONDA_PREFIX','CONDA_DEFAULT_ENV','DOTNET_ROOT','DOTNET_ROOT_X64','MSBuildSDKsPath')){$info.EnvironmentVariables.Remove($key)}
  $process=[Diagnostics.Process]::Start($info)
  try {if(-not $process.WaitForExit(60000)){$process.Kill();$process.WaitForExit(5000) | Out-Null;throw '独立目录测试超时'};return $process.ExitCode}
  finally {$process.Dispose()}
 }
 $data=Join-Path $testRoot '验收 数据'
 $first=Invoke-Isolated ('--deployment-check "'+$data+'"')
 $reopen=$null
 if($first -eq 0){$reopen=Invoke-Isolated ('--deployment-reopen "'+$data+'"')}
 $aclResult='NOT TESTED'
 $denied=Join-Path $testRoot '写入拒绝 测试目录'
 New-Item -ItemType Directory -Path $denied | Out-Null
 $oldAcl=Get-Acl -LiteralPath $denied
 try {
  $acl=Get-Acl -LiteralPath $denied
  $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
  $rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,[Security.AccessControl.FileSystemRights]::Write,[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Deny)
  $acl.AddAccessRule($rule);Set-Acl -LiteralPath $denied -AclObject $acl
  $denialExit=Invoke-Isolated ('--deployment-check "'+(Join-Path $denied '不可写项目')+'"')
  if($denialExit -eq 0 -or -not (Select-String -LiteralPath (Join-Path $app 'logs/startup-errors.log') -Pattern 'UnauthorizedAccessException' -Quiet)){throw '只读目录未产生可验证的权限拒绝'}
  $aclResult='PASS: actual NTFS write denial reported; no elevation or project overwrite'
 } finally {Set-Acl -LiteralPath $denied -AclObject $oldAcl}
 $checks=if(Test-Path -LiteralPath (Join-Path $data 'results.json')){Get-Content (Join-Path $data 'results.json') -Raw | ConvertFrom-Json}else{$null}
 $restart=if(Test-Path -LiteralPath (Join-Path $data 'reopen-results.json')){Get-Content (Join-Path $data 'reopen-results.json') -Raw | ConvertFrom-Json}else{$null}
 $result=@{recorded_utc=[DateTime]::UtcNow.ToString('o');candidate_sha256=$candidate.zip_sha256;status=$(if($first -eq 0 -and $reopen -eq 0 -and $checks.failed -eq 0 -and $restart.failed -eq 0){'PASS'}else{'FAIL'});test_root=$testRoot;exe=$exe;data=$data;first_exit=$first;restart_exit=$reopen;checks=$checks;restart=$restart;zip_integrity='PASS';acl_denial=$aclResult;physical_ctrl_s='NOT TESTED';native_gui='NOT TESTED';other_computers='NOT TESTED';isolation='fresh TEMP directory outside repository; PATH Windows only; no venv/SDK variables; child EXE resolves itself; loaded assembly/module evidence in runtime.json';missing_runtime_machine='NOT TESTED'}
 $result | ConvertTo-Json -Depth 12 | Set-Content governance/evidence/portable-independent.json -Encoding utf8
 $result | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $testRoot 'independent-result.json') -Encoding utf8
 Write-Output (@{status=$result.status;test_root=$testRoot;checks=$checks.passed;restart_checks=$restart.passed;acl=$aclResult} | ConvertTo-Json -Compress)
 if($result.status -ne 'PASS'){throw ('独立部署验收失败：'+$testRoot)}
} finally {Pop-Location}
