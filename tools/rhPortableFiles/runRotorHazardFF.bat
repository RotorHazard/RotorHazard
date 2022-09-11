@echo off
pushd %~d0%~p0RotorHazardRun\src\server
SET ffprog="C:\Program Files\Mozilla Firefox\firefox.exe"
if exist %ffprog% goto cont
SET ffprog=
:cont
if "%1"=="" goto noparam
start ..\..\python38\python server.py --viewdb "%1" results %ffprog%
goto ex
:noparam
start ..\..\python38\python server.py --launchb results %ffprog%
:ex
popd
