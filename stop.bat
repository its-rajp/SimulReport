@echo off
chcp 65001 >nul 2>&1
title AI Report Generator - Shutdown

echo ======================================
echo   Shutting down all services...
echo ======================================
echo.

:: Kill Backend (port 8000)
echo [1/4] Stopping Backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo     Killed PID %%a
)
echo     Done.

:: Kill Frontend (port 5173)
echo [2/4] Stopping Frontend (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo     Killed PID %%a
)
echo     Done.

:: Kill Celery workers
echo [3/4] Stopping Celery workers...
taskkill /IM celery.exe /F >nul 2>&1
echo     Done.

:: Stop Redis in WSL
echo [4/4] Stopping Redis (WSL2)...
where wsl >nul 2>&1
if %errorlevel% equ 0 (
    wsl -e bash -c "redis-cli shutdown" 2>nul
    echo     Redis stopped.
) else (
    echo     WSL not found, skipping Redis shutdown.
)

echo.
echo ======================================
echo   All services stopped.
echo ======================================
pause
