# Sentence-valued answer-key scoring audit

This is an offline, counterfactual analysis. No API was called, and no dataset, generator, stored response, scorer, or existing analysis output was changed. The proposed rule below has **not** been applied to the benchmark.

## Scope limitation

The repository currently contains complete Test-1 result files for **10 models**, not 16. Each has 50 evaluated `physical_stability` L5 responses. Consequently, the model tables below cover all **500 stored responses** available for this cell. Results for six additional models cannot be calculated without their missing stored Test-1 responses; no values are invented for them.

## 1. Structure of the 3,000 keys

The values are not free prose. They instantiate exactly two templates:

| Status | Count | Template |
|---|---:|---|
| `stable` | 1,500 | `stable; after removing block {TOP}, every cumulative center of mass remains within its supporting base` |
| `unstable` | 1,500 | `unstable; after removing block {TOP}, the cumulative center of mass at the joint between block {UPPER} and block {LOWER} lies outside its supporting base` |

There are only **9 distinct complete strings** across the 3,000 values. The slots contain block letters. For unstable cases, the checkable joint is an ordered upper/supporting-lower pair.

Ten verbatim examples:

1. `physical_stability_0001_q5`: `unstable; after removing block C, the cumulative center of mass at the joint between block B and block A lies outside its supporting base`
2. `physical_stability_0002_q5`: `stable; after removing block B, every cumulative center of mass remains within its supporting base`
3. `physical_stability_0004_q5`: `stable; after removing block C, every cumulative center of mass remains within its supporting base`
4. `physical_stability_0005_q5`: `unstable; after removing block E, the cumulative center of mass at the joint between block B and block A lies outside its supporting base`
5. `physical_stability_0007_q5`: `unstable; after removing block D, the cumulative center of mass at the joint between block C and block B lies outside its supporting base`
6. `physical_stability_0009_q5`: `unstable; after removing block D, the cumulative center of mass at the joint between block B and block A lies outside its supporting base`
7. `physical_stability_0012_q5`: `stable; after removing block E, every cumulative center of mass remains within its supporting base`
8. `physical_stability_0016_q5`: `stable; after removing block D, every cumulative center of mass remains within its supporting base`
9. `physical_stability_0019_q5`: `unstable; after removing block E, the cumulative center of mass at the joint between block D and block C lies outside its supporting base`
10. `physical_stability_3000_q5`: `stable; after removing block C, every cumulative center of mass remains within its supporting base`

## 2. Proposed scoring rule—not applied

The following deterministic rule extracts only the content explicitly requested by the question and represented in the key.

1. Extract the existing single `ANSWER:` line. Strip surrounding whitespace and leading Markdown emphasis characters.
2. Require the first answer token to be exactly `stable` or `unstable`, case-insensitively. Reject a missing, hedged, or ambiguous status.
3. If the key is stable, accept exactly when the extracted status is `stable`. Explanatory wording after that token is ignored because there is no failing joint to identify.
4. If the key is unstable, require both:
   - extracted status `unstable`; and
   - one unambiguous ordered failing-joint pair equal to `(UPPER, LOWER)` in the key.
5. Extract the pair from either an explicit construction such as “joint between D and C”/“D-C interface”, or a relational construction that names an upper block or upper group’s centre of mass relative to a named supporting lower block. For an upper group such as `B+C`, the first/lowest upper member is the upper side of the joint.
6. Reject reversed or incorrect pairs, missing pairs, multiple conflicting pairs, a statement only about the whole stack relative to the ground, and explanations that name blocks without identifying their support relationship.

Examples of what the rule would accept:

- `Stable — every remaining centre of mass is supported.` for a stable key.
- `Unstable — block D's COM lies beyond supporting block C.` for target `(D,C)`.
- `unstable (B+C CoM not over A)` for target `(B,A)`.

Examples of what it would reject:

