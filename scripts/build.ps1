# SPDX-License-Identifier: Apache-2.0
param([switch]$Tests)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$compiler=Join-Path $fx 'csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '需要Windows内置.NET Framework 4.x开发编译器，禁止自动安装系统组件。' }
$out=Join-Path $root 'build/dev'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$references=@('System.dll','System.Core.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Xaml.dll','System.Windows.Forms.dll','System.Drawing.dll','WPF/WindowsBase.dll','WPF/PresentationCore.dll','WPF/PresentationFramework.dll') | ForEach-Object { '/reference:'+(Join-Path $fx $_) }
$sources=@((Join-Path $root 'src/Ids/Ids.cs'),(Join-Path $root 'src/Ids/Work.cs'),(Join-Path $root 'src/Annotator/Media.cs'),(Join-Path $root 'src/Annotator/VideoJobs.cs'),(Join-Path $root 'src/Annotator/Workflow.cs'),(Join-Path $root 'src/Annotator/App.cs'))
$sources += (Join-Path $root 'src/Annotator/UiChecks.cs')
$sources += (Join-Path $root 'src/Annotator/Interface.cs'),(Join-Path $root 'src/Annotator/AppDiagnostics.cs'),(Join-Path $root 'src/Annotator/DeploymentChecks.cs')
$staging=Join-Path $root ('build/compile/'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $staging | Out-Null
$stagedExe=Join-Path $staging 'Ivad.Annotator.Dev.exe'
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /utf8output ('/out:'+$stagedExe) ('/resource:'+(Join-Path $root 'src/Annotator/Theme.xaml')+',Ivad.Theme.xaml') @references @sources
if($LASTEXITCODE -ne 0){throw '开发编译失败'}
$targetExe=Join-Path $out 'Ivad.Annotator.Dev.exe'
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
 $testSources=@((Join-Path $root 'src/Ids/Ids.cs'),(Join-Path $root 'src/Ids/Work.cs'),(Join-Path $root 'src/Annotator/Media.cs'),(Join-Path $root 'src/Annotator/VideoJobs.cs'),(Join-Path $root 'src/Full/TrainingAdapter.cs'),(Join-Path $root 'tests/Tests.cs'),(Join-Path $root 'tests/ExtendedTests.cs'),(Join-Path $root 'tests/MediaFixtures.cs'),(Join-Path $root 'tests/FixtureContainers.cs'))
 $testSources += (Join-Path $root 'src/Annotator/Workflow.cs'),(Join-Path $root 'tests/WorkflowTests.cs')
 & $compiler /nologo /target:exe /platform:x64 /optimize+ /utf8output ('/out:'+(Join-Path $out 'Ivad.Tests.exe')) @references @testSources
 if($LASTEXITCODE -ne 0){throw '测试编译失败'}
 & (Join-Path $out 'Ivad.Tests.exe') (Join-Path $root 'build/test-data')
 if($LASTEXITCODE -ne 0){throw '测试失败'}
}
Write-Output '开发构建完成（非安装包，未签名，发行冻结）'

