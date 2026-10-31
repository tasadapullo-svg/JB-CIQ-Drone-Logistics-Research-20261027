@echo off
setlocal
cd /d "%~dp0"
python code\build_s07_event_contract.py --root .
python -m unittest discover -s tests -v
python code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa --download
python code\read_weather_workbooks.py --sources recovered_sources --index inputs\PINNED_SOURCE_INDEX.json --out outputs\weather_xlsx_raw_only --sheet Weather_Hourly
python code\acquire_v5_abc_directed_osm.py --nodes inputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out outputs\V5_ABC_OSM_CANDIDATES --download
python code\validate_s07_external_data.py --node-master inputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out qa\S07_OPERATIONAL_SOURCE_GATE_ACTUAL.json
ECHO.
ECHO If weather/road is still HOLD, review the logs and attach recovered source files.
ECHO Do not publish M0/M1/M2 emission results until external data and access QA pass.
pause
