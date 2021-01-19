@echo off
set ARDUINO_CMD=arduino_debug.exe
set AVRDUDE_CMD=avrdude.exe
set AVRDUDE_CONF=avrdude.conf
if not exist "%ARDUINO_HOME%\%ARDUINO_CMD%" goto ardNotVar
set "ARDUINO_CMD=%ARDUINO_HOME%\%ARDUINO_CMD%"
set "AVRDUDE_CMD=%ARDUINO_HOME%\hardware\tools\avr\bin\%AVRDUDE_CMD%"
set "AVRDUDE_CONF=%ARDUINO_HOME%\hardware\tools\avr\etc\%AVRDUDE_CONF%"
goto ardFound
:ardNotVar
if not exist "C:\Program Files (x86)\Arduino\%ARDUINO_CMD%" goto ardNotFound
set "ARDUINO_CMD=C:\Program Files (x86)\Arduino\%ARDUINO_CMD%"
set "AVRDUDE_CMD=C:\Program Files (x86)\Arduino\hardware\tools\avr\bin\%AVRDUDE_CMD%"
set "AVRDUDE_CONF=C:\Program Files (x86)\Arduino\hardware\tools\avr\etc\%AVRDUDE_CONF%"
goto ardFound
:ardNotFound
echo Unable to run command: %ARDUINO_CMD%
goto ex
:ardFound

if exist "%AVRDUDE_CMD%" goto avrFound
echo Unable to find program: %AVRDUDE_CMD%
goto ex
:avrFound

set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=rhnode
set RH_UPLOAD_BAUDRATE=115200

if not "%1"=="" goto doRunCont
echo Serial port for upload must be specified as first parameter
goto ex
:doRunCont
set RH_UPLOAD_SERIALPORT=%1

if "%2"=="--skipBuild" goto doUpload
echo on
"%ARDUINO_CMD%" --verify --board arduino:avr:nano:cpu=atmega328 --pref "build.path=%RH_BUILD_WORKDIR%build_arduino" --pref build.project_name=%RH_BUILD_PROJNAME% "%RH_BUILD_WORKDIR%rhnode.cpp" %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:doUpload
echo on
"%AVRDUDE_CMD%" "-C%AVRDUDE_CONF%" -v -patmega328p -carduino -P%RH_UPLOAD_SERIALPORT% -b%RH_UPLOAD_BAUDRATE% -D "-Uflash:w:%RH_BUILD_WORKDIR%build_arduino/%RH_BUILD_PROJNAME%.hex:i"
@echo off
:ex
