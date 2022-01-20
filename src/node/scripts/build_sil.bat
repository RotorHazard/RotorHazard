@echo off

setlocal
set PATH=C:\msys64\mingw64\bin
set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=rhnode%1

cd %RH_BUILD_WORKDIR%
if not exist build_sil mkdir build_sil
echo on
set ARDUINO_LIBS=%USERPROFILE%\Documents\Arduino\libraries
set MQTT_SRC=%ARDUINO_LIBS%\arduino-mqtt\src
set LWMQTT_SRC=%ARDUINO_LIBS%\arduino-mqtt\src\lwmqtt
gcc -c -Ofast %LWMQTT_SRC%\*.c
g++ -c -Ofast %MQTT_SRC%\*.cpp -Isil
g++ -Ofast -DMULTI_RHNODE_MAX=%1 *.cpp sil\*.cpp *.o -Isil -I%MQTT_SRC% -o build_sil\%RH_BUILD_PROJNAME%.exe -lws2_32
@echo off
:ex
endlocal
