@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo No local GitHub directory specified: attempting pinned download.
  python code\s07_recover_and_gate.py --download
) else (
  echo Using local GitHub directory: "%~1"
  python code\s07_recover_and_gate.py --local-source "%~1" --download
)
if errorlevel 1 (
  echo HOLD: some sources not recovered or not verified. See qa\source_byte_gate.csv
  exit /b 2
)
echo All historical file bytes verified. Scientific S07 data release still needs semantic, road-access and V5 C-zone audits.
exit /b 0
