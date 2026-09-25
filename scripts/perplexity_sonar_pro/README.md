# Perplexity Sonar Pro launchers

Model key: `perplexity_sonar_pro`. The Perplexity provider is pinned,
fallbacks are disabled, concurrency is 1, and results are resumable.

Use the same action order documented in `scripts/gpt_5_6_sol/README.md`,
replacing `gpt_5_6_sol` in the script path with `perplexity_sonar_pro`.
Tests 2 and 4 use four non-overlapping batches. Test 3 requires completed
Test 1, and Test 4 Phase 2 requires merged Phase 1 results.

Default safety ceilings are: Test 1 `$80`; Test 2 `$25` per batch; Test 3
`$40`; Test 4 Phase 1 `$8` per batch; Test 4 Phase 2 `$30` per batch.
