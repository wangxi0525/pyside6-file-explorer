@echo off
setlocal
cd /d "%~dp0"

REM ================= locate a Python interpreter =================
set "PY="

if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

if not defined PY if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

REM "current" under versions is a symlink, so dir /b /s aborts the whole
REM scan. Walk the version folders with for /d instead.
if not defined PY for /d %%D in ("%USERPROFILE%\.workbuddy\binaries\python\versions\*") do (
  if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
)

if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

REM py.exe launcher: resolve it to a real interpreter path so %PY% always
REM holds a single executable, never a multi-word command.
if not defined PY (
  for %%P in (py.exe) do (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
      if not defined PY set "PY=%%I"
    )
  )
)

if not defined PY for %%P in (python.exe python3.exe) do if not defined PY (
  for /f "delims=" %%I in ('where %%P 2^>nul') do if not defined PY set "PY=%%I"
)

if not defined PY (
  echo [ERROR] No Python interpreter found.
  echo.
  echo   Install Python 3.10 or newer from https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" during setup, then run this again.
  echo.
  pause
  exit /b 1
)

REM ================= make sure PySide6 is installed =================
"%PY%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installing PySide6, please wait...
  "%PY%" -m pip install --upgrade pip
  "%PY%" -m pip install -i https://pypi.org/simple PySide6
  if errorlevel 1 (
    echo.
    echo [ERROR] PySide6 installation failed. Check your network connection.
    echo.
    pause
    exit /b 1
  )
)

REM ================= launch =================
if /i "%~1"=="--check" (
  echo Interpreter: %PY%
  "%PY%" --version
  "%PY%" -c "import PySide6; print('PySide6', PySide6.__version__)"
  "%PY%" -c "import core, main_window; print('Project modules import OK')"
  echo [OK] Everything is ready.
  exit /b 0
)

REM --run is passed by the VBS launcher: no console output, and the
REM command window closes on its own once the GUI comes up.
if /i "%~1"=="--run" goto :launch_silent

echo [RUN] Starting Qt File Explorer...
echo.
"%PY%" run.py %*
if errorlevel 1 (
  echo.
  echo [ERROR] The program exited with an error.
  echo.
  pause
  exit /b 1
)
exit /b 0

:launch_silent
shift
REM Prefer pythonw.exe: it has no console attached at all, so nothing
REM is left on screen. Fall back to python.exe if pythonw is missing.
set "PYW="
for %%I in ("%PY%") do set "PYDIR=%%~dpI"
if exist "%PYDIR%pythonw.exe" set "PYW=%PYDIR%pythonw.exe"

if defined PYW (
  start "" "%PYW%" run.py %*
) else (
  start "" "%PY%" run.py %*
)
exit /b 0

endlocal