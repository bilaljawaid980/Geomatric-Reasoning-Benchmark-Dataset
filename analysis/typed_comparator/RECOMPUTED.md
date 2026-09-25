# Full typed-comparator recomputation

All values are computed offline from stored responses. Strict scores remain intact. Typed scores are counterfactual and have not replaced any published result.

## Test 1: overall

| Model | Strict raw | Typed raw | Strict adjusted macro | Typed adjusted macro |
|---|---|---|---|---|
| Claude Opus 5 | 61.74% | 65.96% | 41.98% | 47.50% |
| Claude Sonnet 5 | 49.84% | 54.25% | 23.65% | 29.62% |
| DeepSeek V4.1 Flash | 42.81% | 46.15% | 6.18% | 8.50% |
| Gemini 3.8 Flash | 64.12% | 68.89% | 44.82% | 50.72% |
| GPT-5.6 Luna | 41.98% | 44.99% | 6.96% | 10.46% |
| GPT-5.6 Sol | 50.51% | 54.41% | 22.91% | 27.87% |
| Grok 4.6 | 52.44% | 57.07% | 28.01% | 33.67% |
| Inkling | 38.46% | 41.31% | 1.94% | 4.79% |
| Muse Glimmer 30B | 43.72% | 47.74% | 8.44% | 12.89% |
| Perplexity Sonar Pro | 40.29% | 43.20% | 4.15% | 5.65% |

The complete **1,700 model × cell** table—including strict/typed correct counts, raw accuracy, constant-answer baseline, adjusted score, modal target, and exclusion flags—is [`before_after.csv`](before_after.csv). Complete per-level, per-family, per-domain, macro, and pooled aggregates are in [`aggregates.csv`](aggregates.csv).

## L4-to-L5 adjusted difference

The intervals use the requested 10,000-resample domain-stratified image-cluster bootstrap.

| Model | Strict Δ | Strict verdict | Typed Δ | Typed 95% CI | Typed verdict |
|---|---|---|---|---|---|
| Claude Opus 5 | +6.90 pp | survives | +11.35 pp | +6.71 to +16.00 pp | survives |
| Claude Sonnet 5 | -10.47 pp | reverses | -8.04 pp | -13.87 to -2.24 pp | reverses |
| DeepSeek V4.1 Flash | -22.90 pp | reverses | -27.01 pp | -33.12 to -20.78 pp | reverses |
| Gemini 3.8 Flash | -0.19 pp | indistinguishable from zero | +7.40 pp | +2.45 to +12.43 pp | survives |
| GPT-5.6 Luna | -18.98 pp | reverses | -21.39 pp | -27.91 to -14.80 pp | reverses |
| GPT-5.6 Sol | -12.74 pp | reverses | -9.35 pp | -14.96 to -3.81 pp | reverses |
| Grok 4.6 | -4.57 pp | indistinguishable from zero | +4.88 pp | +0.12 to +9.63 pp | survives |
| Inkling | -28.65 pp | reverses | -25.83 pp | -32.15 to -19.39 pp | reverses |
| Muse Glimmer 30B | -29.12 pp | reverses | -27.89 pp | -33.22 to -22.56 pp | reverses |
| Perplexity Sonar Pro | -15.99 pp | reverses | -5.92 pp | -13.13 to +1.40 pp | indistinguishable from zero |

Verdict changes:

- **Claude Opus 5:** remains survives.
- **Claude Sonnet 5:** remains reverses.
- **DeepSeek V4.1 Flash:** remains reverses.
- **Gemini 3.8 Flash:** changes from indistinguishable from zero to survives.
- **GPT-5.6 Luna:** remains reverses.
- **GPT-5.6 Sol:** remains reverses.
- **Grok 4.6:** changes from indistinguishable from zero to survives.
- **Inkling:** remains reverses.
- **Muse Glimmer 30B:** remains reverses.
- **Perplexity Sonar Pro:** changes from reverses to indistinguishable from zero.

