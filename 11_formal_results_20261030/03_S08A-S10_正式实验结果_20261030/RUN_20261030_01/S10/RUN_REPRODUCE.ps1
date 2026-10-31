$ErrorActionPreference = 'Stop'
$stage = Split-Path -Parent $MyInvocation.MyCommand.Path
# Small integration test. Full run supports four --start/--limit/--chunk-label partitions.
py (Join-Path $stage 'code\run_s10_five_mode.py') --limit 10

