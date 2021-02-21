@echo off

set RH_BUILD_WORKDIR=..\
if exist %RH_BUILD_WORKDIR%*.cpp goto doRunCmd
set RH_BUILD_WORKDIR=
:doRunCmd
set RH_BUILD_PROJNAME=rhnode

cd %RH_BUILD_WORKDIR%
if not exist build_sil mkdir build_sil
echo on
g++ *.cpp sil\*.cpp -o build_sil\%RH_BUILD_PROJNAME%.exe
@echo off
:ex
