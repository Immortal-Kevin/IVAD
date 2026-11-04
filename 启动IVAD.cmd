@echo off
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0.venv-media-native-v2\Scripts\python.exe" -m ivad_app %*
