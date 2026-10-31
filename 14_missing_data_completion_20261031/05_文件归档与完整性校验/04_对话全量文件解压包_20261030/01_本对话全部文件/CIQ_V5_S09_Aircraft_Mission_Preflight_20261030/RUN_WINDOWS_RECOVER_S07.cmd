@echo off
setlocal
cd /d "%~dp0"
REM Download 11 pinned history files into recovered_sources, never overwrite existing bytes.
py -3 code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa --download
if errorlevel 1 exit /b 1
py -3 code\check_s07_sources.py --root .
REM Optional full V5 OSM graph requires osmnx 2.x and live Overpass; not historic roads.
REM py -3 code\acquire_v5_abc_directed_osm.py --nodes inputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out outputs\V5_ABC_OSM_CONDITIONAL --download
endlocal
