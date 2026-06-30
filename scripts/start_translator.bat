@echo off
setlocal
cd /d "%~dp0translator"
if errorlevel 1 goto cd_failed
where python >nul 2>nul
if errorlevel 1 goto no_python
python run_ch5_deepseek_debug.py
echo.
echo Translator exited. Press any key to close.
pause >nul
exit /b
:no_python
echo Python not found. Please install Python 3.10+ from https://www.python.org/downloads/windows/
pause
exit /b 1
:cd_failed
echo Failed to enter translator directory.
pause
exit /b 1
