@echo off
setlocal
cd /d "%~dp0"
REM Weather extraction only after actual source-byte hash gates have PASSED.
python 06_RUNNABLE_TOOLS\extract_verified_five_month_weather.py
if errorlevel 1 (
  echo BLOCKED: Weather workbooks missing or failed hash/sheet extraction. See WEATHER_5_MONTH_RAW_EXTRACTED.
  exit /b 2
)
REM Recovering numeric weather rows does not prove unit/interval/spatial validation.
echo Five raw weather sheets extracted. Continue independent time, source grid, direction and rain-unit QA.
echo Road graph and FCD traffic must be validated separately; DO NOT run S10 yet.
