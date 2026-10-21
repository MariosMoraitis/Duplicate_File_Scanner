@echo off
REM ==========================================================================
REM  Duplicate File Scanner - Windows installer
REM
REM  What it does:
REM    1. Finds Python 3.10 or newer, and installs Python 3.12 if it is missing
REM    2. Creates a virtual environment in .venv
REM    3. Installs the dependencies from requirements.txt
REM
REM  Usage:
REM    install.bat          install what is needed to RUN the app
REM    install.bat --dev    also install the test tools (pytest)
REM
REM  You can simply double-click this file.
REM ==========================================================================

setlocal
cd /d "%~dp0"

set "PY_VERSION=3.12.10"
set "WINGET_ID=Python.Python.3.12"
set "INSTALL_DEV=0"
if /i "%~1"=="--dev" set "INSTALL_DEV=1"

echo.
echo === Duplicate File Scanner - installer ===
echo.

if not exist requirements.txt (
    echo ERROR: requirements.txt not found. Run this script from the project folder.
    goto :fail
)

REM --------------------------------------------------------------------------
echo [1/4] Looking for Python 3.10 or newer...
call :find_python
if defined PY goto :python_ready

echo       Python 3.10 or newer was not found on this computer.

REM Try winget first (built into Windows 10 and 11).
where winget >nul 2>&1
if errorlevel 1 goto :download_python

echo       Installing Python %PY_VERSION% with winget. This can take a minute...
winget install -e --id %WINGET_ID% --source winget --silent --accept-package-agreements --accept-source-agreements
call :find_python
if defined PY goto :python_ready
echo       winget did not finish the install. Trying a direct download instead...

:download_python
set "ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
set "INSTALLER=%TEMP%\python-%PY_VERSION%-%ARCH%.exe"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-%ARCH%.exe"

echo       Downloading %PY_URL%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%INSTALLER%'"
if not exist "%INSTALLER%" (
    echo ERROR: the download failed. Please install Python 3.10 or newer manually from
    echo        https://www.python.org/downloads/  and tick "Add python.exe to PATH",
    echo        then run this script again.
    goto :fail
)

echo       Running the Python installer. This can take a minute...
start "" /wait "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1 Include_pip=1 Include_test=0
del "%INSTALLER%" >nul 2>&1

call :find_python
if defined PY goto :python_ready
echo ERROR: Python was installed but could not be located yet.
echo        Close this window, open a new one and run install.bat again.
goto :fail

REM --------------------------------------------------------------------------
:python_ready
echo       Found:
"%PY%" %PYARGS% --version

echo.
echo [2/4] Checking tkinter, which the GUI needs...
"%PY%" %PYARGS% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo ERROR: this Python has no tkinter. Re-run the Python installer, choose Modify,
    echo        and make sure "tcl/tk and IDLE" is ticked.
    goto :fail
)
echo       OK

echo.
echo [3/4] Creating virtual environment in .venv ...
if exist ".venv\Scripts\python.exe" (
    echo       Already exists, reusing it.
) else (
    "%PY%" %PYARGS% -m venv .venv
    if errorlevel 1 goto :fail
    echo       Created.
)

echo.
echo [4/4] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if "%INSTALL_DEV%"=="1" (
    if not exist requirements-dev.txt (
        echo ERROR: requirements-dev.txt not found.
        goto :fail
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
    if errorlevel 1 goto :fail
)

".venv\Scripts\python.exe" -c "import tkinter, customtkinter, send2trash" >nul 2>&1
if errorlevel 1 (
    echo ERROR: something did not install correctly. Scroll up for the error.
    goto :fail
)

echo.
echo ==========================================================================
echo  All done. Start the app by double-clicking run.bat
echo ==========================================================================
echo.
pause
exit /b 0

:fail
echo.
echo Installation did not complete. Please read the messages above.
echo.
pause
exit /b 1


REM ==========================================================================
REM  :find_python  - looks for Python 3.10+ and sets two variables:
REM      PY      the program to run (py, python, or a full path to python.exe)
REM      PYARGS  extra arguments for it (-3 when using the "py" launcher)
REM  Leaves PY empty when nothing suitable is found.
REM ==========================================================================
:find_python
set "PY="
set "PYARGS="
set "CHECK=import sys; sys.exit(0 if (sys.version_info.major == 3 and sys.version_info.minor >= 10) else 1)"

REM 1) The "py" launcher that python.org installers add.
py -3 -c "%CHECK%" >nul 2>&1
if not errorlevel 1 (
    set "PY=py"
    set "PYARGS=-3"
    exit /b 0
)

REM 2) python / python3 on PATH. The Microsoft Store placeholder fails this
REM    check, which is exactly what we want.
for %%P in (python python3) do (
    if not defined PY (
        %%P -c "%CHECK%" >nul 2>&1
        if not errorlevel 1 set "PY=%%P"
    )
)
if defined PY exit /b 0

REM 3) Standard install folders. A Python that was JUST installed is not on
REM    PATH in this window yet, so look for it directly.
for %%V in (314 313 312 311 310) do (
    if not defined PY (
        if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
            "%LocalAppData%\Programs\Python\Python%%V\python.exe" -c "%CHECK%" >nul 2>&1
            if not errorlevel 1 set "PY=%LocalAppData%\Programs\Python\Python%%V\python.exe"
        )
    )
)
if defined PY exit /b 0

for %%V in (314 313 312 311 310) do (
    if not defined PY (
        if exist "%ProgramFiles%\Python%%V\python.exe" (
            "%ProgramFiles%\Python%%V\python.exe" -c "%CHECK%" >nul 2>&1
            if not errorlevel 1 set "PY=%ProgramFiles%\Python%%V\python.exe"
        )
    )
)
exit /b 0