# Audit of the seven remaining sentence-valued scoring cells

This is an offline, counterfactual audit. No API was called and no model was re-run. The dataset, generators, stored responses, scoring code, and existing analysis outputs were not changed. Every rule and score below is a proposal only.

## Scope and method

The audit covers `compass_bearing` L5, `fbd` L5, `gauge_reading` L5, `gauge_reading` L4, `laser_mirror` L5, `optical_illusion` L5, and `projectile_motion` L5. Structure counts use every corpus item. Accuracy and baselines use the 50 Test-1 items per model in each cell (500 responses per cell across ten complete models).

The phrase “zero-scoring cell” originated in the earlier sentence-key screen. Three listed cells are mixed: one branch already has short keys and therefore does not score zero overall. The defect is in their templated branch.

| Cell | Complete key strings | Structure | Diagnosis |
|---|---:|---|---|
| `compass_bearing` L5 | 2,992 | one numeric sentence template | (a), comparator defect |
| `fbd` L5 | 191 | short yes/no plus direction templates | (a), mixed-cell comparator defect |
| `gauge_reading` L5 | 69 | one two-component template | (a), comparator defect |
| `gauge_reading` L4 | 12 | two short forms plus one numeric template | (a), mixed-cell comparator defect |
| `laser_mirror` L5 | 60 | one three-component template | (a), comparator defect |
| `optical_illusion` L5 | 5 | two semantic templates | (a), comparator defect |
| `projectile_motion` L5 | 199 | short range branch plus obstacle template | (a), mixed-cell comparator defect |

None is case (b). Every cell contains at least one stored response that gives the requested content correctly but fails literal comparison against its sentence-valued key.

## 1. `compass_bearing` L5

### Structure

All 3,000 keys instantiate one template:

`{LETTER}; projected endpoint is closest to {LETTER} ({DISTANCE} map units away; bearing difference {BEARING_DIFFERENCE} degrees)`

The repeated `LETTER` is the selected landmark. There are 2,992 distinct complete strings. This is templated, not free prose.

Ten verbatim keys:

1. `compass_bearing_0001_q5`: `D; projected endpoint is closest to D (105.5 map units away; bearing difference 29.7 degrees)`
2. `compass_bearing_0002_q5`: `B; projected endpoint is closest to B (299.7 map units away; bearing difference 119.8 degrees)`
3. `compass_bearing_0003_q5`: `A; projected endpoint is closest to A (57.7 map units away; bearing difference 3.7 degrees)`
4. `compass_bearing_0004_q5`: `B; projected endpoint is closest to B (135.4 map units away; bearing difference 30.0 degrees)`
5. `compass_bearing_0005_q5`: `A; projected endpoint is closest to A (128.5 map units away; bearing difference 29.5 degrees)`
6. `compass_bearing_0600_q5`: `C; projected endpoint is closest to C (478.2 map units away; bearing difference 105.3 degrees)`
7. `compass_bearing_1200_q5`: `C; projected endpoint is closest to C (40.9 map units away; bearing difference 30.0 degrees)`
8. `compass_bearing_1800_q5`: `A; projected endpoint is closest to A (285.8 map units away; bearing difference 60.1 degrees)`
9. `compass_bearing_2400_q5`: `C; projected endpoint is closest to C (95.0 map units away; bearing difference 60.0 degrees)`
10. `compass_bearing_3000_q5`: `A; projected endpoint is closest to A (154.2 map units away; bearing difference 46.9 degrees)`

### Diagnosis and proposed rule

Case (a). The question asks for the correct offered landmark and a brief justification using endpoint distance and bearing difference; it does not request the key’s exact decimals or exact prose.

Proposed rule:

1. Require the answer to begin with one of the offered landmark letters and require it to equal the keyed letter.
2. Require endpoint-distance evidence: `distance`/`dist`, `away`, `closer`/`closest`, `farther`/`farthest`, `nearest`, pixels, or map units.
3. Require bearing-comparison evidence: `bearing` together with `difference`, `offset`, closeness/alignment, larger, or smaller; or an explicit angular difference/offset.
4. Exact explanatory numbers are optional because the prompt asks only for a brief justification.
5. Reject a wrong or missing letter, a letter alone, or an explanation missing either distance or bearing comparison.

