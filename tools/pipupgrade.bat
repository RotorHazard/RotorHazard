@echo off
if not exist "..\src\server\reqsNonPi.txt" goto check2
python -m pip install --upgrade --no-cache-dir -r ..\src\server\reqsNonPi.txt
goto ex
:check2
if not exist "src\server\reqsNonPi.txt" goto check3
python -m pip install --upgrade --no-cache-dir -r src\server\reqsNonPi.txt
goto ex
:check3
if not exist "reqsNonPi.txt" goto notfound
python -m pip install --upgrade --no-cache-dir -r reqsNonPi.txt
goto ex
:notfound
echo Unable to find 'reqsNonPi.txt' file
:ex
