@echo off
chcp 65001 >nul 2>&1
title AI Report Generator - Install All Dependencies

echo =====================================================
echo   AI Report Generator - Dependency Installer
echo   This will install ALL backend + frontend packages
echo =====================================================
echo.

:: ─────────────────────────────────────────────────────────
:: Pre-flight checks
:: ─────────────────────────────────────────────────────────

echo [PRE-CHECK] Verifying required tools...
echo.

set ABORT=0

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] Python NOT found in PATH!
    echo       Download from: https://www.python.org/downloads/
    echo       IMPORTANT: Check "Add Python to PATH" during install!
    set ABORT=1
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   [OK] %%v
)

:: Check pip
where pip >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] pip NOT found!
    echo       Run: python -m ensurepip --upgrade
    set ABORT=1
) else (
    for /f "tokens=*" %%v in ('pip --version 2^>^&1') do echo   [OK] pip found
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] Node.js NOT found in PATH!
    echo       Download from: https://nodejs.org/ (LTS version)
    set ABORT=1
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo   [OK] Node.js %%v
)

:: Check npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] npm NOT found!
    echo       npm comes bundled with Node.js
    set ABORT=1
) else (
    for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo   [OK] npm %%v
)

echo.

if %ABORT% equ 1 (
    echo =====================================================
    echo   [ABORTED] Fix the missing tools above, then re-run.
    echo =====================================================
    pause
    exit /b 1
)

echo   All tools found. Proceeding with installation...
echo.

:: ─────────────────────────────────────────────────────────
:: SECTION 1: Backend Python Packages
:: ─────────────────────────────────────────────────────────
echo =====================================================
echo   [BACKEND] Installing Python Packages via pip
echo =====================================================
echo.
echo   Packages to install:
echo     - fastapi         (Web API framework)
echo     - uvicorn         (ASGI server)
echo     - celery          (Async task queue / worker)
echo     - redis           (Redis Python client)
echo     - pymongo         (MongoDB driver)
echo     - dnspython       (DNS for MongoDB Atlas URIs)
echo     - pandas          (Data processing)
echo     - openpyxl        (Excel file reading)
echo     - plotly          (Chart generation)
echo     - kaleido         (Plotly image export)
echo     - reportlab       (PDF generation)
echo     - PyPDF2          (PDF reading)
echo     - langchain-google-genai  (Google Gemini AI)
echo     - SQLAlchemy      (ORM)
echo     - pydantic        (Data validation)
echo     - loguru          (Logging)
echo     - python-multipart (File upload handling)
echo     - python-dotenv   (.env file loading)
echo.

:: Check if requirements.txt exists
if exist "%~dp0backend\requirements.txt" (
    echo   Installing from backend\requirements.txt ...
    echo.
    pip install -r "%~dp0backend\requirements.txt"
) else (
    echo   [WARNING] backend\requirements.txt not found!
    echo   Installing packages individually...
    echo.
    pip install fastapi==0.136.1
    pip install uvicorn==0.47.0
    pip install SQLAlchemy==2.0.49
    pip install pandas==2.3.3
    pip install plotly==6.7.0
    pip install loguru==0.7.3
    pip install python-multipart==0.0.28
    pip install celery==5.6.3
    pip install redis==7.4.0
    pip install pydantic==2.13.4
    pip install langchain-google-genai==4.2.2
    pip install reportlab==4.5.1
    pip install openpyxl==3.1.5
    pip install kaleido==1.3.0
    pip install PyPDF2==3.0.1
    pip install python-dotenv==1.0.1
    pip install pymongo==4.17.0
    pip install dnspython==2.8.0
)

if %errorlevel% neq 0 (
    echo.
    echo   [WARNING] Some Python packages may have failed to install.
    echo   Check the output above for errors.
) else (
    echo.
    echo   [OK] All Python packages installed successfully!
)

echo.

