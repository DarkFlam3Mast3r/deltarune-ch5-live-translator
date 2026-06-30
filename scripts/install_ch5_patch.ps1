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

    throw "找不到 DELTARUNE 目录。请用参数指定，例如：.\install_ch5_patch.ps1 -GameDir 'D:\SteamLibrary\steamapps\common\DELTARUNE'"
}

$gameRoot = Find-DeltaruneDir
$dataWin = Join-Path $gameRoot $dataRel
$tool = Join-Path $root "tools\utmt_cli\UndertaleModCli.exe"
$script = Join-Path $root "patch\patch_ch5_msgset_choice_bridge_v7.csx"
$out = Join-Path $env:TEMP ("deltarune_ch5_translator_patched_" + [Guid]::NewGuid().ToString("N") + ".win")
$backup = $dataWin + ".ch5-live-translator-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")

if (-not (Test-Path -LiteralPath $tool)) {
    throw "缺少 UTMT CLI：$tool"
}
if (-not (Test-Path -LiteralPath $script)) {
    throw "缺少补丁脚本：$script"
}

Write-Host "DELTARUNE: $gameRoot"
Write-Host "备份 data.win 到：$backup"
Copy-Item -LiteralPath $dataWin -Destination $backup -Force

Write-Host "正在生成已 patch 的 data.win..."
& $tool load $dataWin -s $script -o $out
if ($LASTEXITCODE -ne 0) {
    throw "UTMT CLI patch 失败，已保留原文件和备份。"
}

Write-Host "正在安装补丁..."
Copy-Item -LiteralPath $out -Destination $dataWin -Force
Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "安装完成。请完全关闭并重新启动 DELTARUNE 第五章。"
Write-Host "如需还原，把备份文件复制回 data.win 即可："
Write-Host $backup
