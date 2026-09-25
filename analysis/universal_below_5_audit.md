# Universal below-5% cell audit after proposed repairs

This is a read-only, counterfactual audit. No API was called, no model was re-run, and no dataset, response, scorer, or existing analysis output was changed. The eight previously proposed repairs were used only to determine which cells remain below 5% for all ten models simultaneously.

## Result

Six `(domain, level)` cells remain below 5% for every model:

| Domain | Level | Opus | Sonnet | DeepSeek | Gemini | Luna | Sol | Grok | Inkling | Muse | Sonar | Diagnosis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `depth_height` | L3 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |
| `fbd` | L3 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |
| `fbd` | L4 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |
| `gear_train` | L2 | 2% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |
| `hex_pathfinding` | L5 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |
| `projectile_motion` | L4 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | comparator defect |

The eight cells covered by the earlier proposed repairs no longer meet the “below 5% for all ten” condition. The six cells above were not altered by those counterfactual repairs, so their displayed scores are their current stored Test-1 scores.

There is **no genuine universal capability failure in this set**. Every cell has multiple verbatim examples where the response contains the requested answer but fails because the key is serialized as a Python list/dictionary, contains an unrequested suffix, or uses a shorter canonical token than the model’s equivalent phrase.

## 1. `depth_height` L3

### Key structure

The full 3,000-item corpus contains 200 distinct Python-list strings. Each is an ordered list of two to four color labels:

`['{COLOR_1}', '{COLOR_2}', ...]`

List lengths are: 965 two-element keys, 1,027 three-element keys, and 1,008 four-element keys. The order is meaningful. The prompt asks for a ranking by color, not Python list syntax.

### Ten verbatim pairs

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `0663` | `['blue', 'teal']` | `ANSWER: blue, teal` | substantively exact |
| Sonnet, `1282` | `['magenta', 'blue']` | `ANSWER: pink, blue` | color-label mismatch (`pink` vs `magenta`) |
| DeepSeek, `0488` | `['magenta', 'orange', 'blue', 'purple']` | `ANSWER: pink, orange, blue, purple` | color-label mismatch |
| Gemini, `0663` | `['blue', 'teal']` | `ANSWER: blue, teal` | substantively exact |
| Luna, `1282` | `['magenta', 'blue']` | `ANSWER: Pink, Blue` | color-label mismatch |
| Sol, `0663` | `['blue', 'teal']` | `ANSWER: blue, teal` | substantively exact |
| Grok, `1282` | `['magenta', 'blue']` | `ANSWER: pink, blue` | color-label mismatch |
| Inkling, `1282` | `['magenta', 'blue']` | `ANSWER: Pink, Blue` | color-label mismatch |
| Muse, `0663` | `['blue', 'teal']` | `ANSWER: blue, teal` | substantively exact |
| Sonar, `0663` | `['blue', 'teal']` | `ANSWER: blue, teal` | substantively exact |

### Verdict

**Comparator defect.** At least five displayed responses reproduce the exact ordered labels and differ only because the key contains brackets and quoted strings. A genuine comparator should parse the key as an ordered sequence and parse comma/arrow-separated response labels into the same representation. Whether `pink` may alias `magenta` is a separate policy decision and is not needed to establish the defect.

## 2. `fbd` L3

### Key structure

All 3,000 keys are Python-dictionary strings with exactly three fields:

```text
{
  'magnitude_ranking': [[tie group 1], [tie group 2], ...],
  'physical_equilibrium': 'yes' or 'no',
  'shown_vertical_forces_balanced': 'yes' or 'no'
}
```

There are 27 distinct complete dictionaries. The prompt asks for the magnitude ranking, whether the drawn vertical components balance, and whether the physically correct body is in equilibrium. It does not ask the model to emit Python.

### Ten verbatim pairs

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `0749` | `{'magnitude_ranking': [['N', 'W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'yes'}` | `ANSWER: N = W (both 178.2 N, tied); the drawn vertical components are balanced (net zero); and physically the body is in equilibrium, since a = 0 means N = mg = 178.2 N.` | all three components correct |
| Sonnet, `0749` | same key | `ANSWER: N = W (178.2 N each); balanced; equilibrium` | all three components correct |
| DeepSeek, `2549` | same key | `ANSWER: Drawn magnitudes: N = W (tie). Drawn vertical components: balanced. Physically correct: equilibrium (a = 0).` | all three components correct |
| Gemini, `1364` | `{'magnitude_ranking': [['T'], ['W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'no'}` | `None` | no usable answer |
| Luna, `2381` | `{'magnitude_ranking': [['N', 'W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'yes'}` | `ANSWER: Shown magnitudes: N = W (tie); shown vertical components: balanced; physically correct overall: in equilibrium.` | all three components correct |
| Sol, `2462` | `{'magnitude_ranking': [['W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'no'}` | `ANSWER: W; no; yes` | all three components correct in prompt order |
| Grok, `1925` | `{'magnitude_ranking': [['N', 'W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'yes'}` | `ANSWER: N=W, yes; yes` | all three components correct in prompt order |
| Inkling, `2443` | `{'magnitude_ranking': [['W'], ['N'], ['F'], ['A']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'no'}` | `ANSWER: (W > N > F > A), yes; not in equilibrium` | ranking correct; final judgments do not match key order/content |
| Muse, `0037` | `{'magnitude_ranking': [['W'], ['F'], ['A']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'no'}` | `None` | no usable answer |
| Sonar, `1109` | `{'magnitude_ranking': [['N', 'W']], 'physical_equilibrium': 'yes', 'shown_vertical_forces_balanced': 'yes'}` | `ANSWER: N = W; yes; yes` | all three components correct in prompt order |

