param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('xpu', 'cuda')]
    [string]$Backend
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root 'runtime'
$target = Join-Path $root "runtime-$Backend"
$staging = "$target-$([guid]::NewGuid().ToString('N'))"
if (!(Test-Path (Join-Path $runtime 'python.exe'))) { throw 'Extract the full CPU ZIP first.' }
if (Test-Path $target) { throw "The runtime already exists at $target" }
Copy-Item -LiteralPath $runtime -Destination $staging -Recurse

$profile = if ($Backend -eq 'cuda') { 'cu130' } else { 'xpu' }
$python = Join-Path $staging 'python.exe'
$index = "https://download.pytorch.org/whl/$profile"
& $python -m pip --disable-pip-version-check install --index-url $index "torch==2.12.1+$profile" "torchvision==0.27.1+$profile"
if ($LASTEXITCODE) { throw "GPU runtime installation failed in $staging" }
& $python -m pip check
if ($LASTEXITCODE) { throw "GPU dependencies did not validate in $staging" }
Move-Item -LiteralPath $staging -Destination $target
Write-Host "Installed $Backend runtime at $target"
