@echo off
REM 小智语音交互服务 - Windows 启动脚本

echo ==========================================
echo 🎤 小智语音交互服务
echo ==========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或未添加到 PATH
    pause
    exit /b 1
)

REM 检查依赖
echo [INFO] 检查依赖...
python -c "import fastapi, uvicorn, httpx, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo [WARN] 缺少依赖，正在安装...
    python -m pip install -r requirements.txt
)

REM 创建必要目录
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist logs mkdir logs
echo [INFO] 目录创建完成

REM 启动服务
echo [INFO] 启动服务...
if "%1"=="ui" (
    echo [INFO] 启动 Gradio UI
    python voice_chat_ui.py
) else if "%1"=="prod" (
    echo [INFO] 生产模式启动
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
) else (
    echo [INFO] 开发模式启动 (自动重载)
    python main.py
)

pause
