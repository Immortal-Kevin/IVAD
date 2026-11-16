# SPDX-License-Identifier: Apache-2.0
# One explicit authorization, one final delivery. No implicit future packaging.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
 $auth=Get-Content governance/portable-authorization-20261026.json -Raw | ConvertFrom-Json
 if($auth.status -ne 'ACTIVE_SINGLE_DELIVERY' -or $auth.authorization_id -ne 'IVAD-ANNOTATOR-PORTABLE-20261026-ONCE'){throw '本次打包授权已消耗或无效；后续版本需要新的用户明确授权。'}
 $gate=Get-Content governance/evidence/release_gate.json -Raw | ConvertFrom-Json
 if($gate.engineering_status -ne 'PASS'){throw '工程Gate必须先通过'}
 $id=[Guid]::NewGuid().ToString('N')
 $stage=Join-Path $root ('build/portable/'+$id)
 New-Item -ItemType Directory -Path $stage | Out-Null
 $fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
 $compiler=Join-Path $fx 'csc.exe'
 $info=Join-Path $stage 'AssemblyInfo.cs'
 @'
// SPDX-License-Identifier: Apache-2.0
using System.Reflection;
using System.Runtime.Versioning;
[assembly: AssemblyTitle("IVAD Annotator")]
[assembly: AssemblyProduct("IVAD Annotator")]
[assembly: AssemblyDescription("Windows x64 portable test build")]
[assembly: AssemblyCopyright("Copyright 2026 IVAD contributors")]
[assembly: AssemblyVersion("1.1.2026.1026")]
[assembly: AssemblyFileVersion("1.1.2026.1026")]
[assembly: AssemblyInformationalVersion("1.1-test.20261026.01")]
[assembly: TargetFramework(".NETFramework,Version=v4.8", FrameworkDisplayName=".NET Framework 4.8")]
'@ | Set-Content -LiteralPath $info -Encoding utf8
 $refs=@('System.dll','System.Core.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Xaml.dll','System.Windows.Forms.dll','System.Drawing.dll','WPF/WindowsBase.dll','WPF/PresentationCore.dll','WPF/PresentationFramework.dll') | ForEach-Object {'/reference:'+(Join-Path $fx $_)}
 $sourceNames=@('src/Ids/Ids.cs','src/Ids/Work.cs','src/Annotator/Media.cs','src/Annotator/VideoJobs.cs','src/Annotator/Workflow.cs','src/Annotator/App.cs','src/Annotator/Interface.cs','src/Annotator/UiChecks.cs','src/Annotator/AppDiagnostics.cs','src/Annotator/DeploymentChecks.cs')
 $sources=$sourceNames | ForEach-Object {Join-Path $root $_}
 $payload=Join-Path $stage 'IVAD-Annotator'
 New-Item -ItemType Directory -Path $payload | Out-Null
 $exe=Join-Path $payload 'IVAD.Annotator.exe'
 & $compiler /nologo /target:winexe /platform:x64 /langversion:5 /optimize+ /debug- /utf8output ('/out:'+$exe) ('/win32manifest:'+(Join-Path $root 'src/Annotator/Portable.manifest')) ('/resource:'+(Join-Path $root 'src/Annotator/Theme.xaml')+',Ivad.Theme.xaml') @refs @sources $info *> (Join-Path $stage 'compile.log')
 if($LASTEXITCODE -ne 0){throw ('便携编译失败：'+(Join-Path $stage 'compile.log'))}
 $assembly=[Reflection.Assembly]::LoadFile($exe)
 $pinvokes=@($assembly.GetTypes() | ForEach-Object {$_.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,DeclaredOnly')} | ForEach-Object {$_.GetCustomAttributes([Runtime.InteropServices.DllImportAttribute],$false)} | ForEach-Object {$_.Value} | Sort-Object -Unique)
 $inspection=@{assembly_name=$assembly.FullName;assembly_references=@($assembly.GetReferencedAssemblies() | ForEach-Object {$_.FullName});pinvoke=$pinvokes;resources=@($assembly.GetManifestResourceNames());types=@($assembly.GetTypes() | ForEach-Object {$_.FullName});compiler_file_version=(Get-Item $compiler).VersionInfo.FileVersion;target_framework=($assembly.GetCustomAttributes([Runtime.Versioning.TargetFrameworkAttribute],$false)[0].FrameworkName)}
 $inspection | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'binary-inspection.json') -Encoding utf8
 & .venvs/intel_infer/Scripts/python.exe -X utf8 scripts/governance/portable_package.py build $stage
 if($LASTEXITCODE -ne 0){throw '候选内容审计/打包失败'}
} finally {Pop-Location}
