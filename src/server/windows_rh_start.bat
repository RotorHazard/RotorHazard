@echo off

echo ############################
echo.
echo RotorHazard Windows Launcher
echo.
echo ############################
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo RH Win Launcher: Python is not installed or not in PATH, please install python from the Microsoft store and re-run this script
	pause
	exit /b 1
)

echo RH Win Launcher: Once the server is running go to localhost:5000 in a browser to use RotorHazard
echo.

REM Check if venv directory exists
if not exist venv\ (
    echo RH Win Launcher: No virtual enviroment detected, the launcher will install the required packages...
    python -m venv venv
	call venv\Scripts\activate
	pip install -r reqsNonPi.txt
) else (
    echo RH Win Launcher: Virtual environment exists. 
	echo RH Win Launcher: If you get ModuleNotFoundError: No module named errors delete the venv folder and re-run this script
	echo.
	call venv\Scripts\activate
)

REM Run the server script
echo RH Win Launcher: Starting RotorHazard server
python server.py

pause