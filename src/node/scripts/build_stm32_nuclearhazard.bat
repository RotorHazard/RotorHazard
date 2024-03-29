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
set RH_BUILD_PROJNAME=RH_S32_BPill_node

echo on
"%ARDUINO_CMD%" --verify --board STMicroelectronics:stm32:GenF1:pnum=BLUEPILL_F103C8 --pref compiler.cpp.extra_flags=-DNUCLEARHAZARD_HARDWARE --pref xserial=generic,usb=none,xusb=FS,opt=osstd,rtlib=nano --pref "build.path=%RH_BUILD_WORKDIR%build_stm32" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %1 %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:ex
pause