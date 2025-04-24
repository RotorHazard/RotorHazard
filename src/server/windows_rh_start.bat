@echo off

echo ############################
echo.
echo RotorHazard Windows Launcher
echo.
echo ############################
echo.
echo RH Win Launcher: Once the server is running go to localhost:5000 in a browser to use RotorHazard
echo.

REM Check if venv directory exists
if not exist venv\ (
    echo RH Win Launcher: No virtual enviroment detected, the launcher will install the required packages
    python -m venv venv
	call venv\Scripts\activate
	pause
	pip install -r reqsNonPi.txt
) else (
    echo RH Win Launcher: Virtual environment exists. 
	echo RH Win Launcher: If you get ModuleNotFoundError: No module named errors delete the venv folder and re-run this script
	echo.
	call venv\Scripts\activate
	pause
)

REM Run the server script
echo RH Win Launcher: Starting RotorHazard server
python server.py

pause