@echo off
setlocal
title WaterMeterVision Launcher

REM Run this file from the project root (the folder containing backend and frontend).
cd /d "%~dp0"

echo.
echo ============================================
echo       WaterMeterVision - System Launcher
echo ============================================
echo.

if not exist "backend\api.py" (
    echo [ERROR] backend\api.py was not found.
    echo Put this BAT file in the Meters_CV project root.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json was not found.
    echo Put this BAT file in the Meters_CV project root.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment .venv was not found.
    echo Create it and install requirements-pc.txt first.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found. Install Node.js LTS and reopen the terminal.
    pause
    exit /b 1
)

echo [1/3] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo [INFO] node_modules not found. Running npm install...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    popd
)

echo [2/3] Starting FastAPI backend...
start "WaterMeterVision Backend" cmd /k "cd /d ""%~dp0"" && call "".venv\Scripts\activate.bat"" && python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000"

echo [3/3] Starting React dashboard...
start "WaterMeterVision Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1"

echo.
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo Backend:   http://127.0.0.1:8000
echo Dashboard: http://127.0.0.1:5173
echo.
echo Keep both terminal windows open while using the system.
echo Close those windows (or press Ctrl+C in each) to stop services.
echo ============================================
echo.

start "" "http://127.0.0.1:5173"
endlocal
