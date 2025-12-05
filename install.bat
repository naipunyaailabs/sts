@echo off
echo Real-time Speech Translation System - Installation Script
echo ========================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found, continuing with installation...

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    echo Try running as administrator or check your internet connection
    pause
    exit /b 1
)

REM Install the package
echo Installing the speech translation system...
pip install -e .
if errorlevel 1 (
    echo ERROR: Failed to install package
    pause
    exit /b 1
)

echo.
echo Installation completed successfully!
echo.
echo To run the system:
echo   1. Activate the virtual environment: venv\Scripts\activate
echo   2. Run the system: python src\main_pipeline.py
echo.
echo Or simply run: run.bat
echo.
pause
