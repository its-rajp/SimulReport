@echo off
chcp 65001 >nul 2>&1
title AI Report Generator - Windows Setup

echo ======================================
echo   Windows Setup Guide
echo   AI Report Generator
echo ======================================
echo.
echo This script checks your system and tells you what's missing.
echo.

set ISSUES=0

:: ─── Python ───
echo [CHECK] Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     OK: %%v
) else (
    echo     MISSING: Python not found!
    echo     Install from: https://www.python.org/downloads/
    echo     IMPORTANT: Check "Add Python to PATH" during install!
    set /a ISSUES+=1
)
echo.

:: ─── Node.js ───
echo [CHECK] Node.js...
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo     OK: Node %%v
) else (
    echo     MISSING: Node.js not found!
    echo     Install from: https://nodejs.org/ (LTS version)
    set /a ISSUES+=1
)
echo.

:: ─── npm ───
echo [CHECK] npm...
where npm >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo     OK: npm %%v
) else (
    echo     MISSING: npm not found! (comes with Node.js)
    set /a ISSUES+=1
)
echo.

:: ─── Git ───
echo [CHECK] Git...
where git >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('git --version 2^>^&1') do echo     OK: %%v
) else (
    echo     MISSING: Git not found!
    echo     Install from: https://git-scm.com/download/win
    set /a ISSUES+=1
)
echo.

:: ─── MongoDB ───
echo [CHECK] MongoDB...
where mongod >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK: mongod found in PATH
) else (
    netstat -ano | findstr :27017 | findstr LISTENING >nul 2>&1
    if %errorlevel% equ 0 (
        echo     OK: MongoDB is running on port 27017
    ) else (
        echo     MISSING: MongoDB not found!
        echo     Install MongoDB Community Server from:
        echo       https://www.mongodb.com/try/download/community
        echo     Or use Docker: docker compose up mongodb
        set /a ISSUES+=1
    )
)
echo.

:: ─── WSL2 (for Redis) ───
echo [CHECK] WSL2 (for Redis)...
where wsl >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK: WSL2 is installed
    wsl -e bash -c "which redis-server" >nul 2>&1
    if %errorlevel% equ 0 (
        echo     OK: redis-server found inside WSL
    ) else (
        echo     MISSING: Redis not installed inside WSL!
        echo     Run these commands in WSL terminal:
        echo       sudo apt update
        echo       sudo apt install redis-server -y
        set /a ISSUES+=1
    )
) else (
    echo     MISSING: WSL2 not installed!
    echo     Run in PowerShell (Admin): wsl --install
    echo     Then restart PC and run in WSL:
    echo       sudo apt update ^&^& sudo apt install redis-server -y
    set /a ISSUES+=1
)
echo.

:: ─── pip packages ───
echo [CHECK] Python packages...
where pip >nul 2>&1
if %errorlevel% equ 0 (
    echo     To install all backend dependencies, run:
    echo       cd backend
    echo       pip install -r requirements.txt
) else (
    echo     MISSING: pip not found!
    set /a ISSUES+=1
)
echo.

:: ─── npm packages ───
echo [CHECK] Frontend packages...
echo     To install all frontend dependencies, run:
echo       cd frontend
echo       npm install
echo.

:: ─── Summary ───
echo ======================================
if %ISSUES% equ 0 (
    echo   All checks passed! You're ready to go.
    echo   Run start.bat to launch the app.
) else (
    echo   %ISSUES% issue(s) found. Fix them above, then re-run this script.
)
echo ======================================
pause
