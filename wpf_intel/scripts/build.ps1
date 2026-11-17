# SPDX-License-Identifier: Apache-2.0
param([switch]$Tests,[string]$OutputDirectory='build/dev',[ValidateSet('Development','Release')][string]$Configuration='Development')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
if(Test-Path -LiteralPath (Join-Path $root 'hotfix-evidence/isolation-baseline.json')){
 $env:TEMP=$env:TMP=Join-Path $root 'hotfix-cache/tmp'
 New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
}
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$compiler=Join-Path $fx 'csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '需要Windows内置.NET Framework 4.x开发编译器，禁止自动安装系统组件。' }
$out=[IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if(-not $out.StartsWith(([IO.Path]::GetFullPath($root)+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)){throw 'Build output must remain inside project'}
$exeName=if($Configuration -eq 'Release'){'IVAD.Annotator.exe'}else{'Ivad.Annotator.Dev.exe'}
$targetPath=Join-Path $out $exeName
if(Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -and [String]::Equals($_.ExecutablePath,$targetPath,[StringComparison]::OrdinalIgnoreCase)}){throw 'Annotator at target output is running: choose a new OutputDirectory; no replacement permitted'}
New-Item -ItemType Directory -Force -Path $out | Out-Null
$references=@('System.dll','System.Core.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Xaml.dll','System.Windows.Forms.dll','System.Drawing.dll','WPF/WindowsBase.dll','WPF/PresentationCore.dll','WPF/PresentationFramework.dll') | ForEach-Object { '/reference:'+(Join-Path $fx $_) }
$sources=@((Join-Path $root 'src/Ids/Ids.cs'),(Join-Path $root 'src/Ids/Work.cs'),(Join-Path $root 'src/Annotator/Media.cs'),(Join-Path $root 'src/Annotator/VideoJobs.cs'),(Join-Path $root 'src/Annotator/Workflow.cs'),(Join-Path $root 'src/Annotator/App.cs'))
$sources += (Join-Path $root 'src/Annotator/UiChecks.cs')
$sources += (Join-Path $root 'src/Annotator/Interface.cs'),(Join-Path $root 'src/Annotator/AppDiagnostics.cs'),(Join-Path $root 'src/Annotator/DeploymentChecks.cs')
$sources += (Join-Path $root 'src/Annotator/HotfixChecks.cs'),(Join-Path $root 'src/Annotator/HotfixAcceptance.cs'),(Join-Path $root 'src/Annotator/FrameBrowser.cs'),(Join-Path $root 'src/Ids/GeometryTransactions.cs'),(Join-Path $root 'src/Ids/FrameTransactions.cs')
$sources += (Join-Path $root 'src/Annotator/RangeFrameList.cs'),(Join-Path $root 'src/Annotator/QueueUi.cs'),(Join-Path $root 'src/Annotator/H45Checks.cs'),(Join-Path $root 'src/Ids/QueueTransactions.cs')
$sources += (Join-Path $root 'src/Ids/StableIdsConverter.cs')
$sources += (Join-Path $root 'src/Annotator/ViewportAndIdsUi.cs'),(Join-Path $root 'src/Annotator/IntegrationChecks.cs'),(Join-Path $root 'src/Annotator/IntegrationVersion.cs'),(Join-Path $root 'src/Annotator/BatchNormalChecks.cs')
$sources += (Join-Path $root 'src/Ids/NvidiaBridge.cs'),(Join-Path $root 'src/Annotator/NvidiaMedia.cs')
$sources += (Join-Path $root 'src/Annotator/NvidiaWorkspace.cs')
$staging=Join-Path $root ('build/compile/'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $staging | Out-Null
$stagedExe=Join-Path $staging $exeName
[string[]]$manifestArgs=if($Configuration -eq 'Release'){@('/win32manifest:'+(Join-Path $root 'src/Annotator/Portable.manifest'))}else{@()}
& $compiler /nologo /debug- /target:winexe /platform:x64 /optimize+ /utf8output ('/out:'+$stagedExe) ('/resource:'+(Join-Path $root 'src/Annotator/Theme.xaml')+',Ivad.Theme.xaml') @references @manifestArgs @sources
if($LASTEXITCODE -ne 0){throw '开发编译失败'}
$targetExe=Join-Path $out $exeName
$backup=$null
if(Test-Path -LiteralPath $targetExe){
 # Preserve the previous executable, including an image mapped by an open developer window.
 # No process is closed or killed, and no project data is moved.
 $history=Join-Path $root ('build/dev-history/'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Force -Path $history | Out-Null
 $backup=Join-Path $history 'Ivad.Annotator.Dev.exe'
 Move-Item -LiteralPath $targetExe -Destination $backup
}
try{Move-Item -LiteralPath $stagedExe -Destination $targetExe}catch{if($backup -and -not (Test-Path -LiteralPath $targetExe)){Move-Item -LiteralPath $backup -Destination $targetExe};throw}
if($Tests){
 $testSources=@((Join-Path $root 'src/Ids/QueueTransactions.cs'),(Join-Path $root 'src/Ids/Ids.cs'),(Join-Path $root 'src/Ids/Work.cs'),(Join-Path $root 'src/Annotator/Media.cs'),(Join-Path $root 'src/Annotator/VideoJobs.cs'),(Join-Path $root 'src/Full/TrainingAdapter.cs'),(Join-Path $root 'tests/Tests.cs'),(Join-Path $root 'tests/ExtendedTests.cs'),(Join-Path $root 'tests/MediaFixtures.cs'),(Join-Path $root 'tests/FixtureContainers.cs'))
 $testSources += (Join-Path $root 'src/Ids/NvidiaBridge.cs'),(Join-Path $root 'src/Annotator/NvidiaMedia.cs')
 $testSources += (Join-Path $root 'src/Ids/StableIdsConverter.cs'),(Join-Path $root 'src/Ids/GeometryTransactions.cs'),(Join-Path $root 'src/Ids/FrameTransactions.cs'),(Join-Path $root 'src/Annotator/Workflow.cs'),(Join-Path $root 'tests/WorkflowTests.cs')
 & $compiler /nologo /target:exe /platform:x64 /optimize+ /utf8output ('/out:'+(Join-Path $out 'Ivad.Tests.exe')) @references @testSources
 if($LASTEXITCODE -ne 0){throw '测试编译失败'}
 & (Join-Path $out 'Ivad.Tests.exe') (Join-Path $root 'build/test-data')
 if($LASTEXITCODE -ne 0){throw '测试失败'}
}
if($Configuration -eq 'Release'){Copy-Item -LiteralPath (Join-Path $root 'src/Annotator/Portable.config') -Destination ($targetExe+'.config');foreach($name in @('LICENSE','NOTICE')){Copy-Item -LiteralPath (Join-Path $root ('src/Annotator/'+$name)) -Destination (Join-Path $out $name)}}
Write-Output '开发构建完成（非安装包，未签名，发行冻结）'