- `unstable` alone for any unstable key: the failing joint is missing.
- `unstable (C-B joint)` for target `(B,C)`: order is reversed.
- `unstable (D's COM not over B)` for target `(D,C)`: the lower block is wrong.
- `unstable; the whole A-D stack is outside A's ground footprint`: this describes global ground support rather than the keyed inter-block joint.
- `probably stable` or `stable or unstable`: the required leading, unambiguous status is absent.

The evaluated 50-item sample contains 26 stable keys and 24 unstable keys. Under this proposed comparator, the strongest constant answer is `stable`, so the physical-stability L5 constant-answer baseline becomes **26/50 = 52.00%**. Aggregate adjusted scores below use that counterfactual baseline.

### Application to 20 real stored responses

These are two deterministic examples per available model: the first sampled stable-key item and the first sampled unstable-key item. Responses are reproduced verbatim.

1. **Claude Opus 5 — `physical_stability_0136_q5` — target `stable` — ACCEPT**
   - `ANSWER: Stable — without E, the combined center of mass of B, C and D (≈x=288) falls within A's support, and each block's COM lies over the one below, so no tipping occurs.`
   - Extracted: `(stable, no joint required)`.
2. **Claude Opus 5 — `physical_stability_0015_q5` — target `unstable, (B,A)` — ACCEPT**
   - `ANSWER: Unstable — with C gone, block B's center of mass (x≈369) lies beyond the right edge of block A's top surface (x≈359), so B would tip off.`
   - Extracted: `(unstable, (B,A))`.
3. **Claude Sonnet 5 — `physical_stability_0136_q5` — target `stable` — ACCEPT**
   - `ANSWER: Stable — with E removed, each remaining block's center of mass still lies above the support of the block below it, keeping the overall center of mass within the base.`
   - Extracted: `(stable, no joint required)`.
4. **Claude Sonnet 5 — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
   - `ANSWER: Stable, because block B's center of mass remains above block A's base of support.`
   - Extracted: `(stable, no joint)`; status is wrong.
5. **DeepSeek V4.1 Flash — `physical_stability_0136_q5` — target `stable` — ACCEPT**
   - `ANSWER: Stable, because the combined center of mass of blocks A-D remains over the base.`
   - Extracted: `(stable, no joint required)`.
6. **DeepSeek V4.1 Flash — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
   - `ANSWER: Stable, because the combined center of mass of blocks A and B remains directly above the base of support (block A).`
   - Extracted: `(stable, no joint)`; status is wrong.
7. **Gemini 3.8 Flash — `physical_stability_0136_q5` — target `stable` — ACCEPT**
   - `ANSWER: Stable, because the center of mass of every upper group of blocks (D; C+D; and B+C+D) lies directly within the supporting base of the block immediately beneath it.`
   - Extracted: `(stable, no joint required)`.
8. **Gemini 3.8 Flash — `physical_stability_0015_q5` — target `unstable, (B,A)` — ACCEPT**
   - `ANSWER: Unstable, because the center of mass of block B lies to the right of the supporting edge of block A, causing it to tip over.`
   - Extracted: `(unstable, (B,A))`.
9. **GPT-5.6 Luna — `physical_stability_0136_q5` — target `stable` — ACCEPT**
   - `ANSWER: Stable — the combined center of mass of blocks A–D remains over the supporting base.`
   - Extracted: `(stable, no joint required)`.
10. **GPT-5.6 Luna — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
    - `ANSWER: Stable — the combined center of mass of blocks A and B remains over block A’s support area.`
    - Extracted: `(stable, no joint)`; status is wrong.
11. **GPT-5.6 Sol — `physical_stability_0136_q5` — target `stable` — ACCEPT**
    - `ANSWER: Stable — the combined center of mass of blocks B–D remains over block A’s support base.`
    - Extracted: `(stable, no joint required)`.
12. **GPT-5.6 Sol — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
    - `ANSWER: Stable — block B’s center of mass lies over the support area of block A.`
    - Extracted: `(stable, no joint)`; status is wrong.
