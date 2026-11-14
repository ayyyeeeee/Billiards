@echo off
chcp 65001 >nul 2>&1
title Billiard Training - Outlier Detection Tool
cd /d "%~dp0"

REM Check for virtual environment
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment.
    ".venv\Scripts\python.exe" outlier_batch.py %*
    goto :end
)

REM Check if base Python has all dependencies
python -c "import statsmodels, scipy, matplotlib, patsy, pandas, numpy" 2>nul
if %ERRORLEVEL% == 0 (
    echo [INFO] All dependencies available in system Python.
    python outlier_batch.py %*
    goto :end
)

REM Try to create virtual environment and install
echo [INFO] Setting up virtual environment for first run...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    echo         Please ensure Python 3.9+ is installed and on PATH.
    pause
    exit /b 1
)
echo [INFO] Installing dependencies...
".venv\Scripts\pip.exe" install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [INFO] Setup complete. Running tool...
".venv\Scripts\python.exe" outlier_batch.py %*

:end
echo.
pause
