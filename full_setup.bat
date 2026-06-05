@echo off
chcp 65001 >nul 2>&1
title SimulReport - Full Windows Setup

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           SimulReport - Full Windows Auto Setup             ║
echo ║   This will install ALL system tools + project dependencies ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo  [!] Run this script as ADMINISTRATOR for best results.
echo  [!] Internet connection required.
echo.
pause

:: ─────────────────────────────────────────────────────────────────
:: STEP 0: Check winget availability
:: winget is built into Windows 10 (1709+) and Windows 11
:: ─────────────────────────────────────────────────────────────────
echo.
echo ══════════════════════════════════════════════════════════════
echo  [0/7] Checking winget (Windows Package Manager)...
echo ══════════════════════════════════════════════════════════════
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] winget is NOT available on this machine!
    echo.
    echo  To install winget:
    echo    1. Open Microsoft Store
    echo    2. Search for "App Installer" and update it
    echo    3. Or visit: https://aka.ms/getwinget
    echo.
    echo  After installing winget, re-run this script.
    pause
    exit /b 1
)
echo  [OK] winget found!
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 1: Install Python 3.11
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [1/7] Installing Python 3.11...
echo ══════════════════════════════════════════════════════════════
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [SKIP] %%v already installed.
) else (
    echo  Installing Python 3.11 via winget...
    winget install --id Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo  [WARNING] winget install failed. Trying alternative ID...
        winget install --id Python.Python.3 -e --silent --accept-package-agreements --accept-source-agreements
    )
    echo  [OK] Python installed.
    echo  [!] Please ensure Python is in your PATH.
    echo      If not, re-run installer and check "Add Python to PATH".
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 2: Install Node.js LTS
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [2/7] Installing Node.js LTS...
echo ══════════════════════════════════════════════════════════════
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo  [SKIP] Node.js %%v already installed.
) else (
    echo  Installing Node.js LTS via winget...
    winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
    echo  [OK] Node.js installed.
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 3: Install Git
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [3/7] Installing Git...
echo ══════════════════════════════════════════════════════════════
where git >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('git --version 2^>^&1') do echo  [SKIP] %%v already installed.
) else (
    echo  Installing Git via winget...
    winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
    echo  [OK] Git installed.
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 4: Install MongoDB Community Server
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [4/7] Installing MongoDB Community Server...
echo ══════════════════════════════════════════════════════════════
where mongod >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SKIP] MongoDB (mongod) already in PATH.
) else (
    netstat -ano | findstr :27017 | findstr LISTENING >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [SKIP] MongoDB already running on port 27017.
    ) else (
        echo  Installing MongoDB 7 via winget...
        winget install --id MongoDB.Server -e --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo  [INFO] winget install may have partially succeeded.
            echo  [INFO] Verify by opening: https://www.mongodb.com/try/download/community
        ) else (
            echo  [OK] MongoDB installed.
            echo  Starting MongoDB service...
            net start MongoDB >nul 2>&1
            if %errorlevel% equ 0 (
                echo  [OK] MongoDB service started.
            ) else (
                echo  [INFO] Could not auto-start MongoDB service.
                echo  [INFO] Run manually: net start MongoDB
            )
        )
    )
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 5: Install Redis via WSL2
:: Redis has no native Windows binary — WSL2 is the recommended way
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [5/7] Installing Redis (via WSL2)...
echo ══════════════════════════════════════════════════════════════
where wsl >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] WSL2 is already installed.
    wsl -e bash -c "which redis-server" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [SKIP] Redis already installed inside WSL.
    ) else (
        echo  Installing Redis inside WSL (Ubuntu)...
        wsl -e bash -c "sudo apt-get update -y && sudo apt-get install -y redis-server"
        if %errorlevel% equ 0 (
            echo  [OK] Redis installed inside WSL.
        ) else (
            echo  [WARNING] Could not install Redis inside WSL automatically.
            echo  [ACTION]  Open WSL terminal and run:
            echo              sudo apt update
            echo              sudo apt install redis-server -y
        )
    )
) else (
    echo  [INFO] WSL2 is NOT installed. Installing now...
    echo  [!] This may require a RESTART after completion.
    echo.
    wsl --install -d Ubuntu
    if %errorlevel% equ 0 (
        echo  [OK] WSL2 + Ubuntu install initiated.
        echo  [!]  RESTART your PC, then re-run this script to install Redis inside WSL.
    ) else (
        echo  [WARNING] WSL2 install failed or requires manual steps.
        echo  [ACTION]  Run in PowerShell (Admin): wsl --install
        echo  [ALT]     Use Docker Desktop instead: docker compose up
    )
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 6: Refresh PATH so newly installed tools are available
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [6/7] Refreshing environment PATH...
echo ══════════════════════════════════════════════════════════════
:: Reload PATH from registry
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%B"
set "PATH=%SYS_PATH%;%USER_PATH%"
echo  [OK] PATH refreshed for this session.
echo.

:: ─────────────────────────────────────────────────────────────────
:: STEP 7: Install all project dependencies
:: ─────────────────────────────────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo  [7/7] Installing Project Dependencies...
echo ══════════════════════════════════════════════════════════════
echo.

:: ── 7a: Python backend packages ──────────────────────────────────
echo  [7a] Installing Python (backend) packages...
where pip >nul 2>&1
if %errorlevel% equ 0 (
    if exist "%~dp0backend\requirements.txt" (
        pip install -r "%~dp0backend\requirements.txt"
        if %errorlevel% equ 0 (
            echo  [OK] Python packages installed from requirements.txt
        ) else (
            echo  [WARNING] Some Python packages may have failed. Check output above.
        )
    ) else (
        echo  [WARNING] backend\requirements.txt not found! Skipping...
    )
) else (
    echo  [WARNING] pip not found. Python may not be in PATH yet.
    echo  [ACTION]  Close this window, open a NEW Command Prompt, and re-run this script.
)
echo.

:: ── 7b: Kaleido Chrome binary for chart export ───────────────────
echo  [7b] Setting up Kaleido Chrome binary for chart/image export...
python -c "import kaleido; kaleido.get_chrome_sync()" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Kaleido Chrome binary ready.
) else (
    echo  [INFO] Kaleido Chrome auto-download skipped (or Chrome already installed).
)
echo.