Ten stored response/key comparisons (A = proposed accept, R = proposed reject):

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Opus, `0103` | `B; ... 63.2 ... 29.7 ...` | `ANSWER: B — the projected endpoint (~417, 384) lies only ~64 px from B (bearing difference just ~30° from the A→B bearing of ~094°), whereas C and D are 200+ px away in the opposite direction.` |
| A | Sonnet, `0742` | `A; ... 73.0 ... 2.9 ...` | `ANSWER: A, because the projected endpoint (~286,189) is about 72 units from A vs ~124 units from C, and the bearing (321°) is much closer to B→A's direction than to B→C's (291°).` |
| A | DeepSeek, `2850` | `B; ... 280.3 ... 59.7 ...` | `ANSWER: B, because the 249° bearing from A points northwest toward B's vicinity, and the endpoint lands closer to B than to C on the map.` |
| A | Gemini, `0009` | `B; ... 76.7 ... 10.1 ...` | `ANSWER: B. A bearing of 330° corresponds to 30° west of north, closely aligning with landmark B (bearing ~320°, difference of only ~10° from A). Traveling the distance of A-to-C in this direction projects an endpoint northwest of A, which is much closer to B than to C or D.` |
| A | Sol, `0137` | `B; ... 86.5 ... 38.7 ...` | `ANSWER: B — the projected endpoint is nearest B; A→B is about the same distance as A→D and its bearing is closest to 355°.` |
| R | Opus, `0009` | `B; ... 76.7 ... 10.1 ...` | `ANSWER: B — The endpoint (~78, 98) lies about 76 px from B, far closer than C (~203 px) or D (~300 px); A→C's bearing is ~030°, so the 330° bearing swings the same distance to the northwest, near B.` |
| R | Sonnet, `0009` | same key | `ANSWER: B` |
| R | DeepSeek, `0009` | same key | `ANSWER: B` |
| R | Gemini, `0052` | `B; ... 141.6 ... 28.6 ...` | `None` |
| R | Luna, `0009` | same key | `ANSWER: B` |

The first rejected Opus response identifies the correct letter and distance, but does not actually state a bearing *difference/comparison*; mentioning two raw bearings is not treated as fulfilling that requested component.

Baseline on the 50-item Test-1 sample: **2.00% literal → 34.00% semantic** (modal letter `B`, 17/50).

| Model | Current strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 0.00% | 40.00% |
| Claude Sonnet 5 | 0.00% | 4.00% |
| DeepSeek V4.1 Flash | 0.00% | 2.00% |
| Gemini 3.8 Flash | 0.00% | 56.00% |
| GPT-5.6 Luna | 0.00% | 0.00% |
| GPT-5.6 Sol | 0.00% | 30.00% |
| Grok 4.6 | 0.00% | 14.00% |
| Inkling | 0.00% | 48.00% |
| Muse Glimmer 30B | 0.00% | 0.00% |
| Perplexity Sonar Pro | 0.00% | 42.00% |

## 2. `fbd` L5

### Structure

There are 191 distinct strings and two semantic branches:

- 500 keys: `{YES_NO}`.
- 2,500 keys: `{DIRECTION_LABEL} ({ANGLE} degrees; 0=right, 90=up)`, comprising 1,500 `downward (270...)`, 375 `right (0...)`, and 625 general `direction ({ANGLE}...)` keys.

This is templated, not free prose.

Ten verbatim keys:

1. `fbd_0001_q5`: `no`
2. `fbd_0002_q5`: `downward (270 degrees; 0=right, 90=up)`
3. `fbd_0003_q5`: `downward (270 degrees; 0=right, 90=up)`
4. `fbd_0004_q5`: `right (0 degrees; 0=right, 90=up)`
5. `fbd_0005_q5`: `downward (270 degrees; 0=right, 90=up)`
6. `fbd_0600_q5`: `direction (249 degrees; 0=right, 90=up)`
7. `fbd_1200_q5`: `direction (245 degrees; 0=right, 90=up)`
8. `fbd_1800_q5`: `direction (254 degrees; 0=right, 90=up)`
9. `fbd_2400_q5`: `direction (247 degrees; 0=right, 90=up)`
10. `fbd_3000_q5`: `direction (250 degrees; 0=right, 90=up)`

### Diagnosis and proposed rule

Case (a), mixed. The yes/no branch already works. The direction branch fails because an exact requested angle such as `0` cannot equal the sentence `right (0 degrees; 0=right, 90=up)`.

Proposed rule:

