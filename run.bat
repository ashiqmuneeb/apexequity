@echo off
title ApexEquity - Full Stack Launcher
color 0A
echo ======================================================================
echo              ApexEquity: Institutional Financial AI Platform
echo        FastAPI Backend (LlamaIndex) + React 19 Frontend
echo ======================================================================
echo.

set "ROOT_DIR=%~dp0"

:: 1. Backend environment check
echo [1/3] Preparing Backend environment...
cd /d "%ROOT_DIR%backend"
if not exist "venv\Scripts\activate.bat" (
    echo [*] Virtual environment missing. Creating backend\venv...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [*] Installing backend dependencies...
    pip install -r requirements.txt
)

if not exist "storage" (
    echo [*] Generating vector store index from articles...
    call venv\Scripts\activate.bat
    python index_data.py
)
echo [OK] Backend ready.

:: 2. Frontend environment check
echo.
echo [2/3] Preparing Frontend environment...
cd /d "%ROOT_DIR%frontend"
if not exist "node_modules" (
    echo [*] node_modules missing. Running npm install...
    call npm install
)
echo [OK] Frontend ready.

:: 3. Concurrently launch both services in labeled windows
echo.
echo [3/3] Launching Backend & Frontend services...
echo.

start "ApexEquity [Backend API - 127.0.0.1:8000]" cmd /k "cd /d "%ROOT_DIR%backend" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

start "ApexEquity [Frontend UI - localhost:5173]" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

echo ======================================================================
echo Both services are running:
echo   - Backend API:    http://127.0.0.1:8000  (Docs: http://127.0.0.1:8000/docs)
echo   - React Frontend: http://localhost:5173
echo.
echo Opening browser in 3 seconds...
echo ======================================================================
timeout /t 3 /nobreak >nul
start http://localhost:5173
