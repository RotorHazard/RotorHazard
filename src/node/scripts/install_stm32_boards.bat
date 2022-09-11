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

echo on
"%ARDUINO_CMD%" --pref boardsmanager.additional.urls=https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json --install-boards STMicroelectronics:stm32 %1 %2 %3 %4 %5 %6 %7 %8 %9
@echo off
:ex
