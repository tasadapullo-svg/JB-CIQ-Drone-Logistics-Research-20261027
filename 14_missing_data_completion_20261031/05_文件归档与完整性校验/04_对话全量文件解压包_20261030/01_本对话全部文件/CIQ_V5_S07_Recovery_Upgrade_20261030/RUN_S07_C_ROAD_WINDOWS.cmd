@echo off
setlocal
cd /d "%~dp0"
python -m pip install osmnx==2.0.6
if errorlevel 1 exit /b 2
python code\acquire_v5_abc_directed_osm.py --nodes inputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out road_v5_abc --download
if errorlevel 1 exit /b 2
echo Saved V5 ABC candidate graph. NOT a verified legal access network or historical May-Sep 2026 snapshot.
