@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv-p1\Scripts\pythonw.exe" (
  echo 缺少独立P1环境。请查看 docs\P1_USER_GUIDE.md，请勿使用全局Python替代。
  pause
  exit /b 1
)
start "" "%~dp0.venv-p1\Scripts\pythonw.exe" -m ivad_app %*
