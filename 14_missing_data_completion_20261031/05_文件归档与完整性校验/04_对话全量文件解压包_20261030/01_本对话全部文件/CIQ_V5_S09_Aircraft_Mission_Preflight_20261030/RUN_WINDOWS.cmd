@echo off
setlocal
cd /d "%~dp0"
py -3 code\build_s09_preflight.py --root .
if errorlevel 1 exit /b 1
py -3 code\check_s07_sources.py --root .
if errorlevel 1 exit /b 1
py -3 -m unittest discover -s tests -v
endlocal
