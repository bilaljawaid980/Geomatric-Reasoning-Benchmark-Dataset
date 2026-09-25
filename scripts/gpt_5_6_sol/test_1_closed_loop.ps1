param(
    [ValidateSet("Run", "Score")]
    [string]$Action = "Run",
    [double]$MaxCost = 18.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

if ($Action -eq "Run") {
    python tests/test_1_closed_loop/scripts/run_closed_loop.py `
        --model gpt_5_6_sol `
        --concurrency 1 `
        --max-cost $MaxCost
} else {
    python tests/test_1_closed_loop/scripts/score_closed_loop.py `
        --models gpt_5_6_sol `
        --output-dir tests/test_1_closed_loop/analysis/gpt_5_6_sol
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
