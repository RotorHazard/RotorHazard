@echo off
set RH_PYTHON_DIR=C:\WinApps\Python39\
set RH_DIR_NAME=RotorHazard
set RH_FILES_DIR=..
set RH_PARENT_DIR=..\..
if exist "%RH_FILES_DIR%\src\server\server.py" goto domkzip
set RH_FILES_DIR=.
set RH_PARENT_DIR=..
:domkzip
del rhPortable.zip >nul 2>&1
del rhPortable.zip.tmp >nul 2>&1
@echo on
7z a -r rhPortable.zip "%RH_PARENT_DIR%\%RH_DIR_NAME%" -x!.git -xr0!%RH_DIR_NAME%/.settings -xr0!%RH_DIR_NAME%/src/libraries -xr0!%RH_DIR_NAME%/src/node/build* -xr0!%RH_DIR_NAME%/src/libraries -xr0!%RH_DIR_NAME%/src/node/Release -xr0!%RH_DIR_NAME%/src/libraries -xr0!%RH_DIR_NAME%/src/node/core -x!db_bkp -x!logs -x!config*.json -x!*.db -x!*.pyc -x!__pycache__
7z a -r rhPortable.zip "%RH_PYTHON_DIR%" -xr0!Python39\Lib\test -x!*.pyc -x!__pycache__
sleep 2
7z a rhPortable.zip "%RH_FILES_DIR%\tools\rhPortableFiles\runRotorHazard.bat" "%RH_FILES_DIR%\tools\rhPortableFiles\runRotorHazardFF.bat"
sleep 1
7z rn rhPortable.zip %RH_DIR_NAME%\ RotorHazardRun\
sleep 1
7z rn rhPortable.zip Python39\ RotorHazardRun\Python39\
sleep 1
7z a -r rhPortable.zip "%RH_FILES_DIR%\tools\rhPortableFiles\RotorHazardRun\"