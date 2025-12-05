@echo off
echo Real-time Speech Translation System
echo ====================================

REM Check if virtual environment exists
if not exist "STS" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

#REM Activate virtual environment
#call venv\Scripts\activate

REM Check if activation was successful
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Run the main pipeline
echo Starting speech translation system...
echo Press Ctrl+C to stop
echo.
cd src
python main_pipeline.py

REM Deactivate on exit
call deactivate
pause
