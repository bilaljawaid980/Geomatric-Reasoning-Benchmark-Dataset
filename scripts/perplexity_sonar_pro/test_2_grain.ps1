param(
    [ValidateSet("Prepare", "Run", "Merge", "Score")]
    [string]$Action = "Prepare",
    [ValidateRange(1, 4)]
    [int]$Batch = 1,
    [double]$MaxCost = 25.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Manifest = "tests/test_2_grain_robustness/plan/grain_manifest.csv"
$BatchPlanRoot = "tests/test_2_grain_robustness/plan/perplexity_sonar_pro_batches"
$BatchResultsRoot = "tests/test_2_grain_robustness/results/perplexity_sonar_pro_batches"
Set-Location $RepoRoot

switch ($Action) {
    "Prepare" {
        python tests/test_2_grain_robustness/scripts/model_batches/prepare_batches.py `
            --model perplexity_sonar_pro --manifest $Manifest `
            --output-dir $BatchPlanRoot --shards 4
    }
    "Run" {
        $BatchManifest = "$BatchPlanRoot/batch_$Batch.csv"
        if (-not (Test-Path -LiteralPath $BatchManifest)) { throw "Run Prepare first." }
        python tests/test_2_grain_robustness/scripts/run_grain.py `
            --model perplexity_sonar_pro --manifest $BatchManifest `
            --results-dir "$BatchResultsRoot/batch_$Batch" `
            --sigmas 15,25,40 --concurrency 1 --max-cost $MaxCost
    }
    "Merge" {
        python tests/test_2_grain_robustness/scripts/model_batches/merge_batches.py `
            --model perplexity_sonar_pro --manifest $Manifest `
            --batch-root $BatchResultsRoot --shards 4
    }
    "Score" {
        python tests/test_2_grain_robustness/scripts/score_grain.py `
            --models perplexity_sonar_pro `
            --output-dir tests/test_2_grain_robustness/analysis/perplexity_sonar_pro
    }
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
