param(
    [ValidateSet("Run", "Score")]
    [string]$Action = "Run",
    [double]$MaxCost = 3.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot
if ($Action -eq "Run") {
    python tests/test_1_closed_loop/scripts/run_closed_loop.py `
        --model deepseek_v4_1_flash --concurrency 1 --max-cost $MaxCost
} else {
    python tests/test_1_closed_loop/scripts/score_closed_loop.py `
        --models deepseek_v4_1_flash `
        --output-dir tests/test_1_closed_loop/analysis/deepseek_v4_1_flash
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
