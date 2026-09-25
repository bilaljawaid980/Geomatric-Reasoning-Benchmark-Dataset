param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('gpt_5_6_luna', 'claude_opus_5', 'claude_sonnet_5', 'gemini_3_8_flash', 'grok_4_6', 'inking', 'muse_glimmer_30b')]
    [string]$Model,

    [Parameter(Mandatory = $true)]
    [ValidateSet(1, 2)]
    [int]$Phase,

    [Parameter(Mandatory = $true)]
    [ValidateRange(0.01, 1000.0)]
    [double]$MaxCostPerBatch,

    [ValidateRange(1, 16)]
    [int]$BatchCount = 4
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$pythonScript = 'tests/test_4_crossexam/scripts/run_crossexam.py'
$cost = $MaxCostPerBatch.ToString([System.Globalization.CultureInfo]::InvariantCulture)

for ($batch = 1; $batch -le $BatchCount; $batch++) {
    $manifest = "tests/test_4_crossexam/plan/batches/phase$Phase/$Model/batch_$batch.csv"
    $absoluteManifest = Join-Path $repoRoot $manifest
    if (-not (Test-Path -LiteralPath $absoluteManifest -PathType Leaf)) {
        throw "Missing batch manifest: $absoluteManifest. Run prepare_crossexam_batches.py first."
    }
    $resultDir = "tests/test_4_crossexam/results/batches/phase$Phase/$Model/batch_$batch"
    $command = "`$Host.UI.RawUI.WindowTitle='Test 4 - $Model - phase $Phase - batch $batch'; " +
        "python $pythonScript --phase $Phase --model $Model " +
        "--results-dir $resultDir --concurrency 1 --max-cost $cost"
    if ($Phase -eq 1) {
        $command += " --round1-manifest $manifest"
    }
    else {
        $command += " --round1-manifest tests/test_4_crossexam/plan/crossexam_manifest.csv " +
            "--round2-manifest $manifest " +
            "--round1-results-dir tests/test_4_crossexam/results"
    }
    Start-Process -FilePath 'powershell.exe' -WorkingDirectory $repoRoot -ArgumentList @(
        '-NoLogo', '-NoExit', '-Command', $command
    )
}

Write-Host "Started $BatchCount non-overlapping phase-$Phase batches for $Model."
