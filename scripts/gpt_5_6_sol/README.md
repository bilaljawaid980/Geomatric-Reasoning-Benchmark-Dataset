# GPT-5.6 Sol evaluation launchers

These launchers use the shared `gpt_5_6_sol` configuration, with reasoning
disabled (`effort: none`), the OpenAI provider pinned with fallbacks disabled,
concurrency 1, resumable JSONL outputs, and explicit cost ceilings.

Run from the repository root in this order:

```powershell
# Test 1: closed loop
.\scripts\gpt_5_6_sol\test_1_closed_loop.ps1 -Action Run
.\scripts\gpt_5_6_sol\test_1_closed_loop.ps1 -Action Score

# Test 2: prepare four disjoint image-level batches
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Prepare

# Run these four commands in four separate terminals
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Run -Batch 1
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Run -Batch 2
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Run -Batch 3
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Run -Batch 4

# Merge only after all four batches finish, then score
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Merge
.\scripts\gpt_5_6_sol\test_2_grain.ps1 -Action Score

# Test 3: answer sycophancy (requires completed Test 1)
.\scripts\gpt_5_6_sol\test_3_sycophancy.ps1 -Action Prepare
.\scripts\gpt_5_6_sol\test_3_sycophancy.ps1 -Action Run
.\scripts\gpt_5_6_sol\test_3_sycophancy.ps1 -Action Score

# Test 4 Phase 1: prepare once, run each batch in a separate terminal
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Prepare1
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run1 -Batch 1
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run1 -Batch 2
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run1 -Batch 3
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run1 -Batch 4
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Merge1
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Score1

# Test 4 Phase 2: only after Phase 1 is merged
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Prepare2
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run2 -Batch 1
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run2 -Batch 2
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run2 -Batch 3
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Run2 -Batch 4
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Merge2
.\scripts\gpt_5_6_sol\test_4_crossexam.ps1 -Action Score2
```

Rerunning the same `Run` command resumes from successful rows already written.
The default maximum ceilings are safeguards, not cost estimates: Test 1 $18,
Test 2 $6 per batch, Test 3 $10, Test 4 Phase 1 $3 per batch, and Test 4 Phase
2 $8 per batch. Override a ceiling only when necessary, for example
`-MaxCostPhase2 10.00`.
