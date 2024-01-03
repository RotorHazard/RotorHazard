@echo off
cd C:\src\RotorHazard_WoP\src\server
if "%1"=="" goto noparam
start C:\src\RotorHazard_WoP\Python38\python.exe server.py --viewdb "%1" results
goto ex
:noparam
start C:\src\RotorHazard_WoP\Python38\python.exe server.py --launchb results
:ex
pause
popd