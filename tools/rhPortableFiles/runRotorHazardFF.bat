@echo off
set RH_RUN_DIR=%~d0%~p0RotorHazardRun
set RH_DATA_DIR=%RH_RUN_DIR%\rh-data
SET FF_PROG="C:\Program Files\Mozilla Firefox\firefox.exe"
if exist %FF_PROG% goto cont
SET FF_PROG=
:cont
if "%1"=="" goto noparam
start %RH_RUN_DIR%\python39\python %RH_RUN_DIR%\src\server\server.py --data %RH_DATA_DIR% --viewdb "%1" --launchb results %FF_PROG%
goto ex
:noparam
start %RH_RUN_DIR%\python39\python %RH_RUN_DIR%\src\server\server.py --data %RH_DATA_DIR% --launchb results %FF_PROG%
:ex
