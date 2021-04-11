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

if exist util\stm32loader.py goto stmLdrFound
echo Unable to find program file: util\stm32loader.py
goto ex
:stmLdrFound

set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=RH_S32_BPill_node_STM32F4

if not "%1"=="" goto doRunCont
echo Serial port for upload must be specified as first parameter
goto ex
:doRunCont
set RH_UPLOAD_SERIALPORT=%1

if "%2"=="--skipBuild" goto doUpload
echo on
"%ARDUINO_CMD%" --verify --board STM32:stm32:GenF4:pnum=BLACKPILL_F411CE --pref compiler.cpp.extra_flags=-DSTM32_F4_PROCTYPE --pref xserial=generic,usb=none,xusb=FS,opt=osstd,rtlib=nano --pref "build.path=%RH_BUILD_WORKDIR%build_stm32_f4" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:doUpload
echo on
python util\stm32loader.py %RH_UPLOAD_SERIALPORT% "%RH_BUILD_WORKDIR%build_stm32\%RH_BUILD_PROJNAME%.bin"
@echo off
:ex
