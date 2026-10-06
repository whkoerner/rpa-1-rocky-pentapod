param(
    [string]$WhisperCliPath = "",
    [string]$WhisperModelPath = "",
    [string]$ConfigPath = (Join-Path $env:USERPROFILE '.rpa1\settings\rocky.json'),
    [string]$AssetsPath = (Join-Path $env:USERPROFILE '.rpa1\settings\assets.json')
)
$ErrorActionPreference = 'Stop'

function Get-SafeFile([string]$PathValue, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        throw "$Label path is required."
    }
    $item = Get-Item -LiteralPath $PathValue -Force -ErrorAction Stop
    if ($item.PSIsContainer) { throw "$Label must be a file." }
    if ($item.LinkType) { throw "$Label must not be a symbolic link or reparse link." }
    return $item
}

function Write-JsonAtomic([string]$PathValue, $Payload) {
    $parent = Split-Path -Parent $PathValue
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $temp = "$PathValue.tmp"
    $json = ($Payload | ConvertTo-Json -Depth 20) + [Environment]::NewLine
    [IO.File]::WriteAllText($temp, $json, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $PathValue -Force
}

Write-Host 'Configure explicitly provisioned local whisper.cpp voice input.'
Write-Host 'This does NOT download whisper.cpp, a model, or any other asset.'
Write-Host 'Choose files you obtained and reviewed separately.'

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Rocky settings file not found: $ConfigPath. Run Rocky setup/repair first."
}
if (-not (Test-Path -LiteralPath $AssetsPath)) {
    throw "Rocky asset manifest not found: $AssetsPath. Run Rocky setup/repair first."
}
if ([string]::IsNullOrWhiteSpace($WhisperCliPath)) {
    $WhisperCliPath = Read-Host 'Path to reviewed whisper-cli executable'
}
if ([string]::IsNullOrWhiteSpace($WhisperModelPath)) {
    $WhisperModelPath = Read-Host 'Path to reviewed local Whisper GGML model'
}

$cli = Get-SafeFile $WhisperCliPath 'whisper-cli'
$model = Get-SafeFile $WhisperModelPath 'Whisper model'
$cliHash = (Get-FileHash -LiteralPath $cli.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$modelHash = (Get-FileHash -LiteralPath $model.FullName -Algorithm SHA256).Hash.ToLowerInvariant()

$assets = Get-Content -LiteralPath $AssetsPath -Raw | ConvertFrom-Json
if ($assets.schema_version -ne 1 -or $assets.manifest_id -ne 'rocky-assets-v1' -or -not $assets.assets) {
    throw 'Rocky asset manifest has an unexpected shape.'
}
$cliRows = @($assets.assets | Where-Object { $_.id -eq 'whisper_cli' -and $_.kind -eq 'file' })
$modelRows = @($assets.assets | Where-Object { $_.id -eq 'whisper_model' -and $_.kind -eq 'file' })
if ($cliRows.Count -ne 1 -or $modelRows.Count -ne 1) {
    throw 'Rocky asset manifest must contain exactly one whisper_cli and one whisper_model file entry.'
}
$cliRows[0].path = $cli.FullName
$cliRows[0].sha256 = $cliHash
$modelRows[0].path = $model.FullName
$modelRows[0].sha256 = $modelHash

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
if ($null -eq $config.stt_backend -or $null -eq $config.whisper_cli_path -or $null -eq $config.whisper_model_path) {
    throw 'Rocky settings file is too old for STT provisioning. Run setup/repair with the current checkout first.'
}

# Write the manifest first. If the later config write fails, STT stays disabled rather
# than pointing at an unpinned runtime asset.
Write-JsonAtomic $AssetsPath $assets
$config.stt_backend = 'whisper-cpp'
$config.whisper_cli_path = $cli.FullName
$config.whisper_model_path = $model.FullName
Write-JsonAtomic $ConfigPath $config

Write-Host ''
Write-Host 'Local whisper.cpp assets configured and checksum-pinned.'
Write-Host "whisper-cli: $($cli.FullName)"
Write-Host "  sha256: $cliHash"
Write-Host "Whisper model: $($model.FullName)"
Write-Host "  sha256: $modelHash"
Write-Host 'No microphone test or recognition-quality claim has been made.'
Write-Host 'Use Rocky web UI push-to-talk for manual acceptance after configuration.'
