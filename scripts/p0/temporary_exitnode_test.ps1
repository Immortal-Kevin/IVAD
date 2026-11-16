$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$rawRoot = Join-Path $projectRoot 'reports/raw'
$tsBinary = 'C:/Program Files/Tailscale/tailscale.exe'
$savedSettings = Get-Content -Raw -LiteralPath (Join-Path $rawRoot 'vpn_restore_settings_20261014.json') | ConvertFrom-Json
if (-not $savedSettings.RestoreAddress) { throw '缺少恢复地址，禁止变更' }
$restoreMarker = Join-Path $rawRoot 'vpn_test_restored_20261014.json'
if (Test-Path -LiteralPath $restoreMarker) { throw '本测试已执行，禁止盲目重复变更' }
$guardScript = Join-Path $PSScriptRoot 'vpn_restore_watchdog.py'
$projectPython = Join-Path $projectRoot '.venvs/intel_infer/Scripts/python.exe'
$guard = Start-Process -FilePath $projectPython -ArgumentList @("`"$guardScript`"") -WindowStyle Hidden -PassThru
$readyPath = Join-Path $rawRoot 'vpn_watchdog_ready_20261014.json'
for ($pollIndex=0; $pollIndex -lt 30 -and -not (Test-Path -LiteralPath $readyPath); $pollIndex++) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path -LiteralPath $readyPath)) { throw '恢复保护未启动，禁止变更' }
try {
    & $tsBinary set --exit-node=
    if ($LASTEXITCODE -ne 0) { throw '临时停用出口节点失败' }
    Start-Sleep -Seconds 2
    Get-NetRoute -AddressFamily IPv4 | Where-Object { $_.DestinationPrefix -eq '0.0.0.0/0' } | Select-Object InterfaceAlias,NextHop,RouteMetric | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $rawRoot 'direct_route_disabled_20261014.json')
    $missingArtifacts = Get-Content -Raw -LiteralPath (Join-Path $rawRoot 'offline_missing_manifest.json') | ConvertFrom-Json
    $h11Artifact = $missingArtifacts | Where-Object { $_.package -eq 'h11' }
    $h11Target = Join-Path $projectRoot ('artifacts/p0/wheels/' + $h11Artifact.filename)
    $h11Temp = "$h11Target.direct_test"
    & curl.exe --noproxy '*' --ipv4 --fail --silent --show-error --connect-timeout 5 --max-time 20 --output $h11Temp --write-out 'h11 status=%{http_code} bytes=%{size_download} time=%{time_total} local=%{local_ip} tls=%{ssl_verify_result}' $h11Artifact.url 2>&1 | Tee-Object -FilePath (Join-Path $rawRoot 'direct_h11_disabled_20261014.log')
    if ($LASTEXITCODE -eq 0) {
        $h11Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $h11Temp).Hash.ToLowerInvariant()
        if ($h11Hash -ne $h11Artifact.sha256) { throw 'h11官方SHA256不符，停止' }
        if (-not (Test-Path -LiteralPath $h11Target)) { Move-Item -LiteralPath $h11Temp -Destination $h11Target }
        Write-Output 'h11 full file SHA256 PASS'
    }
    $torchArtifact = $missingArtifacts | Where-Object { $_.package -eq 'torch' }
    & curl.exe --noproxy '*' --ipv4 --silent --show-error --connect-timeout 5 --max-time 20 --range 0-1048575 --output (Join-Path $projectRoot 'artifacts/p0/torch_direct_disabled_probe.bin') --write-out 'torch status=%{http_code} bytes=%{size_download} time=%{time_total} local=%{local_ip} tls=%{ssl_verify_result}' $torchArtifact.url 2>&1 | Tee-Object -FilePath (Join-Path $rawRoot 'direct_torch_disabled_20261014.log')
} finally {
    & $tsBinary set "--exit-node=$($savedSettings.RestoreAddress)"
    if ($LASTEXITCODE -ne 0) { throw '出口节点恢复命令失败，独立保护仍会恢复' }
    $afterPrefs = & $tsBinary debug prefs | ConvertFrom-Json
    if ($afterPrefs.ExitNodeID -ne $savedSettings.ExitNodeID -or $afterPrefs.ExitNodeAllowLANAccess -ne $savedSettings.ExitNodeAllowLANAccess) { throw '恢复设置校验不符，保留独立恢复保护' }
    [pscustomobject]@{Restored=$true;OriginalNodeMatches=$true;AllowLANMatches=$true;Date=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -Encoding utf8 $restoreMarker
    Write-Output 'Original exit node and LAN preference restored and verified'
    Stop-Process -Id $guard.Id -ErrorAction SilentlyContinue
}
