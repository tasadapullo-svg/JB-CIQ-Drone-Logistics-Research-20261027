@echo off
setlocal
cd /d "%~dp0"
python code\run_actual_task_screen.py
if errorlevel 1 exit /b 1
python code\strict_m0_release_gate.py
if errorlevel 1 exit /b 1
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
echo Completed: payload-only screening and S08 fuel method tests. Full M0 research results remain HOLD until sourced roads and gasoline parameters are verified.
pause
