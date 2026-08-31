# GRIP Unified Five-Level Generation Template

Every future category must generate exactly five questions per image in this order:

1. **Simple Description** — one directly visible fact; the easiest question available.
2. **Basic Relational** — one comparison or one-step rule application.
3. **Comparative/Structural** — reasoning across multiple elements, ranking, an extreme, or cross-referencing image regions.
4. **Compound Reasoning** — combine at least two facts or apply a multi-step formula/rule chain; do not use hypothetical framing.
5. **Extrapolative/Counterfactual** — apply an explicitly defined hypothetical geometric change, extrapolate a pattern, or justify why a result changes. The operation and answer must be deterministic and independently recomputable from raw stored scene geometry.

## Required question schema

```json
{
  "question_id": "category_0001_q5",
  "question_text": "...",
  "question_type": "dataset_specific_operation",
  "ground_truth": "...",
  "answer_format": "...",
  "difficulty_level": 5
}
```

## Acceptance checklist

- Exactly five ordered levels `[1,2,3,4,5]` for every image.
- Level 5 uses the image's actual stored parameters, not a generic unverifiable “what if.”
- A separate validator re-derives every answer without reading it back as its source of truth.
- Ambiguous counterfactuals are rejected during generation.
- Metadata-only question regeneration must not modify PNG files.
- Flattened outputs contain exactly 15,000 rows for a 3,000-image category.
- `question_set.csv` excludes ground truth; `answer_key.csv` includes it.
- No inference, scoring, model API, or evaluation harness is part of generation.

## Mandatory distribution reporting

Every generation and validation report must automatically include:

- min, p25, p50, p75, p95, and max for every sampled continuous parameter;
- complete value counts for every sampled categorical parameter;
- target-label association checks for all stored scene parameters, with target-defining quantities explicitly distinguished from nuisance features;
- per-cause rejection counts and synthetic violating/boundary injection tests for every active guard.

Reporting only parameters changed in the current development pass is not sufficient. This full dump is a standing requirement for all future GRIP categories so degenerate samplers and fix-induced correlations are visible in the same build that introduces them.
