# DeepSeek V4.1 Flash launchers

Model key: `deepseek_v4_1_flash`. Reasoning is disabled, OpenRouter routing is
latency-sorted, concurrency is 1, and results are resumable.

Use the same action order documented in `scripts/gpt_5_6_sol/README.md`,
replacing `gpt_5_6_sol` in the script path with `deepseek_v4_1_flash`.
Tests 2 and 4 use four non-overlapping batches. Test 3 requires completed
Test 1, and Test 4 Phase 2 requires merged Phase 1 results.

Default safety ceilings are: Test 1 `$3`; Test 2 `$1.50` per batch; Test 3
`$2`; Test 4 Phase 1 `$0.75` per batch; Test 4 Phase 2 `$2` per batch.
