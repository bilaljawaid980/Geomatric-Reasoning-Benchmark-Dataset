# GRIP Nested Triangles Dataset 3000 — v8

Version `nested-triangles-8.0.0` contains 3,000 images and 15,000 questions. V8 occupies the unsuffixed release paths; superseded local builds were removed to keep the repository clean.

## Phase 8 changes

Level 5 now uses a 12% outermost-side threshold and a rescaled 9.6%–14.4% exclusion band. V7 medians motivated an upward move, and the triangle 10–12-outline guard intersection established 12% as the lowest shared rounded threshold compatible with both the unchanged 15 px innermost-side and 3 px clear-background floors. The result is exactly 1,500 `yes` / 1,500 `no`, count correlation `0.000000`, and an achievable extrapolated-fraction range of 4.03%–16.99%.

Changing scenes vary earlier reduction steps while matching their paired constant scene's total contraction and final extrapolation factor. Rotation targets retain the existing Level 4 multiset and sampling inversion, but are assigned by independently computed containment capacity so hard rotations remain valid. Clearance matching moves intermediate centers only, leaving both endpoint centers label-independent. Minimum-clearance Cramér's V is `0.015914`; the only V≥0.10 fields are the two approved definitional fields, `factor_progression_direction` and `reduction_factor_span`.

All 3,000 PNG outline counts were independently recovered. Every guard injection test passes, Level 4 retains its `0.191011` theoretical baseline and `0.191373` observed capture, and validation reports **PASS — 0 mismatches**. Full distributions and all 3,990 minimum-clearance rejections are recorded in `validation_report.txt`.

### Supplementary open-ended questions

Version `nested-triangles-10.0.0` rewrites the one parameterized free-response question per image without changing any image or existing five-level question or answer. Each plain-English prompt scores at most three visible sub-facts, does not name its own reasoning trap, requires a brief visual justification, and ends with a confidence score from 0 to 1.

- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.
- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.
- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.
- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.

The composite acceptance-set baseline is `0.028667`. Scored fields at or above 60% after template revision: `{}`. Targeted fields: `shape_count, cumulative_rotation_degrees_nearest_5, shrink_pattern`. Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.
