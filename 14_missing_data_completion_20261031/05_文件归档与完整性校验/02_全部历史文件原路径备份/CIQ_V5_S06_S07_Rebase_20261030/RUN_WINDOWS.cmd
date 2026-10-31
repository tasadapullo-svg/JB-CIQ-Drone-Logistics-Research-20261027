@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=py)
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto :fail
%PY% code\build_v5_rebase_and_synthetic_tasks.py --root .
if errorlevel 1 goto :fail
%PY% code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa --download
%PY% code\v5_s07_source_gate.py .
%PY% code\read_weather_workbooks.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out outputs\weather_raw
%PY% code\audit_legacy_road_graph.py --sources recovered_sources --nodes outputs\S06_V5_68_NODE_MASTER_AUTHORITATIVE.csv --out outputs\legacy_AB_road_QA
%PY% -m unittest discover -s tests -v > qa\windows_test_log.txt 2>&1
if errorlevel 1 goto :fail
ECHO V5 S06/S07 data audit finished. Review qa\S07_V5_SOURCE_RELEASE_GATE.json
ECHO DO NOT CLAIM M0/M1/M2 RESULTS BEFORE GATES PASS.
pause
exit /b 0
:fail
ECHO ERROR: inspect qa and command output. Source project not changed.
pause
exit /b 1
