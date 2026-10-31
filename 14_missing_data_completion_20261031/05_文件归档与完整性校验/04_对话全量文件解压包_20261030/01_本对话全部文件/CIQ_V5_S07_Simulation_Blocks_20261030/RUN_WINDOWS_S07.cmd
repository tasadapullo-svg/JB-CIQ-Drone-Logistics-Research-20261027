@echo off
setlocal
cd /d "%~dp0"
REM This starts the real source-data acquisition. Requires Python 3.11+ and network.
REM IMPORTANT: Does NOT change frozen V5 and task inputs.
python code\build_paired_run_manifest.py --nodes inputs\V5_68_NODE_MASTER.csv --tasks inputs\V5_82620_CONDITIONAL_TASKS.csv --out outputs
python -m unittest discover -s tests -v
python code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa --download
python code\read_weather_workbooks.py --sources recovered_sources --index inputs\PINNED_SOURCE_INDEX.json --out outputs\WEATHER_RAW_EXTRACTED --sheet Weather_Hourly
REM Install osmnx for the next command: py -m pip install "osmnx>=2,<3" scipy
python code\acquire_v5_abc_directed_osm.py --nodes inputs\V5_68_NODE_MASTER.csv --out outputs\V5_ABC_OSM_CANDIDATES --download
REM Do not publish results until weather units, interval semantics, road access and timestamps pass independent QA.
python code\validate_s07_external_data.py --node-master inputs\V5_68_NODE_MASTER.csv --out qa\S07_OPERATIONAL_SOURCE_GATE_ACTUAL.json
pause
