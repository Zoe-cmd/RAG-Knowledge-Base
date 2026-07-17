@echo off
REM ============================================================
REM AI 文档知识库（MVP）一键启动脚本（Windows）
REM ============================================================
REM 在 Windows 上启动前后端服务
REM ============================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend
set BACKEND_LOG_DIR=%BACKEND_DIR%\data\logs
set FRONTEND_LOG_DIR=%FRONTEND_DIR%\data\logs
set BACKEND_LOG_FILE=%BACKEND_LOG_DIR%\backend.out.log
set FRONTEND_LOG_FILE=%FRONTEND_LOG_DIR%\frontend.out.log

echo.
echo [STEP] 1/6 环境检查...

REM Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 python，请先安装 Python 3.11+
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PY_VERSION=%%i
echo [INFO] Python: %PY_VERSION%

REM Node
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 node，请先安装 Node.js 18+
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [INFO] Node.js: %NODE_VERSION%

REM npm
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 npm
    exit /b 1
)

REM ===== 2. .env 检查 =====
echo.
echo [STEP] 2/6 检查 .env ...
if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
        echo [WARN] 已从 .env.example 复制创建 backend/.env
        echo [ERROR] 请编辑 backend\.env 填写 DATABASE_URL 与 OPENAI_API_KEY 后重新执行本脚本
        notepad "%BACKEND_DIR%\.env"
        exit /b 1
    ) else (
        echo [ERROR] 未找到 backend\.env 与 backend\.env.example
        exit /b 1
    )
) else (
    echo [INFO] backend\.env 已配置
)

REM ===== 3. 数据目录 =====
echo.
echo [STEP] 3/6 创建数据目录...
if not exist "%BACKEND_DIR%\data\uploads" mkdir "%BACKEND_DIR%\data\uploads"
if not exist "%BACKEND_DIR%\data\chroma" mkdir "%BACKEND_DIR%\data\chroma"
if not exist "%BACKEND_DIR%\data\models" mkdir "%BACKEND_DIR%\data\models"
if not exist "%BACKEND_LOG_DIR%" mkdir "%BACKEND_LOG_DIR%"
if not exist "%FRONTEND_LOG_DIR%" mkdir "%FRONTEND_LOG_DIR%"
echo [INFO] 数据目录就绪

REM ===== 4. 后端虚拟环境 =====
echo.
echo [STEP] 4/6 后端虚拟环境...
if not exist "%BACKEND_DIR%\.venv" (
    echo [INFO] 创建虚拟环境 .venv ...
    python -m venv "%BACKEND_DIR%\.venv"
)
call "%BACKEND_DIR%\.venv\Scripts\activate.bat"

REM 安装依赖（首次）
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装后端依赖（首次较慢）...
    python -m pip install --upgrade pip --quiet
    python -m pip install -r "%BACKEND_DIR%\requirements.txt" --quiet
    echo [INFO] 后端依赖安装完成
) else (
    echo [INFO] 后端依赖已安装
)

REM ===== 5. 启动后端 =====
echo.
echo [STEP] 5/6 启动后端 (uvicorn)...
cd /d "%BACKEND_DIR%"
start "AI-KB-Backend" /MIN cmd /c "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "%BACKEND_LOG_FILE%" 2>&1"
echo [INFO] 后端已后台启动，日志: %BACKEND_LOG_FILE%

REM 等待后端就绪
echo [INFO] 等待后端就绪（最多 30 秒）...
set /a COUNT=0
:WAIT_BACKEND
set /a COUNT+=1
timeout /t 1 /nobreak >nul
powershell -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { 0 }" >nul 2>&1 | findstr "200" >nul
if errorlevel 1 (
    if !COUNT! lss 30 (
        goto WAIT_BACKEND
    ) else (
        echo [WARN] 后端 30s 内未响应，请查看日志: %BACKEND_LOG_FILE%
    )
) else (
    echo [INFO] 后端就绪（耗时 !COUNT!s）
)

REM ===== 6. 启动前端 =====
echo.
echo [STEP] 6/6 启动前端 (Vite)...
cd /d "%FRONTEND_DIR%"
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [INFO] 安装前端依赖（首次较慢）...
    call npm install --silent
    echo [INFO] 前端依赖安装完成
)
start "AI-KB-Frontend" /MIN cmd /c "npm run dev -- --host 127.0.0.1 --port 5173 > "%FRONTEND_LOG_FILE%" 2>&1"
echo [INFO] 前端已后台启动，日志: %FRONTEND_LOG_FILE%

REM 等待前端就绪
echo [INFO] 等待前端就绪（最多 20 秒）...
set /a COUNT=0
:WAIT_FRONTEND
set /a COUNT+=1
timeout /t 1 /nobreak >nul
powershell -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { 0 }" >nul 2>&1 | findstr "200" >nul
if errorlevel 1 (
    if !COUNT! lss 20 (
        goto WAIT_FRONTEND
    ) else (
        echo [WARN] 前端 20s 内未响应，请查看日志: %FRONTEND_LOG_FILE%
    )
) else (
    echo [INFO] 前端就绪（耗时 !COUNT!s）
)

cd /d "%SCRIPT_DIR%"

REM ===== 启动完成 =====
echo.
echo ========================================
echo   AI 文档知识库已启动
echo ========================================
echo.
echo   前端:    http://127.0.0.1:5173
echo   后端:    http://127.0.0.1:8000
echo   健康检查: http://127.0.0.1:8000/health
echo   API 文档: http://127.0.0.1:8000/docs (仅 DEBUG=true)
echo.
echo   日志:
echo     后端: %BACKEND_LOG_FILE%
echo     前端: %FRONTEND_LOG_FILE%
echo.
echo   停止服务: 关闭名为 AI-KB-Backend 和 AI-KB-Frontend 的窗口
echo             或执行 taskkill /FI "WINDOWTITLE eq AI-KB-*" /F
echo.
pause
