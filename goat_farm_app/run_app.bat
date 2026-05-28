@echo off
title Ranga Farms Web Service Starter
echo ===================================================
echo   Starting Ranga Farms Web Service...
echo ===================================================
cd /d "%~dp0"

echo 1. Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please download and install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

echo 2. Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] There was an issue installing some dependencies. Trying anyway...
)

echo 3. Launching Flask Application...
echo The app will run on http://127.0.0.1:5001
echo Keep this window open while using the application.
echo ===================================================
python Project_goatfarm.py
if %errorlevel% neq 0 (
    echo [ERROR] The application crashed or failed to start.
    pause
)