13. **Grok 4.6 — `physical_stability_0136_q5` — target `stable` — REJECT**
    - `ANSWER: unstable (CM of A–D not over A's base)`
    - Extracted: `(unstable, no keyed inter-block joint)`; status is wrong.
14. **Grok 4.6 — `physical_stability_0015_q5` — target `unstable, (B,A)` — ACCEPT**
    - `ANSWER: unstable (B's CoM not over A)`
    - Extracted: `(unstable, (B,A))`.
15. **Inkling — `physical_stability_0136_q5` — target `stable` — REJECT**
    - `ANSWER: Unstable, because removing E shifts the combined center of mass right of block A's left edge/support base.`
    - Extracted: `(unstable, no keyed inter-block joint)`; status is wrong.
16. **Inkling — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
    - `ANSWER: stable, because the combined center of mass of A and B remains within block A's base on the ground`
    - Extracted: `(stable, no joint)`; status is wrong.
17. **Muse Glimmer 30B — `physical_stability_0136_q5` — target `stable` — ACCEPT**
    - `ANSWER: stable, the combined center of mass of blocks A–D remains vertically above the supporting base of block A, so the overall weight acts within the base of support.`
    - Extracted: `(stable, no joint required)`.
18. **Muse Glimmer 30B — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
    - `ANSWER: unstable, the combined center of mass of blocks A and B lies to the right of the supporting base of A, i.e. outside A’s footprint on the ground, so the stack would tip.`
    - Extracted: `(unstable, no keyed inter-block joint)`; it describes whole-stack ground support.
19. **Perplexity Sonar Pro — `physical_stability_0136_q5` — target `stable` — ACCEPT**
    - `ANSWER: Stable; without E, the combined center of mass of blocks A–D still lies above the base of block A, so the stack does not tip.`
    - Extracted: `(stable, no joint required)`.
20. **Perplexity Sonar Pro — `physical_stability_0015_q5` — target `unstable, (B,A)` — REJECT**
    - `ANSWER: Stable; with C removed, block B’s center of mass lies above the part of B that is supported by A, so the combined center of mass of A and B stays over A’s base.`
    - Extracted: `(stable, no joint)`; status is wrong.

## 3. Counterfactual physical-stability L5 accuracy

| Model | N | Current strict | Proposed structured |
|---|---:|---:|---:|
| Claude Opus 5 | 50 | 0.00% | **100.00%** |
| Claude Sonnet 5 | 50 | 0.00% | **52.00%** |
| DeepSeek V4.1 Flash | 50 | 0.00% | **52.00%** |
| Gemini 3.8 Flash | 50 | 0.00% | **100.00%** |
| GPT-5.6 Luna | 50 | 0.00% | **52.00%** |
| GPT-5.6 Sol | 50 | 0.00% | **60.00%** |
| Grok 4.6 | 50 | 0.00% | **82.00%** |
| Inkling | 50 | 0.00% | **50.00%** |
| Muse Glimmer 30B | 50 | 0.00% | **58.00%** |
| Perplexity Sonar Pro | 50 | 0.00% | **52.00%** |

## 4. Effect on aggregates

“Raw L5” is the mean raw accuracy across all 34 domain/L5 cells. “Adjusted L5” is the existing paired-domain macro mean used by the L4-to-L5 analysis. “L5−L4” and its verdict use the same 10,000-resample, domain-stratified image-cluster bootstrap as the current analysis. “Overall macro” is the Test-1 baseline-adjusted macro score. Only the proposed physical-stability L5 cell and its empirical baseline are changed in the after calculation.