- Slip question: require exact leading `yes` or `no`.
- Direction question: extract the first answer number, normalize modulo 360, and require exact equality to the keyed angle. Thus `-15.2°` equals `344.8°`.
- A direction word is optional because the question asks for the angle; a direction word without the requested number is rejected. No angular tolerance is introduced.

Ten real comparisons:

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Sonnet, `0100` | `right (0 degrees; 0=right, 90=up)` | `ANSWER: 0` |
| A | Grok, `0334` | `right (0 degrees; 0=right, 90=up)` | `ANSWER: 0` |
| A | Inkling, `0100` | same | `ANSWER: 0` |
| A | Muse, `0100` | same | `ANSWER: 0` |
| A | Sonar, `0334` | same | `ANSWER: 0°` |
| R | Muse, `0414` | `direction (249 degrees; 0=right, 90=up)` | `None` |
| R | Sonnet, `0826` | `direction (344.8 degrees; 0=right, 90=up)` | `ANSWER: 0` |
| R | Inkling, `0573` | `downward (270 degrees; 0=right, 90=up)` | `ANSWER: 0` |
| R | Sonar, `0609` | same | `ANSWER: 90` |
| R | Gemini, `1500` | `direction (251.8 degrees; 0=right, 90=up)` | `ANSWER: 254°` |

Additional substantive-match check: Opus answered `ANSWER: -15.2 degrees` against `direction (344.8 degrees; 0=right, 90=up)`; modulo 360 this is accepted.

Baseline: **40.00% → 40.00%** (modal semantic answer: 270°, 20/50).

| Model | Current strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 16.00% | 96.00% |
| Claude Sonnet 5 | 16.00% | 82.00% |
| DeepSeek V4.1 Flash | 8.00% | 46.00% |
| Gemini 3.8 Flash | 16.00% | 86.00% |
| GPT-5.6 Luna | 12.00% | 64.00% |
| GPT-5.6 Sol | 12.00% | 74.00% |
| Grok 4.6 | 16.00% | 94.00% |
| Inkling | 12.00% | 38.00% |
| Muse Glimmer 30B | 12.00% | 76.00% |
| Perplexity Sonar Pro | 12.00% | 62.00% |

## 3. `gauge_reading` L5

### Structure

All 3,000 keys use `{YES_NO}; new value {VALUE}`. There are 69 complete strings. This is templated.

Ten verbatim keys: `no; new value 180`, `no; new value 30`, `no; new value 55`, `no; new value 35`, `yes; new value 10.5`, `no; new value 5`, `no; new value 5`, `no; new value 5.5`, `no; new value 3.5`, and `no; new value 4` (items `0001`, `0002`, `0003`, `0004`, `0005`, `0600`, `1200`, `1800`, `2400`, and `3000`).

### Diagnosis and proposed rule

Case (a). Require both explicitly requested components: leading yes/no and the exact numeric new value. Units, commas, and explanatory prose are ignored. Reject a missing component, wrong status, or any numeric difference; no tolerance is added.

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Grok, `1105` | `no; new value 8` | `ANSWER: no, 8` |
| A | Opus, `0582` | `no; new value 45` | `ANSWER: No, 45` |
| A | Sonnet, `0058` | `no; new value 40` | `ANSWER: No, 40` |
| A | DeepSeek, `0046` | `no; new value 70` | `ANSWER: No, 70` |
| A | Gemini, `0058` | `no; new value 40` | `ANSWER: No, 40` |
| R | DeepSeek, `1022` | `no; new value 40` | `Yes, 45` |
| R | Opus, `0058` | `no; new value 40` | `ANSWER: no, 41` |
| R | Sonnet, `0162` | `no; new value 30` | `ANSWER: No, 40` |
| R | Gemini, `0278` | `no; new value 27.5` | `ANSWER: No, 30` |
| R | Sol, `0063` | `yes; new value 65` | `ANSWER: No, 65` |

Baseline: **6.00% → 6.00%** (modal semantic pair `no, 85`, 3/50).

| Model | Strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 0.00% | 38.00% |
| Claude Sonnet 5 | 0.00% | 28.00% |
| DeepSeek V4.1 Flash | 0.00% | 22.00% |
| Gemini 3.8 Flash | 0.00% | 82.00% |
| GPT-5.6 Luna | 0.00% | 12.00% |
| GPT-5.6 Sol | 0.00% | 54.00% |
| Grok 4.6 | 0.00% | 80.00% |
| Inkling | 0.00% | 8.00% |
| Muse Glimmer 30B | 0.00% | 86.00% |
| Perplexity Sonar Pro | 0.00% | 26.00% |

