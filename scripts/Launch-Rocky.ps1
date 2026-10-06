param([ValidateSet('menu','setup','shortcut','tests')][string]$Action = 'menu')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
$SettingsDir = Join-Path $env:USERPROFILE '.rpa1\settings'
$OutputDir = Join-Path $env:USERPROFILE '.rpa1\conversation-v1'
$Config = Join-Path $SettingsDir 'rocky.json'
$Assets = Join-Path $SettingsDir 'assets.json'
$Pointer = Join-Path $Root '.rocky-python-path.txt'

function Repair-Message {
    Write-Host 'No valid project environment was found. Exact repair command in PowerShell:'
    $quoted = (Join-Path $Root 'Rocky.bat').Replace("'", "''")
    Write-Host "& '$quoted' -Action setup"
    Write-Host 'Setup creates a new environment if necessary; it does not delete the old one.'
}
function Find-Python {
    $candidates = @()
    if ($env:ROCKY_PYTHON) { $candidates = @($env:ROCKY_PYTHON) }
    else {
        if (Test-Path -LiteralPath $Pointer) { $candidates += (Get-Content -LiteralPath $Pointer -Raw).Trim() }
        $candidates += (Join-Path $Root '.venv-rocky\Scripts\python.exe')
        $candidates += (Join-Path $Root '.venv\Scripts\python.exe')
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            try {
                & $candidate (Join-Path $PSScriptRoot 'check_environment.py') 2>&1 | Out-Host
                if ($LASTEXITCODE -eq 0) { return $candidate }
            } catch { Write-Host "Broken environment at ${candidate}: $_" }
        }
    }
    Repair-Message
    return $null
}
function Setup-Rocky {
    Write-Host 'Explicit setup: installs this checkout and its pinned Python dependencies. Internet may be needed for Python packages.'
    Write-Host 'It will not download a model, update Git, or replace your configuration files.'
    $python = Find-Python
    if (-not $python) {
        $version = $null
        foreach ($v in @('-3.13', '-3.12')) {
            if (Get-Command py.exe -ErrorAction SilentlyContinue) {
                try {
                    & py.exe $v -c 'import sys; print(sys.version)' 2>$null | Out-Host
                    if ($LASTEXITCODE -eq 0) { $version = $v; break }
                } catch { continue }
            }
        }
        if (-not $version) { throw 'Install Python 3.13 or 3.12 with the Python launcher from https://www.python.org/downloads/windows/; then run this setup again.' }
        $target = Join-Path $Root '.venv-rocky'
        $index = 1
        while (Test-Path -LiteralPath $target) { $target = Join-Path $Root ".venv-rocky-repair-$index"; $index++ }
        & py.exe $version -m venv $target
        if ($LASTEXITCODE -ne 0) { throw "Environment creation failed at $target. Existing folders were preserved." }
        $python = Join-Path $target 'Scripts\python.exe'
    }
    & $python -m pip install -e $Root
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Read the error above, then retry Setup.' }
    & $python (Join-Path $PSScriptRoot 'check_environment.py')
    if ($LASTEXITCODE -ne 0) { throw 'Environment verification failed.' }
    Set-Content -LiteralPath $Pointer -Value $python -Encoding UTF8
    New-Item -ItemType Directory -Force -Path $SettingsDir | Out-Null
    foreach ($name in @('rocky.json', 'personality.json')) {
        $destination = Join-Path $SettingsDir $name
        if (-not (Test-Path -LiteralPath $destination)) {
            Copy-Item -LiteralPath (Join-Path $Root "software\rocky\config\$name") -Destination $destination
        }
    }
    if (-not (Test-Path -LiteralPath $Assets)) {
        Copy-Item -LiteralPath (Join-Path $Root 'software\rocky\config\assets.example.json') -Destination $Assets
    }
    Write-Host "Ready. Settings: $SettingsDir"
}
function Create-Shortcut {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $destination = Join-Path $desktop 'Rocky.lnk'
    if (Test-Path -LiteralPath $destination) { throw "Shortcut already exists: $destination. Rename it if you want another; it has not been changed." }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($destination)
    $shortcut.TargetPath = Join-Path $Root 'Rocky.bat'
    $shortcut.WorkingDirectory = $Root
    $shortcut.Description = 'Rocky desktop menu'
    $shortcut.Save()
    Write-Host "Created $destination"
}
function Run-Tests($python) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $log = Join-Path $OutputDir 'tests-latest.txt'
    & $python (Join-Path $PSScriptRoot 'run_tests.py') 2>&1 | Tee-Object -FilePath $log | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Tests failed. Output: $log" }
    Write-Host "Output: $log"
}
function Run-Rocky($choice) {
    $python = Find-Python
    if (-not $python) { throw 'Run option 7 to repair the environment.' }
    if ($choice -eq '4') { Run-Tests $python; return }
    $arguments = @()
    if (Test-Path -LiteralPath $Config) { $arguments += @('--config', $Config) }
    if (Test-Path -LiteralPath $Assets) { $arguments += @('--asset-manifest', $Assets) }
    if ($choice -eq '10') { & $python -m rocky benchmark @arguments --provider local; return }
    if ($choice -eq '11') {
        $backupDir = Join-Path $env:USERPROFILE '.rpa1\backups'
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $target = Join-Path $backupDir "rocky-user-backup-$stamp.zip"
        & $python -m rocky backup @arguments --backup-output $target
        return
    }
    if ($choice -eq '12') {
        if (-not (Test-Path -LiteralPath $Assets)) { throw 'Run setup/repair first to create the editable asset manifest.' }
        & $python -m rocky verify-assets --asset-manifest $Assets
        return
    }
    if ($choice -eq '13') {
        $session = Read-Host 'Lecture session ID (example lecture-20261005T120000Z-ab12cd34)'
        if ([string]::IsNullOrWhiteSpace($session)) { throw 'Lecture session ID is required.' }
        & $python -m rocky lecture-transcribe @arguments --lecture-session $session
        return
    }
    if ($choice -eq '14') {
        $session = Read-Host 'Transcribed lecture session ID (example lecture-20261005T120000Z-ab12cd34)'
        if ([string]::IsNullOrWhiteSpace($session)) { throw 'Lecture session ID is required.' }
        & $python -m rocky lecture-notes @arguments --lecture-session $session --provider local
        return
    }
    if ($choice -eq '15') {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts\Setup-Piper.ps1')
        if ($LASTEXITCODE -ne 0) { throw 'Optional Piper sidecar setup failed.' }
        return
    }
    if ($choice -eq '16') {
        if (-not (Test-Path -LiteralPath $Config) -or -not (Test-Path -LiteralPath $Assets)) {
            throw 'Run setup/repair first to create editable Rocky settings and asset manifest.'
        }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts\Setup-WhisperCpp.ps1') -ConfigPath $Config -AssetsPath $Assets
        if ($LASTEXITCODE -ne 0) { throw 'Local whisper.cpp provisioning failed.' }
        return
    }
    if ($choice -eq '1' -or $choice -eq '9') {
        Write-Host 'Local model availability check only; this does not establish GPU stability.'
        & $python -m rocky check @arguments --provider local
        if ($LASTEXITCODE -ne 0) { throw 'Start Ollama. Run ollama list. Set model in your rocky.json to an already downloaded local model, then try again. No download was attempted.' }
        if ($choice -eq '9') { & $python -m rocky web @arguments --provider local }
        else { & $python -m rocky chat @arguments --provider local }
    } elseif ($choice -eq '2') {
        & $python -m rocky chat @arguments --provider dummy
    } elseif ($choice -eq '3') {
        & $python -m rocky audio-test @arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "Rocky exited with code $LASTEXITCODE. The error is shown above." }
}
# Dot-sourcing exposes functions for the Windows integration tests only.
if ($MyInvocation.InvocationName -eq '.') { return }
try {
    if ($Action -eq 'setup') { Setup-Rocky; Read-Host 'Press Enter to close'; exit 0 }
    if ($Action -eq 'shortcut') { Create-Shortcut; Read-Host 'Press Enter to close'; exit 0 }
    if ($Action -eq 'tests') { Run-Rocky '4'; Read-Host 'Press Enter to close'; exit 0 }
    while ($true) {
        Write-Host "`nRocky desktop menu`n1 Talk with real local model (terminal)`n2 DummyAI diagnostics`n3 Audio test`n4 Automated tests`n5 Settings/personality instructions`n6 Latest test output`n7 Setup/repair (explicit package installation)`n8 Create desktop shortcut`n9 Open local Rocky web UI`n10 Run real Assistant benchmark`n11 Export portable user backup`n12 Verify external asset manifest`n13 Transcribe recorded lecture session`n14 Generate study notes from lecture`n15 Setup optional Piper neural voice sidecar`n16 Configure local whisper.cpp voice input`n0 Exit"
        $choice = Read-Host 'Choose'
        try {
            switch ($choice) {
                '0' { exit 0 }
                '5' {
                    Start-Process notepad.exe -ArgumentList ('"' + (Join-Path $Root 'docs\build-guides\rocky-desktop-v1-1.md') + '"')
                    if (Test-Path -LiteralPath $SettingsDir) { Start-Process explorer.exe -ArgumentList ('"' + $SettingsDir + '"') }
                    else { Write-Host 'Choose 7 to create editable settings without replacing existing files.' }
                }
                '6' {
                    $log = Join-Path $OutputDir 'tests-latest.txt'
                    if (Test-Path -LiteralPath $log) { Start-Process notepad.exe -ArgumentList ('"' + $log + '"') }
                    else { Write-Host 'No automated test output yet. Choose 4.' }
                }
                '7' { Setup-Rocky }
                '8' { Create-Shortcut }
                { $_ -in '1','2','3','4','9','10','11','12','13','14','15','16' } { Run-Rocky $choice }
                default { Write-Host 'Choose 0 through 16.' }
            }
        } catch { Write-Host "ERROR: $_" -ForegroundColor Red }
    }
} catch { Write-Host "ERROR: $_" -ForegroundColor Red; exit 1 }
