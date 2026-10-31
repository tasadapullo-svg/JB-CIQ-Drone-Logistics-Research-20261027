@echo off
setlocal
if "%~1"=="" (
  echo Usage: RUN_LOCAL_FROM_REPO.cmd "C:\path\to\JB-CIQ-Drone-Logistics-Research-20261027"
  exit /b 2
)
set BASE=%~dp0
python "%BASE%tools\ciq_s07\qa_real.py" --repo-root "%~1" --tools-dir "%BASE%tools\ciq_s07" --output "%BASE%qa\s07_actual_run"
exit /b %ERRORLEVEL%
