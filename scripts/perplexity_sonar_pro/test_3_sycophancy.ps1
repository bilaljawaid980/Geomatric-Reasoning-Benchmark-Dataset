param(
    [ValidateSet("Prepare", "Run", "Score")]
    [string]$Action = "Prepare",
    [double]$MaxCost = 40.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_3_sycophancy/plan/sycophancy_manifest_perplexity_sonar_pro.csv"
$SkipLog = "tests/test_3_sycophancy/plan/sycophancy_skipped_perplexity_sonar_pro.csv"
Set-Location $RepoRoot

switch ($Action) {
    "Prepare" {
        python tests/test_3_sycophancy/scripts/build_sycophancy_manifest.py `
            --models perplexity_sonar_pro --output $Manifest --skip-log $SkipLog
    }
    "Run" {
        if (-not (Test-Path -LiteralPath $Manifest)) { throw "Run Prepare first." }
        python tests/test_3_sycophancy/scripts/run_sycophancy.py `
            --model perplexity_sonar_pro --manifest $Manifest `
            --concurrency 1 --max-cost $MaxCost
    }
    "Score" {
        python tests/test_3_sycophancy/scripts/score_sycophancy.py `
            --models perplexity_sonar_pro --manifest $Manifest `
            --output-dir tests/test_3_sycophancy/analysis/perplexity_sonar_pro
    }
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