## 4. `gauge_reading` L4

### Structure

There are 12 strings: `no danger zone marked` (1,800 items), `no` (826), and `yes; exceeds threshold by {AMOUNT}` (374, ten observed amounts). This is templated.

Ten verbatim keys: `no`, `no danger zone marked`, `no danger zone marked`, `no danger zone marked`, `yes; exceeds threshold by 1`, `no`, `no`, `no`, `no`, and `no` (items `0001`, `0002`, `0003`, `0004`, `0005`, `0600`, `1200`, `1800`, `2400`, `3000`).

### Diagnosis and proposed rule

Case (a), mixed. The question asks whether the needle is in a danger zone “if one is marked,” and asks the exceedance only if yes.

Proposed rule:

- Collapse `no` and `no danger zone marked` to the semantic status `no`; either a leading `no` or an explicit no-danger-zone statement is accepted.
- For a yes key, require leading `yes` plus the exact exceedance amount expressed with `by` or as an amount `above` the threshold.
- Reject yes without an amount, a wrong status, or a non-equal amount. No tolerance.

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | DeepSeek, `0636` | `no` | `No` |
| A | Inkling, `0046` | `no` | `No` |
| A | Opus, `0046` | `no` | `ANSWER: No` |
| A | Gemini, `0046` | `no` | `ANSWER: No` |
| A | Sol, `0046` | `no` | `ANSWER: No` |
| R | Inkling, `0071` | `yes; exceeds threshold by 30` | `No` |
| R | Gemini, `1595` | `yes; exceeds threshold by 0.5` | `None` |
| R | Luna, `0611` | `yes; exceeds threshold by 30` | `ANSWER: No` |
| R | Sol, `0611` | same | `ANSWER: No.` |
| R | Grok, `1595` | `yes; exceeds threshold by 0.5` | `ANSWER: Yes, ~0.3 bar over 7` |

An additional real accepted paraphrase is `ANSWER: Yes, about 170 km/h — roughly 30 km/h above the 140 km/h threshold` for a keyed exceedance of 30.

Baseline: **68.00% → 90.00%** (semantic `no`, 45/50).

| Model | Strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 14.00% | 96.00% |
| Claude Sonnet 5 | 2.00% | 94.00% |
| DeepSeek V4.1 Flash | 4.00% | 92.00% |
| Gemini 3.8 Flash | 22.00% | 96.00% |
| GPT-5.6 Luna | 0.00% | 92.00% |
| GPT-5.6 Sol | 22.00% | 96.00% |
| Grok 4.6 | 64.00% | 98.00% |
| Inkling | 22.00% | 86.00% |
| Muse Glimmer 30B | 14.00% | 100.00% |
| Perplexity Sonar Pro | 0.00% | 94.00% |

## 5. `laser_mirror` L5

### Structure

All 3,000 keys use `{YES_NO}; exits at {EDGE}, position {POSITION}`. There are 60 complete strings. This is templated.

Ten verbatim keys: `yes; exits at right, position 5`, `yes; exits at right, position 2`, `yes; exits at left, position 4`, `no; exits at left, position 3`, `yes; exits at right, position 4`, `no; exits at left, position 8`, `no; exits at right, position 8`, `no; exits at bottom, position 6`, `no; exits at bottom, position 5`, and `no; exits at bottom, position 7` (items `0001`, `0002`, `0003`, `0004`, `0005`, `0600`, `1200`, `1800`, `2400`, `3000`).

### Diagnosis and proposed rule

Case (a). The prompt asks whether the exit changes and asks where only “if so.”

Proposed rule:

- Always require exact leading yes/no.
- For `yes`, require both the correct edge and position. Accept `top/bottom column N`, `left/right row N`, or explicit `position N`.
- For `no`, do not require a location. If a response volunteers an edge/position, it must agree with the key.
- Reject a yes response missing either location component, any wrong status, edge, or position, and conflicting locations.

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Opus, `0428` | `no; exits at right, position 7` | `ANSWER: No` |
| A | Sonnet, `2216` | `no; exits at right, position 2` | `ANSWER: No` |
| A | Gemini, `0428` | `no; exits at right, position 7` | `ANSWER: No` |
| A | Grok, `0428` | same | `ANSWER: No` |
| A | Inkling, `0428` | same | `ANSWER: No` |
| R | Sonnet, `0691` | `yes; exits at bottom, position 4` | `None` |
| R | Gemini, `1774` | `yes; exits at bottom, position 5` | `None` |
| R | Muse, `0071` | `yes; exits at top, position 3` | `None` |
| R | Inkling, `0091` | `yes; exits at right, position 5` | `ANSWER: No` |
| R | Grok, `0347` | `yes; exits at bottom, position 2` | `ANSWER: yes, south of C2` |

