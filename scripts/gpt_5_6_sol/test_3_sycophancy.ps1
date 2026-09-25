param(
    [ValidateSet("Prepare", "Run", "Score")]
    [string]$Action = "Prepare",
    [double]$MaxCost = 10.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_3_sycophancy/plan/sycophancy_manifest_gpt_5_6_sol.csv"
$SkipLog = "tests/test_3_sycophancy/plan/sycophancy_skipped_gpt_5_6_sol.csv"
Set-Location $RepoRoot

switch ($Action) {
    "Prepare" {
        python tests/test_3_sycophancy/scripts/build_sycophancy_manifest.py `
            --models gpt_5_6_sol `
            --output $Manifest `
            --skip-log $SkipLog
    }
    "Run" {
        if (-not (Test-Path -LiteralPath $Manifest)) {
            throw "Run Prepare first: .\scripts\gpt_5_6_sol\test_3_sycophancy.ps1 -Action Prepare"
        }
        python tests/test_3_sycophancy/scripts/run_sycophancy.py `
            --model gpt_5_6_sol `
            --manifest $Manifest `
            --concurrency 1 `
            --max-cost $MaxCost
    }
    "Score" {
        python tests/test_3_sycophancy/scripts/score_sycophancy.py `
            --models gpt_5_6_sol `
            --manifest $Manifest `
            --output-dir tests/test_3_sycophancy/analysis/gpt_5_6_sol
    }
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
