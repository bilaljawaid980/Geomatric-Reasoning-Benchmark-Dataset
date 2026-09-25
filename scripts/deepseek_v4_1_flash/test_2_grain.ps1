param(
    [ValidateSet("Prepare", "Run", "Merge", "Score")]
    [string]$Action = "Prepare",
    [ValidateRange(1, 4)]
    [int]$Batch = 1,
    [double]$MaxCost = 1.50
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_2_grain_robustness/plan/grain_manifest.csv"
$BatchPlanRoot = "tests/test_2_grain_robustness/plan/deepseek_v4_1_flash_batches"
$BatchResultsRoot = "tests/test_2_grain_robustness/results/deepseek_v4_1_flash_batches"
Set-Location $RepoRoot
switch ($Action) {
    "Prepare" {
        python tests/test_2_grain_robustness/scripts/model_batches/prepare_batches.py `
            --model deepseek_v4_1_flash --manifest $Manifest `
            --output-dir $BatchPlanRoot --shards 4
    }
    "Run" {
        $BatchManifest = "$BatchPlanRoot/batch_$Batch.csv"
        if (-not (Test-Path -LiteralPath $BatchManifest)) { throw "Run Prepare first." }
        python tests/test_2_grain_robustness/scripts/run_grain.py `
            --model deepseek_v4_1_flash --manifest $BatchManifest `
            --results-dir "$BatchResultsRoot/batch_$Batch" `
            --sigmas 15,25,40 --concurrency 1 --max-cost $MaxCost
    }
    "Merge" {
        python tests/test_2_grain_robustness/scripts/model_batches/merge_batches.py `
            --model deepseek_v4_1_flash --manifest $Manifest `
            --batch-root $BatchResultsRoot --shards 4
    }
    "Score" {
        python tests/test_2_grain_robustness/scripts/score_grain.py `
            --models deepseek_v4_1_flash `
            --output-dir tests/test_2_grain_robustness/analysis/deepseek_v4_1_flash
    }
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