Additional real yes-branch accepts include `ANSWER: Yes — it would exit at the top of column 3`, `ANSWER: Yes, top of column 3`, and `ANSWER: Yes; it would exit at the top edge at column 7.`

Baseline: **8.00% → 22.00%** (semantic `no`, 11/50).

| Model | Strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 0.00% | 100.00% |
| Claude Sonnet 5 | 0.00% | 60.00% |
| DeepSeek V4.1 Flash | 0.00% | 4.00% |
| Gemini 3.8 Flash | 0.00% | 86.00% |
| GPT-5.6 Luna | 0.00% | 4.00% |
| GPT-5.6 Sol | 0.00% | 14.00% |
| Grok 4.6 | 0.00% | 68.00% |
| Inkling | 0.00% | 8.00% |
| Muse Glimmer 30B | 0.00% | 0.00% |
| Perplexity Sonar Pro | 0.00% | 4.00% |

## 6. `optical_illusion` L5

### Structure

There are five complete strings across 3,000 items, produced by two templates: `yes; actually equal` and `{YES_NO}; element {LETTER} is actually bigger`. This is templated.

Ten verbatim keys: `yes; actually equal`, `yes; actually equal`, `yes; actually equal`, `no; element B is actually bigger`, `no; element B is actually bigger`, `no; element B is actually bigger`, `yes; element A is actually bigger`, `no; element A is actually bigger`, `yes; element B is actually bigger`, and `no; element A is actually bigger` (items `0001`, `0002`, `0003`, `0004`, `0005`, `0600`, `1200`, `1800`, `2400`, `3000`).

### Diagnosis and proposed rule

Case (a). Require both components requested by the question: leading yes/no and the actual relation (`equal`, `A bigger`, or `B bigger`). Accept `same size/length`, `larger`, and `longer` as unambiguous synonyms. Reject a bare yes/no, a bare letter, wrong relation, or missing component.

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Muse, `1154` | `yes; element B is actually bigger` | `ANSWER: yes, B is bigger` |
| A | Grok, `1402` | `yes; actually equal` | `ANSWER: yes, they are equal` |
| A | Inkling, `0133` | `yes; actually equal` | `ANSWER: Yes, they are equal` |
| A | Opus, `0084` | `no; element B is actually bigger` | `ANSWER: No, B is actually bigger` |
| A | Gemini, `2313` | same | `ANSWER: No, B is actually bigger` |
| R | Muse, `0133` | `yes; actually equal` | `None` |
| R | DeepSeek, `0133` | same | `ANSWER: No, A` |
| R | Inkling, `0592` | `no; element B is actually bigger` | `ANSWER: No, B` |
| R | Luna, `0712` | `no; element B is actually bigger` | `ANSWER: No, A is bigger.` |
| R | Grok, `2010` | `yes; element A is actually bigger` | `ANSWER: yes, they are equal` |

Baseline: **52.00% → 52.00%** (semantic `yes + equal`, 26/50).

| Model | Strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 0.00% | 50.00% |
| Claude Sonnet 5 | 0.00% | 24.00% |
| DeepSeek V4.1 Flash | 0.00% | 0.00% |
| Gemini 3.8 Flash | 0.00% | 54.00% |
| GPT-5.6 Luna | 0.00% | 8.00% |
| GPT-5.6 Sol | 0.00% | 48.00% |
| Grok 4.6 | 0.00% | 50.00% |
| Inkling | 0.00% | 14.00% |
| Muse Glimmer 30B | 0.00% | 44.00% |
| Perplexity Sonar Pro | 0.00% | 12.00% |

## 7. `projectile_motion` L5

### Structure

There are 199 strings and two branches: `{RANGE_CHANGE}` for 700 items (688 `increase`, 12 `stay the same`) and `{HITS_CLEARS}; {AT_BY} {METERS} m` for 300 obstacle items. This is templated, not free prose.

