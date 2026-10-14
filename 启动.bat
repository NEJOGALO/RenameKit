@echo off
chcp 65001 >nul 2>nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo    RenameKit 源码运行版启动器
echo ============================================
echo.

rem ---- 1. 查找 Python（py 启动器优先）----
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [错误] 未检测到 Python。
    echo 请先安装 Python 3.10 或更高版本：
    echo     https://www.python.org/downloads/
    echo 安装时请勾选 "Add python.exe to PATH"。
    pause
    exit /b 1
)

rem ---- 2. 首次运行创建虚拟环境 ----
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 首次运行，正在创建虚拟环境，请稍候...
    %PY% -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [错误] 虚拟环境创建失败。
        pause
        exit /b 1
    )
)

rem ---- 3. 安装依赖（首次需要联网）----
echo [2/3] 检查依赖...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

rem ---- 4. 启动 ----
echo [3/3] 正在启动 RenameKit...
echo.
".venv\Scripts\python.exe" src\main.py
pause
