param(
    [ValidateSet('-3.13','-3.12')][string]$PythonVersion = '-3.13'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
$Pointer = Join-Path $Root '.rocky-piper-python-path.txt'
$TokenDir = Join-Path $env:USERPROFILE '.rpa1\piper'
$TokenPath = Join-Path $TokenDir 'sidecar.token'
$RequiredVersion = '1.8.0'

function Test-PiperEnvironment($python) {
    if (-not (Test-Path -LiteralPath $python)) { return $false }
    try {
        $version = & $python -c "import importlib.metadata; print(importlib.metadata.version('piper-tts'))" 2>$null
        return ($LASTEXITCODE -eq 0 -and $version.Trim() -eq $RequiredVersion)
    } catch {
        return $false
    }
}

Write-Host "Explicit optional setup: Piper neural TTS sidecar $RequiredVersion"
Write-Host 'This installs GPL-3.0-or-later piper-tts in a separate environment.'
Write-Host 'It does NOT download a voice, change Rocky settings, start a server, or modify the core Rocky environment.'

$python = $null
if (Test-Path -LiteralPath $Pointer) {
    $candidate = (Get-Content -LiteralPath $Pointer -Raw).Trim()
    if (Test-PiperEnvironment $candidate) { $python = $candidate }
}
$default = Join-Path $Root '.venv-rocky-piper\Scripts\python.exe'
if (-not $python -and (Test-PiperEnvironment $default)) { $python = $default }

if (-not $python) {
    if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
        throw 'Python launcher py.exe is required. Install Python 3.12 or 3.13 first.'
    }
    & py.exe $PythonVersion -c 'import sys; print(sys.version)'
    if ($LASTEXITCODE -ne 0) {
        throw "Python $PythonVersion is unavailable."
    }
    $target = Join-Path $Root '.venv-rocky-piper'
    if (Test-Path -LiteralPath $target) {
        $index = 1
        do {
            $target = Join-Path $Root ".venv-rocky-piper-repair-$index"
            $index++
        } while (Test-Path -LiteralPath $target)
    }
    & py.exe $PythonVersion -m venv $target
    if ($LASTEXITCODE -ne 0) { throw "Could not create Piper environment at $target" }
    $python = Join-Path $target 'Scripts\python.exe'
    & $python -m pip install "piper-tts==$RequiredVersion"
    if ($LASTEXITCODE -ne 0) {
        throw 'Piper installation failed. The separate environment was preserved for inspection.'
    }
    if (-not (Test-PiperEnvironment $python)) {
        throw 'Piper environment verification failed.'
    }
    Set-Content -LiteralPath $Pointer -Value $python -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $TokenDir | Out-Null
if (-not (Test-Path -LiteralPath $TokenPath)) {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
    [IO.File]::WriteAllText($TokenPath, $token, [Text.Encoding]::ASCII)
}

Write-Host ''
Write-Host "Piper sidecar environment ready: $python"
Write-Host "Sidecar token: $TokenPath"
Write-Host 'No voice model was downloaded.'
Write-Host ''
Write-Host 'Next, explicitly choose/provision a Piper voice and review its model license.'
Write-Host 'The Piper voice downloader can be listed with:'
Write-Host "& '$python' -m piper.download_voices"
Write-Host ''
Write-Host 'After you have an ONNX voice file, checksum it in ~/.rpa1/settings/assets.json.'
Write-Host 'Start the sidecar with:'
$sidecar = Join-Path $Root 'scripts\rocky_piper_sidecar.py'
Write-Host "& '$python' '$sidecar' --model 'C:\path\to\voice.onnx' --token-file '$TokenPath' --port 5055"
Write-Host ''
Write-Host 'Then set rocky.json translation_voice_backend to piper-sidecar and piper_sidecar_token_path to the token path.'
