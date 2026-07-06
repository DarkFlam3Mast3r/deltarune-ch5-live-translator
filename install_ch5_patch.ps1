param(
    [string]$GameDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataRel = "chapter5_windows\data.win"

function Find-DeltaruneDir {
    $candidates = @()

    if ($GameDir) {
        $candidates += $GameDir
    }

    $candidates += @(
        "C:\Program Files (x86)\Steam\steamapps\common\DELTARUNE",
        "C:\Program Files\Steam\steamapps\common\DELTARUNE",
        "C:\Software\Steam\steamapps\common\DELTARUNE"
    )

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $dataPath = Join-Path $candidate $dataRel
        if (Test-Path -LiteralPath $dataPath) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not find DELTARUNE. Run: powershell -ExecutionPolicy Bypass -File .\install_ch5_patch.ps1 -GameDir 'D:\SteamLibrary\steamapps\common\DELTARUNE'"
}

$gameRoot = Find-DeltaruneDir
$dataWin = Join-Path $gameRoot $dataRel
$tool = Join-Path $root "tools\utmt_cli\UndertaleModCli.exe"
$script = Join-Path $root "patch\patch_ch5_msgset_choice_bridge_v7.csx"
$out = Join-Path $env:TEMP ("deltarune_ch5_translator_patched_" + [Guid]::NewGuid().ToString("N") + ".win")
$backup = $dataWin + ".ch5-live-translator-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")

if (-not (Test-Path -LiteralPath $tool)) {
    throw "Missing UTMT CLI: $tool"
}
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing patch script: $script"
}

Write-Host "DELTARUNE: $gameRoot"
Write-Host "Backing up data.win to: $backup"
Copy-Item -LiteralPath $dataWin -Destination $backup -Force

Write-Host "Generating patched data.win..."
& $tool load $dataWin -s $script -o $out
if ($LASTEXITCODE -ne 0) {
    throw "UTMT CLI patch failed. Original file and backup were kept."
}

Write-Host "Installing patched data.win..."
Copy-Item -LiteralPath $out -Destination $dataWin -Force
Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Install complete. Fully close and restart DELTARUNE Chapter 5."
Write-Host "To restore, copy this backup back to data.win:"
Write-Host $backup