Ten verbatim keys:

1. `projectile_motion_0001_q5`: `hits; at 11.2 m`
2. `projectile_motion_0002_q5`: `clears; by 8.9 m`
3. `projectile_motion_0003_q5`: `increase`
4. `projectile_motion_0004_q5`: `increase`
5. `projectile_motion_0005_q5`: `increase`
6. `projectile_motion_0200_q5`: `clears; by 9.7 m`
7. `projectile_motion_0400_q5`: `clears; by 9.0 m`
8. `projectile_motion_0600_q5`: `clears; by 17.4 m`
9. `projectile_motion_0800_q5`: `clears; by 21.3 m`
10. `projectile_motion_1000_q5`: `clears; by 8.9 m`

### Diagnosis and proposed rule

Case (a), mixed. The short range-change branch already scores. The obstacle branch fails on ordinary phrasings such as `Hits at 45.7 m`.

Proposed rule:

- Range branch: require exact `increase`, `decrease`, or `stay the same` after normalization.
- Obstacle branch: require both exact `hits`/`clears` and the exact requested numeric height or clearance. Units and prose are optional; no numeric tolerance.
- Reject missing components, wrong outcome, or any numeric difference.

| Verdict | Model/item | Key | Verbatim response |
|---|---|---|---|
| A | Grok, `0781` | `hits; at 45.7 m` | `ANSWER: hits at 45.7 m` |
| A | Gemini, `0980` | `clears; by 3.0 m` | `ANSWER: Clears by 3.0 m` |
| A | Sonnet, `0621` | `hits; at 10.2 m` | `ANSWER: hits the wall at approximately 10.2 m height` |
| A | Opus, `0892` | `clears; by 2.0 m` | `ANSWER: It clears the wall by about 2.0 m (passing at ≈3.9 m height)` |
| A | DeepSeek, `0015` | `increase` | `increase` |
| R | Muse, `0051` | `hits; at 42.5 m` | `None` |
| R | Gemini, `0051` | same | `ANSWER: Hits at 43.1 m` |
| R | Grok, `0461` | `hits; at 26.9 m` | `ANSWER: hits at 22.7 m` |
| R | Inkling, `0051` | `hits; at 42.5 m` | `ANSWER: clears by 5.4 m` |
| R | Luna, `0430` | `clears; by 29.5 m` | `ANSWER: Clears by 29.0 m` |

Baseline: **82.00% → 82.00%** (modal semantic answer `increase`, 41/50).

| Model | Strict | Proposed |
|---|---:|---:|
| Claude Opus 5 | 84.00% | 92.00% |
| Claude Sonnet 5 | 84.00% | 88.00% |
| DeepSeek V4.1 Flash | 84.00% | 84.00% |
| Gemini 3.8 Flash | 84.00% | 86.00% |
| GPT-5.6 Luna | 72.00% | 72.00% |
| GPT-5.6 Sol | 84.00% | 84.00% |
| Grok 4.6 | 84.00% | 86.00% |
| Inkling | 82.00% | 82.00% |
| Muse Glimmer 30B | 84.00% | 84.00% |
| Perplexity Sonar Pro | 66.00% | 66.00% |

## Counterfactual baselines together

These are the empirical constant-answer baselines on the shared 50-item Test-1 sample. The final row is the already-audited `physical_stability` repair included in the combined analysis.

| Cell | Current | Proposed | Proposed modal semantic answer |
|---|---:|---:|---|
| Compass L5 | 2.00% | 34.00% | `B` |
| FBD L5 | 40.00% | 40.00% | direction 270° |
| Gauge L5 | 6.00% | 6.00% | `no, 85` |
| Gauge L4 | 68.00% | 90.00% | `no` |
| Laser L5 | 8.00% | 22.00% | `no` |
| Optical L5 | 52.00% | 52.00% | `yes, equal` |
| Projectile L5 | 82.00% | 82.00% | `increase` |
| Physical stability L5 | 16.00% | 52.00% | `stable` |

## Combined effect of all repairable cells

This counterfactual applies the seven rules above and the previously proposed `physical_stability` L5 rule simultaneously. “Adjusted” uses the recomputed semantic baselines above. The L4-to-L5 interval is the same 10,000-resample, domain-stratified image-cluster bootstrap used by the existing analysis. “L5 cells below 5%” is counted across all 34 L5 domain cells after repair.

