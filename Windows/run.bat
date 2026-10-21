@echo off
REM Start Duplicate File Scanner (run install.bat once first).
REM   run.bat             start the app without a console window
REM   run.bat --console   start it WITH a console, so error messages are visible
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

if /i "%~1"=="--console" (
    ".venv\Scripts\python.exe" "src\app.py"
    pause
    exit /b %errorlevel%
)

start "" ".venv\Scripts\pythonw.exe" "src\app.py"