| Model | Raw L5 before | Raw L5 after | Adjusted L5 before | Adjusted L5 after | Adjusted L5−L4 before | Verdict before | Adjusted L5−L4 after | 95% CI after | Verdict after | Overall macro before | Overall macro after |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|
| Claude Opus 5 | 55.18% | 58.12% | 21.81% | 25.65% | +6.90 pp | survives | +10.74 pp | +6.26 to +15.14 pp | survives | 41.98% | 42.71% |
| Claude Sonnet 5 | 38.35% | 39.88% | -9.57% | -8.96% | -10.47 pp | reverses | -9.85 pp | -15.21 to -4.53 pp | reverses | 23.65% | 23.77% |
| DeepSeek V4.1 Flash | 34.82% | 36.35% | -30.63% | -30.02% | -22.90 pp | reverses | -22.28 pp | -27.86 to -16.66 pp | reverses | 6.18% | 6.30% |
| Gemini 3.8 Flash | 55.00% | 57.94% | 21.86% | 25.70% | -0.19 pp | indistinguishable from zero | +3.65 pp | -1.08 to +8.31 pp | indistinguishable from zero | 44.82% | 45.54% |
| GPT-5.6 Luna | 34.00% | 35.53% | -26.41% | -25.79% | -18.98 pp | reverses | -18.37 pp | -24.20 to -12.43 pp | reverses | 6.96% | 7.07% |
| GPT-5.6 Sol | 40.47% | 42.24% | -9.71% | -8.56% | -12.74 pp | reverses | -11.58 pp | -17.16 to -6.42 pp | reverses | 22.91% | 23.13% |
| Grok 4.6 | 46.35% | 48.76% | 3.51% | 6.14% | -4.57 pp | indistinguishable from zero | -1.94 pp | -6.55 to +2.77 pp | indistinguishable from zero | 28.01% | 28.50% |
| Inkling | 32.12% | 33.59% | -36.60% | -36.12% | -28.65 pp | reverses | -28.17 pp | -33.90 to -22.47 pp | reverses | 1.94% | 2.03% |
| Muse Glimmer 30B | 33.47% | 35.18% | -34.06% | -33.04% | -29.12 pp | reverses | -28.10 pp | -33.47 to -22.86 pp | reverses | 8.44% | 8.64% |
| Perplexity Sonar Pro | 31.35% | 32.88% | -29.59% | -28.98% | -15.99 pp | reverses | -15.37 pp | -21.08 to -9.89 pp | reverses | 4.15% | 4.26% |

No L4-to-L5 significance verdict changes under this proposal, although every L5 raw mean rises and the size of several adjusted differences changes.

## 5. Other sentence-valued or multi-clause keys

For this diagnostic, a ground-truth value is flagged when it is not a JSON/list container and either contains a semicolon or contains at least six alphanumeric word tokens. “Items” counts flagged values in the full domain answer key. “Evaluated responses” is the corresponding number of stored Test-1 model responses whose keys were flagged. Accuracy is the current unmodified strict score on only those flagged responses, pooled across the 10 available models.

| Domain | Level | Flagged corpus items | Total corpus items at level | Evaluated responses | Current strict correct | Current strict accuracy |
|---|---:|---:|---:|---:|---:|---:|
| `compass_bearing` | L5 | 3,000 | 3,000 | 500 | 0 | **0.00%** |
| `fbd` | L5 | 2,500 | 3,000 | 420 | 0 | **0.00%** |
| `gauge_reading` | L4 | 374 | 3,000 | 50 | 0 | **0.00%** |
| `gauge_reading` | L5 | 3,000 | 3,000 | 500 | 0 | **0.00%** |
| `gear_train` | L5 | 3,000 | 3,000 | 500 | 82 | 16.40% |
| `laser_mirror` | L5 | 3,000 | 3,000 | 500 | 0 | **0.00%** |
| `optical_illusion` | L5 | 3,000 | 3,000 | 500 | 0 | **0.00%** |
| `projectile_motion` | L5 | 300 | 1,000 | 80 | 0 | **0.00%** |
| `surface_topology` | L4 | 3,000 | 3,000 | 500 | 317 | 63.40% |

The zero-scoring cells are strong candidates for separate structured-key audits, but this table does not establish that their current scoring is wrong. Some may intentionally require every component, and each requires a domain-specific acceptance rule before any score is changed. No such rule or score change is applied here.
