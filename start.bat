@echo off
chcp 65001 >nul
echo 🚀 Edict 一键启动器
echo ====================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

:: 检查 node_modules
if not exist "dashboard-ui\node_modules" (
    echo 📦 首次运行，正在安装前端依赖...
    cd dashboard-ui
    call npm install
    if errorlevel 1 (
        echo ❌ 安装失败
        pause
        exit /b 1
    )
    cd ..
)

:: 启动服务
echo.
python start.py %*
