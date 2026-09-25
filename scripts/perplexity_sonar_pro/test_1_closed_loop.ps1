param(
    [ValidateSet("Run", "Score")]
    [string]$Action = "Run",
    [double]$MaxCost = 80.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

if ($Action -eq "Run") {
    python tests/test_1_closed_loop/scripts/run_closed_loop.py `
        --model perplexity_sonar_pro --concurrency 1 --max-cost $MaxCost
} else {
    python tests/test_1_closed_loop/scripts/score_closed_loop.py `
        --models perplexity_sonar_pro `
        --output-dir tests/test_1_closed_loop/analysis/perplexity_sonar_pro
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