:: ── 7c: Node.js frontend packages ────────────────────────────────
echo  [7c] Installing Node.js (frontend) packages...
where npm >nul 2>&1
if %errorlevel% equ 0 (
    if exist "%~dp0frontend\package.json" (
        cd /d "%~dp0frontend"
        call npm install
        if %errorlevel% equ 0 (
            echo  [OK] Frontend npm packages installed.
        ) else (
            echo  [WARNING] Some npm packages may have failed. Check output above.
        )
        cd /d "%~dp0"
    ) else (
        echo  [WARNING] frontend\package.json not found! Skipping...
    )
) else (
    echo  [WARNING] npm not found. Node.js may not be in PATH yet.
    echo  [ACTION]  Close this window, open a NEW Command Prompt, and re-run this script.
)
echo.

:: ── 7d: Create .env if missing ───────────────────────────────────
echo  [7d] Setting up environment config file...
if not exist "%~dp0backend\.env" (
    if exist "%~dp0backend\.env.example" (
        copy "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
        echo  [OK] Created backend\.env from .env.example
        echo  [!!] ACTION REQUIRED: Edit backend\.env and fill in your API keys:
        echo        - GOOGLE_API_KEY=your_google_gemini_api_key
        echo        - MONGO_URI=mongodb://localhost:27017/report_generator
        echo        - REDIS_URL=redis://localhost:6379/0
    ) else (
        echo  [WARNING] No .env.example found. Create backend\.env manually.
    )
) else (
    echo  [SKIP] backend\.env already exists.
)
echo.

:: ─────────────────────────────────────────────────────────────────
:: FINAL SUMMARY
:: ─────────────────────────────────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                   SETUP COMPLETE!                           ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║                                                              ║
echo ║  What was installed:                                         ║
echo ║    [1] Python 3.11           (via winget)                    ║
echo ║    [2] Node.js LTS           (via winget)                    ║
echo ║    [3] Git                   (via winget)                    ║
echo ║    [4] MongoDB Community     (via winget)                    ║
echo ║    [5] Redis                 (via WSL2)                      ║
echo ║    [6] Python pip packages   (from requirements.txt)         ║
echo ║    [7] Node npm packages     (from package.json)             ║
echo ║    [8] backend\.env          (from .env.example)             ║
echo ║                                                              ║
echo ║  Next Steps:                                                 ║
echo ║    1. Edit backend\.env  →  add your GOOGLE_API_KEY          ║
echo ║    2. Run:  start.bat   →  to launch the full app            ║
echo ║                                                              ║
echo ║  App URLs after starting:                                    ║
echo ║    Frontend:  http://localhost:5173                          ║
echo ║    Backend:   http://localhost:8000                          ║
echo ║    API Docs:  http://localhost:8000/docs                     ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
pause
