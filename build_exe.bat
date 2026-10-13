@echo off
setlocal
cd /d "%~dp0"

REM =============================================================
REM  Build a standalone Windows application with PyInstaller.
REM
REM  --windowed  no console window is ever created
REM  --onedir     reliable. The onefile bootloader can hang on some
REM               machines: the process parks in "PyInstaller Onefile
REM               Hidden Window" and the GUI never appears.
REM
REM  Usage:
REM    build_exe.bat            -> dist\QtExplorer\QtExplorer.exe
REM    build_exe.bat --onefile  -> single exe (may not launch)
REM =============================================================

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

REM "current" under versions is a symlink, so dir /b /s aborts the whole
REM scan. Walk the version folders with for /d instead.
if not defined PY for /d %%D in ("%USERPROFILE%\.workbuddy\binaries\python\versions\*") do (
  if exist "%%~fD\python.exe" if not defined PY set "PY=%%~fD\python.exe"
)

if not defined PY if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

if not defined PY for %%P in (python.exe py.exe) do if not defined PY (
  for /f "delims=" %%I in ('where %%P 2^>nul') do if not defined PY set "PY=%%I"
)

if not defined PY (
  echo [ERROR] Python not found.
  echo         Install Python 3.10+ from https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

"%PY%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installing PyInstaller...
  "%PY%" -m pip install -i https://pypi.org/simple pyinstaller
  if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    echo.
    pause
    exit /b 1
  )
)

echo [BUILD] Generating icon...
"%PY%" make_icon.py || echo [WARN] Icon generation failed, using default.

set "MODE=--onedir"
if /i "%~1"=="--onefile" set "MODE=--onefile"

echo [BUILD] Packaging with %MODE%, this takes a minute...
echo.

"%PY%" -m PyInstaller ^
  --noconfirm ^
  %MODE% ^
  --windowed ^
  --name "QtExplorer" ^
  --icon "%~dp0app_icon.ico" ^
  --add-data "%~dp0app_icon.ico;." ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.QtMultimedia ^
  --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtDataVisualization ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pytest ^
  --exclude-module tkinter ^
  "%~dp0run.py"

if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. Scroll up for details.
  echo.
  pause
  exit /b 1
)

echo.
if /i "%MODE%"=="--onedir" (
  echo [OK] Built: dist\QtExplorer\QtExplorer.exe
  echo.
  echo IMPORTANT: keep the whole QtExplorer folder together -
  echo the exe needs the _internal folder beside it.
  echo You can move that folder anywhere, or make a shortcut to the exe.
  echo.
  start "" "dist\QtExplorer\QtExplorer.exe" "C:\"
) else (
  echo [OK] Built: dist\QtExplorer.exe
  echo.
  echo NOTE: if double-clicking shows nothing, rebuild with the default
  echo       onedir mode -- the onefile bootloader is unreliable here.
)

endlocal