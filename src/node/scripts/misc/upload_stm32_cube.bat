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

set CUBEPROG_CMD=stm32CubeProg.bat
if not exist "%STM32CUBE_HOME%\%CUBEPROG_CMD%" goto notCubeHome
set "CUBEPROG_CMD=%STM32CUBE_HOME%\%CUBEPROG_CMD%"
goto cubeFound
:notCubeHome
if not exist "%HOMEDRIVE%%HOMEPATH%\AppData\Local\Arduino15\packages\STM32\tools\STM32Tools\1.4.0\tools\win\%CUBEPROG_CMD%" goto cubeNotFound
set "CUBEPROG_CMD=%HOMEDRIVE%%HOMEPATH%\AppData\Local\Arduino15\packages\STM32\tools\STM32Tools\1.4.0\tools\win\%CUBEPROG_CMD%"
goto cubeFound
:cubeNotFound
if exist "%CUBEPROG_CMD%" goto cubeFound
echo Unable to find program file: %CUBEPROG_CMD%
goto ex
:cubeFound

set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=rhnode
if not "%1"=="" goto doRunCont
echo Serial port for upload must be specified as first parameter
goto ex
:doRunCont
set RH_UPLOAD_SERIALPORT=%1

if "%2"=="--skipBuild" goto doUpload
echo on
"%ARDUINO_CMD%" --verify --board STM32:stm32:GenF1:pnum=BLUEPILL_F103C8 --pref xserial=generic,usb=none,xusb=FS,opt=osstd,rtlib=nano --pref "build.path=%RH_BUILD_WORKDIR%build_stm32" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:doUpload
echo on
cmd /C "%CUBEPROG_CMD% 1 %RH_BUILD_WORKDIR%build_stm32\%RH_BUILD_PROJNAME%.bin %RH_UPLOAD_SERIALPORT% -s"
@echo off
:ex
