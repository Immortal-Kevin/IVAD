param([Parameter(Mandatory=$true)][string]$Token,[Parameter(Mandatory=$true)][string]$Manifest,[Parameter(Mandatory=$true)][string]$Directory,[switch]$ProbeMirror,[switch]$PrepareMirror)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$rawRoot=Join-Path $projectRoot 'reports/raw'
$tsBinary='C:/Program Files/Tailscale/tailscale.exe'
$saved=Get-Content -Raw (Join-Path $rawRoot 'vpn_restore_settings_20261014.json') | ConvertFrom-Json
$current=& $tsBinary debug prefs | ConvertFrom-Json
if ($current.ExitNodeID -ne $saved.ExitNodeID) { throw '当前出口节点与授权测试前不同，停止' }
$python=Join-Path $projectRoot '.venvs/intel_infer/Scripts/python.exe'
$guardPath=Join-Path $PSScriptRoot 'vpn_restore_watchdog.py'
$ready=Join-Path $rawRoot "vpn_watchdog_ready_$Token.json"
$marker=Join-Path $rawRoot "vpn_test_restored_$Token.json"
if (Test-Path $marker) { throw '窗口Token已使用' }
$guard=Start-Process -FilePath $python -ArgumentList @("`"$guardPath`"",'--token',$Token,'--delay','90') -WindowStyle Hidden -PassThru
for ($pollIndex=0;$pollIndex -lt 30 -and -not (Test-Path $ready);$pollIndex++) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path $ready)) { throw '恢复保护未启动' }
try {
    & $tsBinary set --exit-node=
    if ($LASTEXITCODE -ne 0) { throw '停用失败' }
    Start-Sleep -Seconds 1
    $disabled=& $tsBinary debug prefs | ConvertFrom-Json
    if ($disabled.ExitNodeID) { throw '出口节点未实际停用' }
    $actualRoute=Find-NetRoute -RemoteIPAddress 151.101.0.223
    if (($actualRoute | Where-Object { $_.InterfaceAlias -eq 'Tailscale' }).Count) { throw '系统路由尚未切换，停止下载并恢复' }
    $env:IVAD_DIRECT_SOURCE_IP=(Get-NetIPAddress -InterfaceAlias WLAN -AddressFamily IPv4 | Select-Object -First 1).IPAddress
    $env:PYTHONUTF8='1'
    if ($PrepareMirror) {
        & $python (Join-Path $PSScriptRoot 'run_bounded.py') --seconds 45 --log (Join-Path $rawRoot 'tuna_manifest_preparation_20261014.log') $python (Join-Path $PSScriptRoot 'prepare_mirror_manifest.py')
    } elseif ($ProbeMirror) {
        $mklArtifact=Get-Content -Raw $Manifest | ConvertFrom-Json | Where-Object { $_.package -eq 'mkl' }
        $indexPath=Join-Path $rawRoot 'tuna_mkl_index_20261014.html'
        & curl.exe --noproxy '*' --ipv4 --compressed --fail --silent --show-error --connect-timeout 5 --max-time 10 --output $indexPath 'https://pypi.tuna.tsinghua.edu.cn/simple/mkl/'
        if ($LASTEXITCODE -ne 0) { throw '镜像索引不可读取' }
        $indexLine=(Select-String -LiteralPath $indexPath -SimpleMatch $mklArtifact.filename | Select-Object -First 1).Line
        if (-not $indexLine -or -not $indexLine.Contains($mklArtifact.sha256)) { throw '镜像索引文件/hash未匹配官方元数据' }
        $relative=[regex]::Match($indexLine,'href="([^"]+)"').Groups[1].Value
        $mirrorUrl=([uri]::new([uri]'https://pypi.tuna.tsinghua.edu.cn/simple/mkl/',$relative)).AbsoluteUri.Split('#')[0]
        [pscustomobject]@{Url=$mirrorUrl;OfficialSHA256=$mklArtifact.sha256;IndexMatched=$true} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $rawRoot 'tuna_mkl_verified_source_20261014.json')
        & curl.exe --noproxy '*' --ipv4 --fail --silent --show-error --connect-timeout 5 --max-time 15 --range 0-1048575 --output (Join-Path $projectRoot 'artifacts/p0/mkl_tuna_probe.bin') --write-out 'tuna mkl status=%{http_code} bytes=%{size_download} time=%{time_total} local=%{local_ip} tls=%{ssl_verify_result}' $mirrorUrl 2>&1 | Tee-Object -FilePath (Join-Path $rawRoot 'tuna_mkl_direct_probe_20261014.log')
    } else {
    & $python (Join-Path $PSScriptRoot 'ranged_download.py') $Manifest --directory $Directory --workers 16 --direct --window-seconds 35 --range-segments 16 2>&1 | Tee-Object -FilePath (Join-Path $rawRoot "direct_download_$Token.log") | Out-Null
    $windowLog=Get-Content -LiteralPath (Join-Path $rawRoot "direct_download_$Token.log")
    $windowLog | Where-Object { $_ -match 'HASH VERIFIED(?! existing)|WINDOW PAUSED|[0-9]+/[0-9]+ ' } | Select-Object -Last 3 | Write-Output
    }
} finally {
    & $tsBinary set "--exit-node=$($saved.RestoreAddress)"
    $after=& $tsBinary debug prefs | ConvertFrom-Json
    if ($after.ExitNodeID -ne $saved.ExitNodeID -or $after.ExitNodeAllowLANAccess -ne $saved.ExitNodeAllowLANAccess) { throw '恢复核验失败，90秒保护仍生效' }
    [pscustomobject]@{Restored=$true;OriginalNodeMatches=$true;AllowLANMatches=$true;Date=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -Encoding utf8 $marker
    Stop-Process -Id $guard.Id -ErrorAction SilentlyContinue
    Write-Output 'VPN RESTORED AND VERIFIED'
}
