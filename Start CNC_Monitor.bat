@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python was not found.
    echo.
    echo Install Python 3 and enable "Add python.exe to PATH",
    echo or edit this file and set the full path to python.exe.
    echo.
    pause
    exit /b 1
)

echo Using: %PYTHON_CMD%
echo.
%PYTHON_CMD% cnc_monitor.py

echo.
echo CNC Monitor stopped or failed. See the message above.
pause
