@echo off
setlocal
chcp 65001 >nul
set "IVAD_RESULT=0"
echo IVAD Annotator 只读环境检查 - 不安装或修改系统
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" goto architecture_ok
if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" goto architecture_ok
echo FAIL: 需要 Windows x64。
set "IVAD_RESULT=1"
:architecture_ok
set "IVAD_RELEASE=0"
for /f "tokens=3" %%R in ('reg query "HKLM\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" /v Release /reg:64 2^>nul') do set /a IVAD_RELEASE=%%R
if %IVAD_RELEASE% GEQ 528040 (echo PASS: .NET Framework 4.8 或更高已检测到。) else (
 echo FAIL: 需要 .NET Framework 4.8 或更高。请阅读 RUNTIME_REQUIREMENTS.txt。
 echo https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48
 set "IVAD_RESULT=1"
)
if exist "%SystemRoot%\System32\mfplat.dll" (echo PASS: mfplat.dll 已找到。) else (echo FAIL: 缺少 Media Foundation。& set "IVAD_RESULT=1")
if exist "%SystemRoot%\System32\mfreadwrite.dll" (echo PASS: mfreadwrite.dll 已找到。) else (echo FAIL: 缺少媒体读取组件。& set "IVAD_RESULT=1")
echo 文件存在不代表所有视频格式已通过解码；实际兼容性需复验。
if /i not "%~1"=="--no-pause" pause
exit /b %IVAD_RESULT%