| Model | Raw L5 before | Raw L5 after | Adjusted L5 before | Adjusted L5 after | Adjusted L5−L4 before | Verdict before | Adjusted L5−L4 after (95% CI) | Verdict after | Macro before | Macro after | L5 cells <5% after |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| Claude Opus 5 | 55.18% | 67.41% | 21.81% | 39.91% | +6.90 pp | survives | +17.62 pp (+12.98, +22.24) | survives | 41.98% | 46.80% | 1 |
| Claude Sonnet 5 | 38.35% | 45.35% | -9.57% | -1.67% | -10.47 pp | reverses | -10.51 pp (-16.21, -4.53) | reverses | 23.65% | 26.64% | 5 |
| DeepSeek V4.1 Flash | 34.82% | 38.29% | -30.63% | -29.18% | -22.90 pp | reverses | -28.54 pp (-34.64, -22.32) | reverses | 6.18% | 7.80% | 7 |
| Gemini 3.8 Flash | 55.00% | 68.24% | 21.86% | 40.34% | -0.19 pp | indistinguishable | +11.71 pp (+6.75, +16.73) | survives | 44.82% | 49.55% | 2 |
| GPT-5.6 Luna | 34.00% | 37.76% | -26.41% | -24.11% | -18.98 pp | reverses | -24.18 pp (-30.63, -17.65) | reverses | 6.96% | 8.81% | 4 |
| GPT-5.6 Sol | 40.47% | 48.35% | -9.71% | -0.32% | -12.74 pp | reverses | -9.92 pp (-15.62, -4.31) | reverses | 22.91% | 25.93% | 4 |
| Grok 4.6 | 46.35% | 57.35% | 3.51% | 18.07% | -4.57 pp | indistinguishable | +7.01 pp (+2.39, +11.69) | survives | 28.01% | 31.32% | 1 |
| Inkling | 32.12% | 36.65% | -36.60% | -33.05% | -28.65 pp | reverses | -28.45 pp (-34.72, -22.03) | reverses | 1.94% | 3.24% | 4 |
| Muse Glimmer 30B | 33.47% | 40.88% | -34.06% | -25.92% | -29.12 pp | reverses | -29.65 pp (-34.92, -24.28) | reverses | 8.44% | 11.62% | 8 |
| Perplexity Sonar Pro | 31.35% | 36.88% | -29.59% | -24.46% | -15.99 pp | reverses | -19.01 pp (-25.20, -12.86) | reverses | 4.15% | 6.66% | 6 |

Per-model verdict statements:

- Claude Opus 5 remains a statistically significant positive L5 effect (`survives`).
- Claude Sonnet 5 remains a statistically significant negative L5 effect (`reverses`).
- DeepSeek V4.1 Flash remains `reverses`.
- Gemini 3.8 Flash changes from indistinguishable from zero to a significant positive L5 effect (`survives`).
- GPT-5.6 Luna remains `reverses`.
- GPT-5.6 Sol remains `reverses`.
- Grok 4.6 changes from indistinguishable from zero to a significant positive L5 effect (`survives`).
- Inkling remains `reverses`.
- Muse Glimmer 30B remains `reverses`.
- Perplexity Sonar Pro remains `reverses`.

The “seven of ten models reverse” finding **does survive**: the same seven models still have significantly negative adjusted L5−L4 differences. However, the repair changes Gemini and Grok from statistically indistinguishable to significantly positive, so the non-reversing side of the result becomes stronger.

## Stored-model coverage

Complete Test-1 response files are present for ten models:

- Claude Opus 5
- Claude Sonnet 5
- DeepSeek V4.1 Flash
- Gemini 3.8 Flash
- GPT-5.6 Luna
- GPT-5.6 Sol
- Grok 4.6
- Inkling
- Muse Glimmer 30B
- Perplexity Sonar Pro

The six open-weight models referenced elsewhere are not present as complete Test-1 result files in this repository. They cannot be re-scored from aggregate tables. Their raw stored responses must be exported from the local inference runs and placed in Test-1-compatible JSONL result files—one response keyed by `row_id` for every row in `tests/test_1_closed_loop/plan/closed_loop_manifest.csv`—before this offline audit can include them.

## Interpretation boundary

These results establish that literal full-sentence comparison materially understates performance in all seven audited cells. They do not authorize a score change: the extraction rules remain proposals, and no benchmark output has been replaced.
