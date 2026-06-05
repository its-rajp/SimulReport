@echo off
chcp 65001 >nul 2>&1
title AI Report Generator - Launcher

echo ======================================
echo   AI Report Generator - Starting...
echo ======================================
echo.

:: ─────────────────────────────────────────────────────────
:: Step 1: Kill old processes on ports 8000 and 5173
:: (Windows equivalent of: lsof -ti:8000 | xargs kill -9)
:: ─────────────────────────────────────────────────────────
echo [1/6] Cleaning up old processes...

:: Kill anything on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo     Killing PID %%a on port 8000...
    taskkill /PID %%a /F >nul 2>&1
)

:: Kill anything on port 5173
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo     Killing PID %%a on port 5173...
    taskkill /PID %%a /F >nul 2>&1
)

echo     Done.
echo.

:: ─────────────────────────────────────────────────────────
:: Step 2: Start MongoDB
:: Install MongoDB Community Server from:
::   https://www.mongodb.com/try/download/community
:: Make sure mongod.exe is in your PATH or installed as a service.
:: ─────────────────────────────────────────────────────────
echo [2/6] Starting MongoDB...

if not exist "%USERPROFILE%\data\db" mkdir "%USERPROFILE%\data\db"

:: Check if MongoDB is already running
netstat -ano | findstr :27017 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo     MongoDB is already running.
) else (
    where mongod >nul 2>&1
    if %errorlevel% equ 0 (
        start "MongoDB" /min mongod --dbpath "%USERPROFILE%\data\db" --logpath "%USERPROFILE%\data\mongod.log" --quiet
        echo     MongoDB started.
    ) else (
        echo     [WARNING] mongod not found in PATH!
        echo     Install MongoDB Community Server from:
        echo       https://www.mongodb.com/try/download/community
        echo     Or run: docker compose up mongodb
        echo.
    )
)
timeout /t 2 /nobreak >nul
echo.

:: ─────────────────────────────────────────────────────────
:: Step 3: Start Redis via WSL2
:: Most efficient free option for Windows.
:: Requires: WSL2 installed with Ubuntu (wsl --install)
:: Then inside WSL: sudo apt update && sudo apt install redis-server -y
:: ─────────────────────────────────────────────────────────
echo [3/6] Starting Redis (via WSL2)...

:: Check if Redis is already running (port 6379)
netstat -ano | findstr :6379 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo     Redis is already running.
) else (
    where wsl >nul 2>&1
    if %errorlevel% equ 0 (
        wsl -e bash -c "redis-server --daemonize yes --logfile /tmp/redis.log" 2>nul
        if %errorlevel% equ 0 (
            echo     Redis started via WSL2.
        ) else (
            echo     [WARNING] Redis failed to start in WSL.
            echo     Run inside WSL first: sudo apt update ^&^& sudo apt install redis-server -y
            echo     Or use Docker: docker compose up redis
        )
    ) else (
        echo     [WARNING] WSL2 not found!
        echo     Option 1: Install WSL2 - run: wsl --install
        echo     Option 2: Use Docker:    docker compose up redis
        echo     Option 3: Install Memurai from https://www.memurai.com/
    )
)
timeout /t 1 /nobreak >nul
echo.

:: ─────────────────────────────────────────────────────────
:: Step 4: Start Backend (FastAPI on port 8000)
:: Runs in a separate window so you can see logs
:: ─────────────────────────────────────────────────────────
echo [4/6] Starting Backend (FastAPI on port 8000)...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && uvicorn src.api.main:app --reload --port 8000"
echo     Backend starting in new window.
echo.

:: ─────────────────────────────────────────────────────────
:: Step 5: Start Celery Worker
:: ─────────────────────────────────────────────────────────
echo [5/6] Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0backend && celery -A src.core.tasks.celery_app worker --loglevel=info --pool=solo"
echo     Celery worker starting in new window.
echo.

:: ─────────────────────────────────────────────────────────
:: Step 6: Start Frontend (React/Vite on port 5173)
:: ─────────────────────────────────────────────────────────
echo [6/6] Starting Frontend (React on port 5173)...
start "Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"
echo     Frontend starting in new window.

timeout /t 3 /nobreak >nul
echo.
echo ======================================
echo   ALL SYSTEMS ARE LIVE!
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo.
echo   Each service runs in its own window.
echo   Close this window or press any key to exit launcher.
echo ======================================
pause >nul
