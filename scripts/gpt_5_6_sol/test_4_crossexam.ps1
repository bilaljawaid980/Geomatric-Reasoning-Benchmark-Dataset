param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Prepare1", "Run1", "Merge1", "Score1", "Prepare2", "Run2", "Merge2", "Score2")]
    [string]$Action,
    [ValidateRange(1, 4)]
    [int]$Batch = 1,
    [double]$MaxCostPhase1 = 3.00,
    [double]$MaxCostPhase2 = 8.00
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PlanRoot = "tests/test_4_crossexam/plan/gpt_5_6_sol"
$Round1Manifest = "$PlanRoot/crossexam_manifest_with_gpt_5_6_sol.csv"
$Round1Sample = "$PlanRoot/crossexam_sample_with_gpt_5_6_sol.csv"
$Round2Manifest = "$PlanRoot/crossexam_round2_manifest_with_gpt_5_6_sol.csv"
$Round2SkipLog = "$PlanRoot/crossexam_round2_skipped_with_gpt_5_6_sol.csv"
$BatchPlanRoot = "$PlanRoot/batches"
$BatchResultsRoot = "tests/test_4_crossexam/results/gpt_5_6_sol_batches"
$Models = "gpt_5_6_luna,inking,claude_opus_5,claude_sonnet_5,muse_glimmer_30b,gemini_3_8_flash,grok_4_6,gpt_5_6_sol"
Set-Location $RepoRoot

switch ($Action) {
    "Prepare1" {
        python tests/test_4_crossexam/scripts/build_crossexam_manifest.py `
            --models $Models `
            --output $Round1Manifest `
            --sample-output $Round1Sample
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        python tests/test_4_crossexam/scripts/prepare_crossexam_batches.py `
            --phase 1 `
            --model gpt_5_6_sol `
            --batches 4 `
            --manifest $Round1Manifest `
            --output-root $BatchPlanRoot
    }
    "Run1" {
        $BatchManifest = "$BatchPlanRoot/phase1/gpt_5_6_sol/batch_$Batch.csv"
        if (-not (Test-Path -LiteralPath $BatchManifest)) { throw "Run Prepare1 first." }
        python tests/test_4_crossexam/scripts/run_crossexam.py `
            --phase 1 `
            --model gpt_5_6_sol `
            --round1-manifest $BatchManifest `
            --results-dir "$BatchResultsRoot/phase1/gpt_5_6_sol/batch_$Batch" `
            --concurrency 1 `
            --max-cost $MaxCostPhase1
    }
    "Merge1" {
        python tests/test_4_crossexam/scripts/merge_crossexam_batches.py `
            --phase 1 `
            --model gpt_5_6_sol `
            --batches 4 `
            --manifest $Round1Manifest `
            --batch-results-root $BatchResultsRoot
    }
    "Score1" {
        python tests/test_4_crossexam/scripts/score_crossexam_round1.py `
            --model gpt_5_6_sol `
            --manifest $Round1Manifest `
            --output-root tests/test_4_crossexam/analysis/phase1
    }
    "Prepare2" {
        python tests/test_4_crossexam/scripts/build_crossexam_round2.py `
            --round1-manifest $Round1Manifest `
            --output $Round2Manifest `
            --skip-log $Round2SkipLog
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        python tests/test_4_crossexam/scripts/prepare_crossexam_batches.py `
            --phase 2 `
            --model gpt_5_6_sol `
            --batches 4 `
            --manifest $Round2Manifest `
            --output-root $BatchPlanRoot
    }
    "Run2" {
        $BatchManifest = "$BatchPlanRoot/phase2/gpt_5_6_sol/batch_$Batch.csv"
        if (-not (Test-Path -LiteralPath $BatchManifest)) { throw "Run Prepare2 first." }
        python tests/test_4_crossexam/scripts/run_crossexam.py `
            --phase 2 `
            --model gpt_5_6_sol `
            --round1-manifest $Round1Manifest `
            --round2-manifest $BatchManifest `
            --results-dir "$BatchResultsRoot/phase2/gpt_5_6_sol/batch_$Batch" `
            --concurrency 1 `
            --max-cost $MaxCostPhase2
    }
    "Merge2" {
        python tests/test_4_crossexam/scripts/merge_crossexam_batches.py `
            --phase 2 `
            --model gpt_5_6_sol `
            --batches 4 `
            --manifest $Round2Manifest `
            --batch-results-root $BatchResultsRoot
    }
    "Score2" {
        python tests/test_4_crossexam/scripts/score_crossexam.py `
            --models gpt_5_6_sol `
            --manifest $Round2Manifest `
            --output-dir tests/test_4_crossexam/analysis/gpt_5_6_sol
    }
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
