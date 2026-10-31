@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: RUN_WINDOWS_RECOVER_ALL.cmd "C:\path\to\JB-CIQ-GitHub-Repo"
  echo Or run: python 06_RUNNABLE_TOOLS\recover_all_14_sources.py --download
  exit /b 2
)
python 06_RUNNABLE_TOOLS\recover_all_14_sources.py --repo-root "%~1"
if errorlevel 1 (
  echo Some source files are MISSING or FAILED verification. See 05_AUDIT_REPORTS_AND_TEST_LOGS.
  exit /b 2
)
echo Source bytes verified; scientific weather and V5 road QA must still be performed.