### Verdict

**Comparator defect.** Multiple models state the ranking, balance judgment, and equilibrium judgment correctly, but a natural-language answer cannot equal the serialized dictionary. The response must be parsed into three named semantic components, preserving tie groups and the distinction between the drawn and physically correct frames.

## 3. `fbd` L4

### Key structure

The full corpus contains 2,202 distinct Python-dictionary strings. Every key contains `net_force_N` plus one scenario-specific requested quantity:

| Schema | Corpus rows |
|---|---:|
| `net_force_N`, `required_friction_coefficient` | 1,000 |
| `net_force_N`, `tension_magnitude` | 1,000 |
| `minimum_friction_coefficient`, `net_force_N` | 500 |
| `net_force_N`, `support_force_magnitude` | 500 |

In 750 of the 3,000 items, the same schemas additionally contain a nested `wrong_force_details` dictionary because the prompt also asks the model to identify and explain an intentionally incorrect arrow. The nested fields include the arrow label, force identity, error type, shown value, correct value, and explanation.

### Ten verbatim pairs

These pairs deliberately use keys without `wrong_force_details`, so exact agreement on the two requested numerical components is sufficient to prove the representation defect.

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `0037` | `{'net_force_N': 0.0, 'required_friction_coefficient': 0.4}` | `ANSWER: net force = 0 N (block stays static); required μ ≈ 0.40` | exact values |
| Sonnet, `0037` | same key | `ANSWER: net force = 0 N, required μ ≈ 0.40` | exact values |
| DeepSeek, `0232` | `{'minimum_friction_coefficient': 0.68, 'net_force_N': 0.0}` | `ANSWER: Physical net force magnitude: 0 N; minimum friction coefficient: 0.680` | exact values |
| Gemini, `0337` | `{'net_force_N': 0.0, 'required_friction_coefficient': 0.68}` | `ANSWER: Net force = 0 N, required friction coefficient = 0.68` | exact values |
| Luna, `1994` | `{'net_force_N': 0.0, 'tension_magnitude': 134.3}` | `ANSWER: Net force = 0 N; tension = 134.3 N` | exact values |
| Sol, `1994` | same key | `ANSWER: 0 N, 134.3 N` | exact values in prompt order |
| Grok, `1994` | same key | `ANSWER: 0, 134.3` | exact values in prompt order |
| Inkling, `0414` | `{'net_force_N': 0.0, 'required_friction_coefficient': 0.38}` | `ANSWER: Net force = 0.0 N, μ = 0.38` | exact values |
| Muse, `1994` | `{'net_force_N': 0.0, 'tension_magnitude': 134.3}` | `ANSWER: net force magnitude 0 N, tension magnitude ≈ 134.3 N` | exact values |
| Sonar, `1994` | same key | `ANSWER: net force = 0 N, tension = 134.3 N` | exact values |

### Verdict

**Comparator defect.** All ten models have at least one exact two-value answer that scores wrong solely because it is compared to a Python dictionary string. A structured comparator must select fields based on the prompt variant and, for the 750 wrong-arrow prompts, must additionally require the requested arrow/error components rather than silently ignoring them.

## 4. `gear_train` L2

### Key structure

All 3,000 keys are the single token `opposite`; there is one distinct answer. The prompt asks whether gear B rotates in the “same direction” or “opposite direction.”

### Ten verbatim pairs

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `2085` | `opposite` | `ANSWER: opposite` | exact; the one currently credited response in this sample |
| Sonnet, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| DeepSeek, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Gemini, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Luna, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Sol, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Grok, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Inkling, `1255` | `opposite` | `Opposite direction` | semantically exact |
| Muse, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |
| Sonar, `0015` | `opposite` | `ANSWER: opposite direction` | semantically exact |

### Verdict

