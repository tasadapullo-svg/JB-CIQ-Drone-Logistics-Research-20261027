@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements_osm_optional.txt
if errorlevel 1 goto :fail
py code\acquire_v5_abc_directed_osm.py --nodes outputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out outputs\V5_ABC_OSM_CONDITIONAL --download
ECHO CHECK outputs\V5_ABC_OSM_CONDITIONAL\V5_ABC_OSM_DOWNLOAD_AUDIT.json
ECHO A nearest OSM node is NOT approved entrance. Do not run emission effects from this alone.
pause
exit /b 0
:fail
ECHO Installation failed. No geometry changes.
pause
exit /b 1