The earlier “seven of ten reverse” conclusion changes to **six of ten reverse**: Perplexity Sonar Pro becomes statistically indistinguishable from zero. Gemini and Grok change from indistinguishable to significantly positive; Opus remains significantly positive. Thus the qualitative L5-anomaly conclusion weakens but does not disappear.

## FBD L4 variants

| Model | Variant | Rows | Strict | Typed |
|---|---|---|---|---|
| Claude Opus 5 | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Claude Opus 5 | numeric only | 35 | 0.00% | 28.57% |
| Claude Sonnet 5 | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Claude Sonnet 5 | numeric only | 35 | 0.00% | 14.29% |
| DeepSeek V4.1 Flash | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| DeepSeek V4.1 Flash | numeric only | 35 | 0.00% | 11.43% |
| Gemini 3.8 Flash | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Gemini 3.8 Flash | numeric only | 35 | 0.00% | 17.14% |
| GPT-5.6 Luna | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| GPT-5.6 Luna | numeric only | 35 | 0.00% | 8.57% |
| GPT-5.6 Sol | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| GPT-5.6 Sol | numeric only | 35 | 0.00% | 8.57% |
| Grok 4.6 | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Grok 4.6 | numeric only | 35 | 0.00% | 8.57% |
| Inkling | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Inkling | numeric only | 35 | 0.00% | 11.43% |
| Muse Glimmer 30B | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Muse Glimmer 30B | numeric only | 35 | 0.00% | 8.57% |
| Perplexity Sonar Pro | numeric + wrong-arrow | 15 | 0.00% | 0.00% |
| Perplexity Sonar Pro | numeric only | 35 | 0.00% | 8.57% |

The numeric + wrong-arrow variant requires every requested arrow component. Its standalone table is [`fbd_l4_variants.csv`](fbd_l4_variants.csv).

## Test 2: grain

| Model | Sigma | Rows | Strict | Typed |
|---|---|---|---|---|
| Claude Opus 5 | 0 | 3400 | 62.35% | 66.76% |
| Claude Opus 5 | 15 | 3400 | 59.88% | 64.59% |
| Claude Opus 5 | 25 | 3400 | 58.56% | 63.12% |
| Claude Opus 5 | 40 | 3400 | 56.21% | 60.71% |
| Claude Sonnet 5 | 0 | 3400 | 49.71% | 54.47% |
| Claude Sonnet 5 | 15 | 3400 | 48.35% | 52.79% |
| Claude Sonnet 5 | 25 | 3400 | 47.62% | 52.06% |
| Claude Sonnet 5 | 40 | 3400 | 47.15% | 51.44% |
| DeepSeek V4.1 Flash | 0 | 3400 | 43.21% | 46.65% |
| DeepSeek V4.1 Flash | 15 | 3400 | 39.32% | 42.71% |
| DeepSeek V4.1 Flash | 25 | 3400 | 40.09% | 43.47% |
| DeepSeek V4.1 Flash | 40 | 3400 | 39.09% | 42.47% |
| Gemini 3.8 Flash | 0 | 3400 | 64.12% | 69.12% |
| Gemini 3.8 Flash | 15 | 3400 | 65.53% | 70.62% |
| Gemini 3.8 Flash | 25 | 3400 | 64.71% | 69.76% |
| Gemini 3.8 Flash | 40 | 3400 | 64.00% | 69.12% |
| GPT-5.6 Luna | 0 | 3400 | 42.41% | 45.65% |
| GPT-5.6 Luna | 15 | 3400 | 41.82% | 44.82% |
| GPT-5.6 Luna | 25 | 3400 | 42.00% | 45.12% |
| GPT-5.6 Luna | 40 | 3400 | 40.32% | 43.38% |
| GPT-5.6 Sol | 0 | 3400 | 50.82% | 54.82% |
| GPT-5.6 Sol | 15 | 3400 | 50.85% | 55.00% |
| GPT-5.6 Sol | 25 | 3400 | 51.03% | 55.03% |
| GPT-5.6 Sol | 40 | 3400 | 49.76% | 53.65% |
| Grok 4.6 | 0 | 3400 | 52.71% | 57.35% |
| Grok 4.6 | 15 | 3400 | 51.21% | 55.53% |
| Grok 4.6 | 25 | 3400 | 51.32% | 55.82% |
| Grok 4.6 | 40 | 3400 | 50.35% | 54.91% |
| Inkling | 0 | 3400 | 38.68% | 41.65% |
| Inkling | 15 | 3400 | 36.79% | 39.97% |
| Inkling | 25 | 3400 | 35.71% | 38.53% |
| Inkling | 40 | 3400 | 34.38% | 37.24% |
| Muse Glimmer 30B | 0 | 3400 | 44.35% | 48.26% |
| Muse Glimmer 30B | 15 | 3400 | 42.41% | 46.24% |
| Muse Glimmer 30B | 25 | 3400 | 43.56% | 47.35% |
| Muse Glimmer 30B | 40 | 3400 | 42.44% | 46.35% |
| Perplexity Sonar Pro | 0 | 3400 | 41.76% | 44.65% |
| Perplexity Sonar Pro | 15 | 3400 | 41.35% | 44.29% |
| Perplexity Sonar Pro | 25 | 3400 | 40.94% | 43.53% |
| Perplexity Sonar Pro | 40 | 3400 | 39.41% | 42.24% |

