param(
    [ValidateSet("Prepare", "Run", "Merge", "Score")]
    [string]$Action = "Prepare",
    [ValidateRange(1, 4)]
    [int]$Batch = 1,
    [double]$MaxCost = 6.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_2_grain_robustness/plan/grain_manifest.csv"
$BatchPlanRoot = "tests/test_2_grain_robustness/plan/gpt_5_6_sol_batches"
$BatchResultsRoot = "tests/test_2_grain_robustness/results/gpt_5_6_sol_batches"
Set-Location $RepoRoot

switch ($Action) {
    "Prepare" {
        python tests/test_2_grain_robustness/scripts/model_batches/prepare_batches.py `
            --model gpt_5_6_sol `
            --manifest $Manifest `
            --output-dir $BatchPlanRoot `
            --shards 4
    }
    "Run" {
        $BatchManifest = "$BatchPlanRoot/batch_$Batch.csv"
        if (-not (Test-Path -LiteralPath $BatchManifest)) {
            throw "Run Prepare first: .\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Prepare"
        }
        python tests/test_2_grain_robustness/scripts/run_grain.py `
            --model gpt_5_6_sol `
            --manifest $BatchManifest `
            --results-dir "$BatchResultsRoot/batch_$Batch" `
            --sigmas 15,25,40 `
            --concurrency 1 `
            --max-cost $MaxCost
    }
    "Merge" {
        python tests/test_2_grain_robustness/scripts/model_batches/merge_batches.py `
            --model gpt_5_6_sol `
            --manifest $Manifest `
            --batch-root $BatchResultsRoot `
            --shards 4
    }
    "Score" {
        python tests/test_2_grain_robustness/scripts/score_grain.py `
            --models gpt_5_6_sol `
            --output-dir tests/test_2_grain_robustness/analysis/gpt_5_6_sol
    }
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
