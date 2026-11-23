param(
    [string]$Python = 'python',
    [string]$PreparedRuntime
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$stamp = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -or !$stamp) { throw 'Build from a committed checkout.' }
if (git status --porcelain --untracked-files=all) { throw 'Commit source changes before building.' }

$build = Join-Path $root ('.build\portable-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$stage = Join-Path $build 'IVAD Open Trainer'
New-Item -ItemType Directory -Path $stage | Out-Null
$sourceZip = Join-Path $build 'source.zip'
git archive --format=zip --output=$sourceZip HEAD
if ($LASTEXITCODE) { throw 'Source archive failed.' }
Expand-Archive -LiteralPath $sourceZip -DestinationPath $stage
$runtime = Join-Path $stage 'runtime'

if ($PreparedRuntime) {
    robocopy.exe (Resolve-Path -LiteralPath $PreparedRuntime).Path $runtime /E /MT:12 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) { throw 'Prepared runtime copy failed.' }
} else {
    $embed = Join-Path $build 'python.zip'
    curl.exe --fail --location --retry 2 --silent --show-error https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip --output $embed
    if ($LASTEXITCODE -or (Get-FileHash $embed).Hash -ne '4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3') {
        throw 'CPython archive download or SHA-256 verification failed.'
    }
    Expand-Archive -LiteralPath $embed -DestinationPath $runtime
    @('python312.zip', '.', 'Lib\site-packages', 'import site') |
        Set-Content -Encoding ascii -LiteralPath (Join-Path $runtime 'python312._pth')
    & $Python -m pip --python (Join-Path $runtime 'python.exe') install pip==26.2.1
    if ($LASTEXITCODE) { throw 'pip bootstrap failed.' }
    & (Join-Path $runtime 'python.exe') -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r (Join-Path $stage 'requirements-win-cpu.txt')
    if ($LASTEXITCODE) { throw 'Runtime package installation failed.' }
}
$embedded = Join-Path $runtime 'python.exe'
& $embedded -B -m pip check
if ($LASTEXITCODE) { throw 'Runtime dependency check failed.' }
Get-ChildItem -LiteralPath (Join-Path $runtime 'Lib\site-packages\cv2') -File -Filter 'opencv_videoio_ffmpeg*.dll' |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName }
$optionalMetricWeights = Join-Path $runtime 'Lib\site-packages\torchmetrics\functional\image\dists_models\weights.pt'
if (Test-Path -LiteralPath $optionalMetricWeights) { Remove-Item -LiteralPath $optionalMetricWeights }
$packageFixture = Join-Path $runtime 'Lib\site-packages\pkg_resources\tests\data\my-test-package-zip\my-test-package.zip'
if (Test-Path -LiteralPath $packageFixture) { Remove-Item -LiteralPath $packageFixture }
& $embedded -B (Join-Path $stage 'scripts\inventory.py') $stage
if ($LASTEXITCODE) { throw 'Runtime inventory failed.' }
Get-ChildItem -LiteralPath $runtime -Recurse -File -Filter '*.pyc' |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName }
$entryPoints = Join-Path $runtime 'Scripts'
if (Test-Path -LiteralPath $entryPoints) {
    Get-ChildItem -LiteralPath $entryPoints -File -Filter '*.exe' |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName }
}

$exe = Join-Path $stage 'IVAD Open Trainer.exe'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$launcher = Join-Path $stage 'launcher'
$sources = @(Get-ChildItem -LiteralPath $launcher -File -Filter '*.cs' | ForEach-Object FullName)
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /codepage:65001 "/out:$exe" "/win32manifest:$launcher\app.manifest" /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll $sources
if ($LASTEXITCODE) { throw 'EXE compilation failed.' }
Copy-Item -LiteralPath (Join-Path $launcher 'app.config') -Destination "$exe.config"
Set-Content -LiteralPath (Join-Path $stage 'SOURCE-COMMIT.txt') -Value $stamp -Encoding ascii

$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Path $dist -Force | Out-Null
$name = 'IVAD-Open-Trainer-v0.2.1-win11-x64.zip'
$archive = Join-Path $dist $name
if (Test-Path $archive) { throw "Existing package: $archive" }
tar.exe -a -cf $archive -C $build 'IVAD Open Trainer'
if ($LASTEXITCODE) { throw 'ZIP packaging failed.' }
$digest = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archive.sha256" -Encoding ascii -Value "$digest  $name"
Write-Output $archive
Write-Output $digest
