@echo off
set ARDUINO_CMD=arduino_debug.exe
if not exist "%ARDUINO_HOME%\%ARDUINO_CMD%" goto ardNotVar
set "ARDUINO_CMD=%ARDUINO_HOME%\%ARDUINO_CMD%"
goto ardFound
:ardNotVar
if not exist "C:\Program Files (x86)\Arduino\%ARDUINO_CMD%" goto ardNotFound
set "ARDUINO_CMD=C:\Program Files (x86)\Arduino\%ARDUINO_CMD%"
goto ardFound
:ardNotFound
echo Unable to run command: %ARDUINO_CMD%
goto ex
:ardFound

set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=rhnode

echo on
"%ARDUINO_CMD%" --verify --board esp32:esp32:esp32:PSRAM=disabled,PartitionScheme=default,CPUFreq=240,FlashMode=qio,FlashFreq=80,FlashSize=4M,UploadSpeed=921600,DebugLevel=none --pref "build.path=%RH_BUILD_WORKDIR%build_esp32" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %1 %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:ex
