@echo off
setlocal
cd /d "%~dp0"
if not exist recovered_sources mkdir recovered_sources
if not exist qa mkdir qa
if not exist outputs mkdir outputs
REM This command downloads sources only from a fixed immutable Git commit and verifies each file.
py -3 code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa --download
REM Extraction preserves raw units/timestamps; no fabricated weather observations.
py -3 code\read_weather_workbooks.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out outputs --sheet Weather_Hourly
REM A/B old topology candidate only; C and 7 special reference nodes remain HOLD.
py -3 code\audit_legacy_road_graph.py --sources recovered_sources --nodes inputs\S06_69_node_master.csv --out outputs
REM Prefer independent ERA5 CSV numeric evidence, otherwise status is HOLD.
py -3 code\join_verified_era5_to_nodes.py --source recovered_sources\E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv --assignment inputs\S07_05_node_to_weather_grid_69_CANDIDATES_ONLY.csv --timeline inputs\S07_03_hourly_timeline_3672.csv --out outputs
py -3 code\s07_release_gate.py --root .
py -3 -m unittest discover -s tests -p "test*.py" -v > qa\unit_test_log_windows.txt 2>&1
ECHO.
ECHO Review qa\actual_source_recovery_status.csv and qa\S07_R2_release_record.json
ECHO Do not run M0/M1/M2 while release_M0_M1_M2 is false.
pause
