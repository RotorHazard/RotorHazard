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
"%ARDUINO_CMD%" --verify --board esp8266:esp8266:generic:xtal=80,vt=flash,exception=disabled,stacksmash=disabled,ssl=all,mmu=3232,non32xfer=fast,ResetMethod=nodemcu,CrystalFreq=26,FlashFreq=40,FlashMode=dout,eesz=1M64,led=2,sdk=nonosdk_190703,ip=lm2f,dbg=Disabled,lvl=None____,wipe=none,baud=115200 --pref "build.path=%RH_BUILD_WORKDIR%build_arduino" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %1 %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:ex
