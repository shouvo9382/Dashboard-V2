@echo off
setlocal
title Bangladesh Sports Ministry - Athlete Dashboard

REM Always run from the folder this script lives in.
cd /d "%~dp0"

echo(
echo  ================================================
echo   National Athlete Performance Dashboard
echo  ================================================
echo(

REM ---- 1. Is Python available? -------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Python is not installed, or not on PATH.
    echo(
    echo      Install Python 3.10 or newer from https://python.org
    echo      IMPORTANT: tick "Add Python to PATH" during setup,
    echo      then close this window and run this file again.
    echo(
    pause
    exit /b 1
)

REM ---- 2. First-time setup (only happens once) ----------------------------
if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] First-time setup: creating environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  [X] Could not create the environment. See the error above.
        pause
        exit /b 1
    )
)

if not exist ".venv\.installed" (
    echo  [2/3] First-time setup: installing packages ^(needs internet, ~2 min^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo(
        echo  [X] Package install failed. Are you connected to the internet?
        pause
        exit /b 1
    )
    echo done > ".venv\.installed"
) else (
    echo  [1-2/3] Setup already done - skipping.
)

REM ---- 3. Launch ----------------------------------------------------------
echo  [3/3] Starting the dashboard...
echo(
echo  Your browser will open automatically (using backup port 8599).
echo(
echo  ------------------------------------------------
echo   KEEP THIS BLACK WINDOW OPEN during the demo.
echo   Closing it shuts the dashboard down.
echo   When finished, just close this window.
echo  ------------------------------------------------
echo(

".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8599

REM If Streamlit exits immediately, the port is probably taken.
echo(
echo  The dashboard stopped.
echo  If it never opened, port 8599 is also in use. Restart the laptop and retry.
echo(
pause
