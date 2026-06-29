@echo off
REM UE Asset Path Finder - 启动脚本
REM 这个脚本用于方便用户启动应用

setlocal enabledelayedexpansion

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"

REM 检查 EXE 文件是否存在
if not exist "%SCRIPT_DIR%dist\UEAssetPathFinder.exe" (
    echo.
    echo ==========================================
    echo 错误: 未找到应用程序文件
    echo ==========================================
    echo.
    echo 预期路径: %SCRIPT_DIR%dist\UEAssetPathFinder.exe
    echo.
    echo 请确保:
    echo 1. 应用已编译到 dist 文件夹
    echo 2. 文件名为 UEAssetPathFinder.exe
    echo.
    pause
    exit /b 1
)

REM 启动应用
start "" "%SCRIPT_DIR%dist\UEAssetPathFinder.exe"

exit /b 0
