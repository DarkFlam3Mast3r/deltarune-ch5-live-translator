# DELTARUNE CH5 Live Translator - Google Free

这是第五章旁路实时翻译包，默认使用 Google Free 翻译接口，不需要 DeepSeek API Key。

它不会分发游戏文件；安装脚本会在目标电脑上备份并 patch 本机的 `chapter5_windows\data.win`。

## 使用步骤

1. 解压整个文件夹。
2. 运行 `install_ch5_patch.bat`，它会自动查找常见 Steam 安装路径。
3. 运行 `start_translator.bat`。
4. 启动 DELTARUNE 第五章。

建议普通用户下载 Releases 里的 zip 包。源码仓库不包含 UTMT CLI 的 `tools/utmt_cli` 目录；发布包内已附带运行所需工具。

如果自动查找失败，用 PowerShell 手动指定游戏目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_ch5_patch.ps1 -GameDir "D:\SteamLibrary\steamapps\common\DELTARUNE"
```

## 还原

安装时会生成类似这样的备份：

```text
chapter5_windows\data.win.ch5-live-translator-backup-YYYYMMDD-HHMMSS
```

关闭游戏后，把备份文件复制回 `chapter5_windows\data.win` 即可还原。

## 注意

- 需要 Windows 和 Python 3.10+。
- 默认走 Google Free，可能会受网络环境影响。
- 包里没有 DELTARUNE 的 `data.win`，每台电脑会 patch 自己本机的游戏文件。

