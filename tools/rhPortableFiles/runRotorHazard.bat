@echo off
pushd %~d0%~p0RotorHazardRun\src\server
if "%1"=="" goto noparam
start ..\..\python39\python server.py --viewdb "%1" results
goto ex
:noparam
start ..\..\python39\python server.py --launchb results
:ex
popd
