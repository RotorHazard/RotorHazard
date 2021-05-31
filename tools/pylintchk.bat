@echo off
REM To install pylint:  python -m pip install pylint
set RH_SRC_DIR=src
if not exist "..\src\server\server.py" goto doscan
set RH_SRC_DIR=..\src
:doscan
echo ------------
echo Scanning 'interface' directory
for %%f in (%RH_SRC_DIR%\interface\*.py) do pylint --errors-only %%f
echo ------------
echo Scanning 'server' directory
for %%f in (%RH_SRC_DIR%\server\*.py) do pylint --errors-only %%f
echo ------------
echo Scanning 'server\util' directory
for %%f in (%RH_SRC_DIR%\server\util\*.py) do pylint --errors-only %%f
