@echo off
setlocal
cd /d "%~dp0"
if not exist "qa" mkdir qa
if "%~1"=="" (
    python code\s07_recover_and_gate.py --download
) else (
    python code\s07_recover_and_gate.py --local-source "%~1"
)
echo === Byte gate completed; now performing strict numerical read-only QA ===
python code\s07_structural_numeric_check.py --sources recovered_sources --output outputs
python code\audit_v5_grid_event.py
python -m unittest discover -s tests -v > qa\TEST_RESULTS_WINDOWS.txt 2>&1
echo === Results ===
echo qa\S07_RELEASE_GATE.json
echo outputs\S07_CURRENT_NUMERIC_GATE.json
echo outputs\S07_V5_WEATHER_GRID_ACTUAL_GEOMETRIC_QA.json
pause
