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
    exit /b 1
)

REM 🔧 пробуємо pythonw
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" /min pythonw cnc_monitor.py
) else (
    REM fallback якщо pythonw нема
    start "" /min %PYTHON_CMD% cnc_monitor.py
)