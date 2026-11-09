@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Patient Food AI - Offline System

echo ==============================================
echo   Patient Food Recommendation System
echo ==============================================
echo.

REM Find Python without using any computer-specific user path.
set "PYTHON="

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 -c "import sys; print(sys.executable)" > "%TEMP%\patient_food_python_path.txt" 2>nul
    if exist "%TEMP%\patient_food_python_path.txt" set /p PYTHON=<"%TEMP%\patient_food_python_path.txt"
)

if not defined PYTHON (
    where python >nul 2>&1
    if %errorlevel%==0 (
        for /f "delims=" %%P in ('where python') do if not defined PYTHON set "PYTHON=%%P"
    )
)

if not defined PYTHON (
    echo Python was not found on this computer.
    echo.
    echo Please install Python 3.11 or newer from:
    echo https://www.python.org/downloads/windows/
    echo.
    echo IMPORTANT: During installation, enable "Add python.exe to PATH".
    echo Then run this file again.
    echo.
    pause
    exit /b 1
)

echo Python found:
"%PYTHON%" --version
if errorlevel 1 goto PythonError

echo.
if not exist "venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    "%PYTHON%" -m venv venv
    if errorlevel 1 goto VenvError
)

set "VENV_PY=%CD%\venv\Scripts\python.exe"
if not exist "%VENV_PY%" goto VenvError

echo.
echo Installing required packages...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto PipError

echo.
echo Starting application...
echo.
echo Open this address in your browser if it does not open automatically:
echo http://127.0.0.1:5000
echo.

start "Patient Food AI" /min cmd /c "timeout /t 2 /nobreak ^>nul ^& start http://127.0.0.1:5000"
"%VENV_PY%" app.py

pause
exit /b 0

:PythonError
echo.
echo The detected Python installation could not be used.
pause
exit /b 1

:VenvError
echo.
echo Could not create the local Python environment.
echo Make sure Python is installed correctly and try again.
pause
exit /b 1

:PipError
echo.
echo Required packages could not be installed.
echo Check your internet connection for the first setup, then run this file again.
pause
exit /b 1
