param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$artifactList = Get-Content -Raw -LiteralPath $Manifest | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
foreach ($artifact in $artifactList) {
    if ([IO.Path]::GetFileName($artifact.filename) -ne $artifact.filename) { throw '非法文件名' }
    $artifactUri = [Uri]$artifact.url
    if ($artifactUri.Scheme -ne 'https' -or $artifactUri.Host -notin @('files.pythonhosted.org','download.pytorch.org','github.com')) { throw '非清单允许的官方 HTTPS 来源' }
    $targetFile = Join-Path $Destination $artifact.filename
    if (Test-Path -LiteralPath $targetFile) {
        $existingHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetFile).Hash.ToLowerInvariant()
        if ($existingHash -eq $artifact.sha256) { Write-Host "已校验，跳过 $($artifact.filename)"; continue }
        throw "已有文件 hash 不符，保留原文件并停止：$targetFile"
    }
    $partialFile = "$targetFile.partial"
    if (Test-Path -LiteralPath $partialFile) { throw "已有未完成文件，保留并停止：$partialFile" }
    Write-Host "下载 $($artifact.filename)"
    & curl.exe --fail --location --connect-timeout 15 --max-time 600 --retry 0 --output $partialFile $artifact.url
    if ($LASTEXITCODE -ne 0) { throw '下载失败/超时，保留 partial 文件，暂停该文件。' }
    $downloadHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $partialFile).Hash.ToLowerInvariant()
    if ($downloadHash -ne $artifact.sha256) { throw '官方 SHA256 不匹配，禁止使用该文件。' }
    Move-Item -LiteralPath $partialFile -Destination $targetFile
    Write-Host "SHA256 PASS $($artifact.filename)"
}
Write-Host '仅下载与校验完成；没有安装包或修改系统设置。'