:: ─────────────────────────────────────────────────────────
:: SECTION 2: Kaleido Chrome dependency
:: Kaleido 1.x needs Chrome/Chromium for image export
:: ─────────────────────────────────────────────────────────
echo =====================================================
echo   [KALEIDO] Setting up Chrome for Plotly image export
echo =====================================================
echo.
echo   Kaleido 1.x requires Chrome/Chromium for chart export.
echo   Attempting to download a compatible Chrome binary...
echo.

python -c "import kaleido; kaleido.get_chrome_sync()" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Chrome binary ready for Kaleido.
) else (
    echo   [INFO] Could not auto-download Chrome for Kaleido.
    echo   If you already have Chrome/Chromium installed, you're fine.
    echo   Otherwise run:  kaleido_get_chrome
)
echo.

:: ─────────────────────────────────────────────────────────
:: SECTION 3: Frontend Node.js Packages
:: ─────────────────────────────────────────────────────────
echo =====================================================
echo   [FRONTEND] Installing Node.js Packages via npm
echo =====================================================
echo.
echo   Packages to install:
echo     - react           (UI library)
echo     - react-dom       (React DOM renderer)
echo     - react-router-dom (Client-side routing)
echo     - plotly.js       (Interactive charts)
echo     - react-plotly.js (React wrapper for Plotly)
echo     - lucide-react    (Icon library)
echo     - vite            (Build tool / dev server)
echo     - @vitejs/plugin-react (Vite React plugin)
echo.

if exist "%~dp0frontend\package.json" (
    echo   Installing from frontend\package.json ...
    echo.
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
) else (
    echo   [WARNING] frontend\package.json not found!
    echo   Creating frontend and installing packages individually...
    echo.
    if not exist "%~dp0frontend" mkdir "%~dp0frontend"
    cd /d "%~dp0frontend"
    call npm init -y
    call npm install react@^18.2.0 react-dom@^18.2.0 react-router-dom@^6.22.3 plotly.js@^3.5.1 react-plotly.js@^2.6.0 lucide-react@^0.364.0
    call npm install --save-dev vite@^5.2.0 @vitejs/plugin-react@^4.2.1
    cd /d "%~dp0"
)

if %errorlevel% neq 0 (
    echo.
    echo   [WARNING] Some npm packages may have failed to install.
    echo   Check the output above for errors.
) else (
    echo.
    echo   [OK] All frontend packages installed successfully!
)

echo.

:: ─────────────────────────────────────────────────────────
:: SECTION 4: Environment file setup
:: ─────────────────────────────────────────────────────────
echo =====================================================
echo   [CONFIG] Setting up environment file
echo =====================================================
echo.

if not exist "%~dp0backend\.env" (
    if exist "%~dp0backend\.env.example" (
        copy "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
        echo   [OK] Created backend\.env from .env.example
        echo   [ACTION REQUIRED] Edit backend\.env and add your API keys:
        echo     - GOOGLE_API_KEY=your_google_gemini_api_key
        echo     - OPENAI_API_KEY=your_openai_api_key (if used)
    ) else (
        echo   [WARNING] No .env.example found to copy from.
        echo   Create backend\.env manually with your API keys.
    )
) else (
    echo   [OK] backend\.env already exists.
)

echo.

:: ─────────────────────────────────────────────────────────
:: Final Summary
:: ─────────────────────────────────────────────────────────
echo =====================================================
echo.
echo   INSTALLATION COMPLETE!
echo.
echo   What was installed:
echo     [Backend]  18 Python packages via pip
echo     [Kaleido]  Chrome binary for chart export
echo     [Frontend] 8 Node.js packages via npm
echo     [Config]   .env file created (if missing)
echo.
echo   Next steps:
echo     1. Edit backend\.env with your API keys
echo     2. Make sure MongoDB + Redis are running
echo        (see setup_check_windows.bat)
echo     3. Run start.bat to launch the app!
echo.
echo =====================================================
pause
