$ErrorActionPreference = 'Stop'
$RunDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CodeDir = Join-Path $RunDir 'code'
$WorkDir = Join-Path $RunDir 'work'

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @Arguments
    } else {
        & python @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "Python failed with exit code $LASTEXITCODE" }
}

Invoke-Python (Join-Path $CodeDir 'prepare_and_audit.py')

$Pairs = @(
    @('E08_E08', '0.8', '0.8'),
    @('E10_E10', '1.0', '1.0'),
    @('E12_E12', '1.2', '1.2'),
    @('D08_W12', '0.8', '1.2'),
    @('D12_W08', '1.2', '0.8')
)
foreach ($Pair in $Pairs) {
    Invoke-Python (Join-Path $CodeDir 'run_joint_dispatch.py') `
        --selected-scenarios (Join-Path $WorkDir 'SELECTED_SCENARIOS.csv') `
        --dji-energy-multiplier $Pair[1] --wing-energy-multiplier $Pair[2] `
        --chunk-label $Pair[0] --spatial STRICT_EXCLUDE_GT10KM --summary-only
}

Invoke-Python (Join-Path $CodeDir 'build_joint_results.py')
Invoke-Python (Join-Path $CodeDir 'run_joint_dispatch.py') `
    --selected-scenarios (Join-Path $WorkDir 'GOLDEN_SCENARIO.csv') `
    --dji-energy-multiplier 1.0 --wing-energy-multiplier 1.0 `
    --chunk-label GOLDEN --spatial STRICT_EXCLUDE_GT10KM
Invoke-Python (Join-Path $CodeDir 'finalize_minimal.py')
