@echo off
set RH_RUN_DIR=%~d0%~p0RotorHazardRun
set RH_DATA_DIR=%RH_RUN_DIR%\rh-data
if "%1"=="" goto noparam
start %RH_RUN_DIR%\python39\python %RH_RUN_DIR%\src\server\server.py --data %RH_DATA_DIR% --viewdb "%1" results
goto ex
:noparam
start %RH_RUN_DIR%\python39\python %RH_RUN_DIR%\src\server\server.py --data %RH_DATA_DIR% results
:ex
