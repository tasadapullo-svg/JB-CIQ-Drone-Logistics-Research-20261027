$ErrorActionPreference = 'Stop'
$stage = Split-Path -Parent $MyInvocation.MyCommand.Path
py (Join-Path $stage 'code\run_s09_mission_simulation.py')