**Comparator defect.** `opposite direction` repeats an option exactly as phrased in the question and must normalize to `opposite`. The observed 2%/0% pattern reflects one Opus response using the shorter key token, not a model capability difference. This cell is also constant-answer and should remain excluded from above-baseline inference even after comparator repair.

## 5. `hex_pathfinding` L5

### Key structure

The 3,000 keys instantiate three semantic forms with 17 distinct complete strings:

- `no valid path exists` — 1,000 items.
- `stay the same ({MOVES} moves)` — 1,000 items across move counts 4–9.
- `increase to {MOVES} moves` — 1,000 items across move counts 6–16.

The prompt requests the new length only **if the path increases**. The parenthesized original/remaining length in `stay the same ({MOVES} moves)` is therefore extra key information that the response was not required to state.

### Ten verbatim pairs

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `0511` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| Sonnet, `0487` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| DeepSeek, `0487` | `stay the same (4 moves)` | `Let's go through it carefully. ... So, the shortest path length **stays the same**.\n\n**ANSWER: stay the same**` | fully answers the prompt |
| Gemini, `0487` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| Luna, `0015` | `no valid path exists` | `ANSWER: No valid path` | semantically exact |
| Sol, `0487` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| Grok, `0487` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| Inkling, `0487` | `stay the same (4 moves)` | `ANSWER: stay the same` | fully answers the prompt |
| Muse, `0015` | `no valid path exists` | `ANSWER: no valid path` | semantically exact |
| Sonar, `1047` | `no valid path exists` | `ANSWER: no valid path` | semantically exact |

### Verdict

**Comparator defect.** All ten models provide at least one response that completely satisfies the prompt but fails literal comparison. A semantic comparator should accept `no valid path` variants; accept `stay the same` without requiring a move count; and, only for `increase`, require both the increase classification and exact new shortest length.

## 6. `projectile_motion` L4

### Key structure

All 1,000 keys are Python-dictionary strings with two fields:

`{'time_of_flight_s': {TIME}, 'range_m': {RANGE}}`

There are 787 distinct complete dictionaries. The prompt asks for both numbers rounded to one decimal; it does not request JSON or Python syntax.

### Ten verbatim pairs

| Model/item | Verbatim key | Verbatim response | Assessment |
|---|---|---|---|
| Opus, `0525` | `{'time_of_flight_s': 0.9, 'range_m': 7.8}` | `ANSWER: 0.9 s, 7.8 m` | exact values |
| Sonnet, `0551` | `{'time_of_flight_s': 2.6, 'range_m': 81.9}` | `ANSWER: 2.6, 81.9` | exact values in prompt order |
| DeepSeek, `0017` | `{'time_of_flight_s': 5.4, 'range_m': 49.3}` | `... ANSWER: 5.4, 49.2` | time correct, range differs by 0.1 |
| Gemini, `0017` | `{'time_of_flight_s': 5.4, 'range_m': 49.3}` | `ANSWER: 5.4 s, 49.3 m` | exact values |
| Luna, `0050` | `{'time_of_flight_s': 5.4, 'range_m': 47.0}` | `ANSWER: 4.9 s, 99.1 m` | both values wrong |
| Sol, `0525` | `{'time_of_flight_s': 0.9, 'range_m': 7.8}` | `ANSWER: 0.9 s, 7.8 m` | exact values |
| Grok, `0525` | `{'time_of_flight_s': 0.9, 'range_m': 7.8}` | `ANSWER: 0.9 7.8` | exact values in prompt order |
| Inkling, `0199` | `{'time_of_flight_s': 5.2, 'range_m': 43.7}` | `ANSWER: 5.0 s, 70.5 m` | both values wrong |
| Muse, `0051` | `{'time_of_flight_s': 6.3, 'range_m': 129.5}` | `None` | no usable answer |
| Sonar, `0525` | `{'time_of_flight_s': 0.9, 'range_m': 7.8}` | `ANSWER: 0.9 s, 8.3 m` | time correct, range wrong |

### Verdict

**Comparator defect.** Several responses give both requested one-decimal values exactly but score zero because they are not serialized dictionaries. A structured comparator should extract two numbers in named or prompt order and require exact numeric equality for both, with no additional tolerance.

## Overall conclusion

After the eight previously proposed repairs, the universal below-5% signature identifies **six additional comparator-defective cells and zero demonstrated universal capability failures**. Their common causes are:

- serialized list or dictionary keys compared against ordinary answers (`depth_height` L3, `fbd` L3/L4, `projectile_motion` L4);
- an equivalent phrase not normalized to the canonical token (`gear_train` L2); and
- key text requiring information the prompt did not require (`hex_pathfinding` L5 stay-same branch), plus ordinary paraphrase handling.

No proposed comparator was applied and no accuracy or aggregate report was replaced.
