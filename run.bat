@echo off
chcp 65001 >nul
REM Windows 启动脚本（真正的逻辑在 start.py，三平台共用）
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [x] 没有找到 Python 3.9+
  echo     下载安装： https://www.python.org/downloads/
  echo     安装时记得勾选 "Add python.exe to PATH"
  pause
  exit /b 1
)

%PY% start.py %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
