param(
    [ValidateSet("Prepare", "Run", "Score")]
    [string]$Action = "Prepare",
    [double]$MaxCost = 2.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_3_sycophancy/plan/sycophancy_manifest_deepseek_v4_1_flash.csv"
$SkipLog = "tests/test_3_sycophancy/plan/sycophancy_skipped_deepseek_v4_1_flash.csv"
Set-Location $RepoRoot
switch ($Action) {
    "Prepare" {
        python tests/test_3_sycophancy/scripts/build_sycophancy_manifest.py `
            --models deepseek_v4_1_flash --output $Manifest --skip-log $SkipLog
    }
    "Run" {
        if (-not (Test-Path -LiteralPath $Manifest)) { throw "Run Prepare first." }
        python tests/test_3_sycophancy/scripts/run_sycophancy.py `
            --model deepseek_v4_1_flash --manifest $Manifest `
            --concurrency 1 --max-cost $MaxCost
    }
    "Score" {
        python tests/test_3_sycophancy/scripts/score_sycophancy.py `
            --models deepseek_v4_1_flash --manifest $Manifest `
            --output-dir tests/test_3_sycophancy/analysis/deepseek_v4_1_flash
    }
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
