@echo off
set RH_FILES_DIR=..
if exist "%RH_FILES_DIR%\src\server\server.py" goto domkzip
set RH_FILES_DIR=.
:domkzip
del rhsrcfiles.zip >nul 2>&1
@echo on
7z a -r rhsrcfiles.zip "%RH_FILES_DIR%" -x!.git -xr0!.settings -xr0!src/libraries -xr-!src/node/build* -xr0!src/libraries -xr0!src/node/Release -xr0!src/libraries -xr0!src/node/core -x!db_bkp -x!cfg_bkp -x!logs -x!config.json -x!datapath.ini -x!*.db -x!*.pyc -x!__pycache__