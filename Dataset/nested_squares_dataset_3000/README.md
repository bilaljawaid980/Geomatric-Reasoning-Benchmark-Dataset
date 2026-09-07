# GRIP Nested Squares Dataset 3000 — v8

Version `nested-squares-8.0.0` contains 3,000 images and 15,000 questions. V8 occupies the unsuffixed release paths; superseded local builds were removed to keep the repository clean.

## Phase 8 changes

Level 5 now uses a 12% outermost-side threshold and a rescaled 9.6%–14.4% exclusion band. V7 medians (6.78% squares, 7.85% triangles, 6.92% hexagons) showed that lowering 5% would increase the already dominant `yes` class. Full guard-intersection calibration found 12% to be the lowest shared rounded threshold whose lower margin remains feasible for 10–12 triangles while retaining both visibility floors. The v8 result is exactly 1,500 `yes` / 1,500 `no`, with shape-count correlation `0.000000` and an achievable extrapolated-fraction range of 9.30%–16.99%.

The 15 px innermost-side guard and 3 px adjacent clear-background guard are unchanged. Clearance targets are sampled by paired nuisance rank and enforced for both Level 2 labels; minimum-clearance Cramér's V is `0.010438`. The definitional association whitelist contains exactly `factor_progression_direction` and `reduction_factor_span`; no nuisance feature reaches V=0.10.

All 3,000 PNG outline counts were independently recovered from disk. Every guard injection test passes, Level 4 retains its `0.194030` theoretical baseline and `0.194510` observed capture, and validation reports **PASS — 0 mismatches**. Full distributions and all 136 minimum-clearance rejections are recorded in `validation_report.txt`.

### Supplementary open-ended questions

Version `nested-squares-9.0.0` adds one parameterized free-response question per image without changing any image or existing five-level question or answer. The template starts from a visible label, coloured element, marked object, or named panel; scores multiple independently derived sub-facts; requires a visual justification; and ends with a confidence score from 0 to 1.

- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.
- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, and deterministic `targets`.
- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.
- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.

The composite acceptance-set preflight baseline is `0.003333`. Scored fields at or above 60% after template revision: `{}`. Targeted fields: `shape_count, outer_to_inner_size_ratio, clockwise_steps, counterclockwise_steps, largest_shrink_step`. Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.
