@echo off
REM Run this batch file to launch the Discord Rich Presence App
REM It will check/install requirements and then start the app

SETLOCAL

REM Check if requirements.txt exists
IF NOT EXIST requirements.txt (
    echo requirements.txt not found!
    exit /b 1
)

REM Check if pip is available
where pip >nul 2>nul
IF ERRORLEVEL 1 (
    echo pip not found! Please install Python and ensure pip is in your PATH.
    exit /b 1
)

REM Install missing requirements (will skip already installed packages)
echo Checking and installing required Python packages...
pip install --upgrade pip >nul
pip install -r requirements.txt

REM Launch the app
echo Starting the Discord Rich Presence App...
python main.py
