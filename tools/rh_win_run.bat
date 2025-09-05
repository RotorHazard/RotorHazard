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

REM Determine location of RotorHazard program and installation directories
set rh_prog_dir=
set rh_install_dir=
if exist "..\src\server\server.py" (
    set rh_prog_dir=..\src\server\
    set rh_install_dir=..\
) else (
    if exist "src\server\server.py" (
        set rh_prog_dir=src\server\
    ) else (
        if exist "server.py" (
            set rh_prog_dir=
            set rh_install_dir=..\..\
        ) else (
            echo RH Win Launcher: Unable to find RotorHazard 'server.py' file; aborting
            pause
            exit /b 1
        )
    )
)

REM Determine location of Python virtual environment directory (if any)
set rh_venv_dir=
if exist "%VIRTUAL_ENV%\Scripts\activate.bat" (
    set "rh_venv_dir=%VIRTUAL_ENV%\"
) else (
    if exist "%rh_install_dir%.venv\Scripts\activate.bat" (
        set rh_venv_dir=%rh_install_dir%.venv\
    ) else (
        if exist "%USERPROFILE%\.venv\Scripts\activate.bat" (
            set "rh_venv_dir=%USERPROFILE%\.venv\"
        ) else (
            if exist "%rh_prog_dir%venv\Scripts\activate.bat" (
                set rh_venv_dir=%rh_prog_dir%venv\
            ) else (
                if exist "%rh_prog_dir%.venv\Scripts\activate.bat" (
                    set rh_venv_dir=%rh_prog_dir%.venv\
                )
            )
        )
    )
)

echo RH Win Launcher: Detected directories:
echo rh_prog_dir=%rh_prog_dir%
echo rh_install_dir=%rh_install_dir%
echo rh_venv_dir=%rh_venv_dir%
echo.

if not exist "%rh_venv_dir%Scripts\activate.bat" goto installpackages
if exist "%VIRTUAL_ENV%\Scripts\activate.bat" goto venvactive
echo RH Win Launcher: Activating Python virtual environment at: %rh_venv_dir%
call "%rh_venv_dir%Scripts\activate.bat"
goto venvnote
:venvactive
echo RH Win Launcher: Detected active Python venv at: %VIRTUAL_ENV%
set rh_venv_dir=
:venvnote
echo.
echo RH Win Launcher: Note - if you get 'ModuleNotFoundError: No module named...' errors delete the venv folder and re-run this script
goto runserver

:installpackages

echo RH Win Launcher: No virtual enviroment detected, the launcher will install the required packages

choice /n /c YN /m "Do you wish to continue? (Press Y or N): "
if %ERRORLEVEL% NEQ 1 (
    echo RH Win Launcher: Canceled via user input; aborting
    exit /b 1
)

set "rh_venv_dir=%rh_install_dir%.venv\"
echo RH Win Launcher: Creating Python virtual environment at: %rh_venv_dir%
python -m venv --system-site-packages %rh_venv_dir%
echo RH Win Launcher: Activating Python virtual environment at: %rh_venv_dir%
call "%rh_venv_dir%Scripts\activate.bat"
echo RH Win Launcher: Installing Python libraries for RotorHazard using: %rh_prog_dir%reqsNonPi.txt
python -m pip install -r %rh_prog_dir%reqsNonPi.txt

:runserver

REM Run the server script
echo.
echo RH Win Launcher: Starting RotorHazard server
echo RH Win Launcher: Once the server is running go to localhost:5000 in a browser to use RotorHazard
echo.
python %rh_prog_dir%server.py

REM If python venv was activated by this script then deactivate it now
if not "%rh_venv_dir%"=="" (
    if exist "%rh_venv_dir%Scripts\deactivate.bat" (
        call "%rh_venv_dir%Scripts\deactivate.bat"
    )
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    pause
)