Typed scoring raises absolute levels where structured answers were previously string-mismatched. The main robustness pattern remains: changes across sigma are generally small relative to the model-to-model differences; this table does not recompute significance of each sigma contrast beyond the stored-score comparison.

## Test 3: sycophancy

| Model | R1 strict | R1 typed | R2 strict | R2 typed | Cap strict | Cap typed | Corr strict | Corr typed |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5 | 64.26% | 68.05% | 60.72% | 64.93% | 38.16% | 38.09% | 52.18% | 59.72% |
| Claude Sonnet 5 | 51.27% | 55.46% | 46.91% | 51.09% | 68.25% | 68.16% | 59.94% | 65.88% |
| DeepSeek V4.1 Flash | 48.93% | 52.10% | 49.07% | 52.70% | 63.09% | 63.09% | 59.78% | 65.07% |
| Gemini 3.8 Flash | 68.00% | 72.36% | 72.40% | 76.54% | 8.26% | 8.26% | 37.45% | 42.42% |
| GPT-5.6 Luna | 43.71% | 46.89% | 47.71% | 50.80% | 64.61% | 64.61% | 60.06% | 63.74% |
| GPT-5.6 Sol | 52.54% | 56.22% | 57.98% | 61.36% | 38.97% | 38.62% | 61.43% | 65.86% |
| Grok 4.6 | 54.25% | 58.16% | 58.92% | 62.91% | 13.05% | 12.88% | 31.31% | 34.50% |
| Inkling | 40.03% | 42.98% | 44.99% | 48.55% | 72.75% | 72.52% | 61.84% | 67.23% |
| Muse Glimmer 30B | 50.40% | 54.31% | 49.83% | 53.94% | 49.80% | 49.80% | 51.21% | 56.39% |
| Perplexity Sonar Pro | 43.04% | 45.68% | 49.35% | 52.38% | 50.32% | 50.11% | 54.57% | 58.49% |

Every overall/strength/level/domain rate, with strict and typed round-1/round-2 correctness side by side, is in [`test3_rates.csv`](test3_rates.csv); row-level verdicts are in `test3_row_scores.csv`. Correction rates move materially because previously unparseable structured correct answers can now score correct. Capitulation rates change little, so the core model-resistance ordering is largely unchanged.

## Audit boundaries

- Strict columns are never deleted.
- Typed constant-answer baselines are recomputed from semantic targets, including acceptance-set overlap handling inherited from the existing baseline code.
- Six constant-key cells remain excluded by the pre-existing adjusted-score convention; raw accuracy for all 170 cells is still reported.
- The typed comparator makes no dataset, generator, stored-response, or published-output change.
