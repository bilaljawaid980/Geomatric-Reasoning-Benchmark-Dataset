# Frozen typed comparator specification

This comparator is an offline counterfactual. It does not replace published scores. It reads stored responses only. The implementation is [`typed_comparator.py`](typed_comparator.py), while [`cell_types.csv`](cell_types.csv) is the dispatch manifest for all 170 `(domain, level)` cells.

## Universal rules

- Parsing dispatches from the cell's declared `answer_type`; domain/level checks do not select the comparator.
- Numeric equality is exact after syntactic parsing. There is no tolerance.
- The only global aliases are `smaller than → smaller` and `none → neither`.
- A missing explicitly requested component is wrong. A parse failure is wrong, never skipped.
- The strict string verdict is preserved beside every typed verdict.
- Option phrasing is accepted only if the complete normalized response phrase occurs verbatim in the question and differs from the stored short token only by the question's added option word(s).

## Answer types

| Type | Parse | Equality |
|---|---|---|
| `SCALAR` | Existing `ANSWER:` extraction and normalization | Existing exact comparison, plus the narrowly scoped verbatim option-phrase rule |
| `ORDERED_LIST` | JSON/Python list or explicit ordered separators | Same length and exact element equality in order; no set fallback and no colour aliases |
| `TYPED_DICT` | Schema-declared named fields | Every prompt-required field must parse and match exactly |
| `TEMPLATED_SENTENCE` | Schema-declared slots only | Every slot explicitly requested by the prompt must parse and match exactly; fixed key prose is ignored |

## Non-scalar schema declarations

| Cell | Type | Schema | Required components |
|---|---|---|---|
| `compass_bearing` L5 | TEMPLATED_SENTENCE | `compass_l5` | landmark; endpoint distance; bearing difference |
| `depth_height` L3 | ORDERED_LIST | `ordered_tokens` | ordered color labels |
| `fbd` L3 | TYPED_DICT | `fbd_l3` | magnitude_ranking; shown_vertical_forces_balanced; physical_equilibrium |
| `fbd` L4 | TYPED_DICT | `fbd_l4` | prompt-selected numeric fields; wrong-arrow fields when requested |
| `fbd` L5 | TEMPLATED_SENTENCE | `fbd_l5` | yes/no or direction angle |
| `gauge_reading` L4 | TEMPLATED_SENTENCE | `gauge_l4` | danger status; exceedance when yes |
| `gauge_reading` L5 | TEMPLATED_SENTENCE | `gauge_l5` | yes/no; new value |
| `hex_pathfinding` L5 | TEMPLATED_SENTENCE | `hex_l5` | path outcome; new length only when increased |
| `laser_mirror` L5 | TEMPLATED_SENTENCE | `laser_l5` | changed status; edge and position when yes |
| `optical_illusion` L5 | TEMPLATED_SENTENCE | `optical_l5` | change status; actual relation |
| `physical_stability` L5 | TEMPLATED_SENTENCE | `physical_stability_l5` | status; failing ordered joint when unstable |
| `projectile_motion` L4 | TYPED_DICT | `projectile_l4` | time_of_flight_s; range_m |
| `projectile_motion` L5 | TEMPLATED_SENTENCE | `projectile_l5` | range change or obstacle outcome and value |

`fbd` L4's schema examines the prompt/key variant. The 750 corpus items with `wrong_force_details` require the arrow label, error kind, and exact error amount in addition to the numeric fields. Numeric-only answers are wrong on that variant.

## Option-phrasing firings

The rule changed **1,256** stored Test-1 responses. These are the only cells where it fired:

| Cell | Strict → typed changes |
|---|---|
| `gear_train` L2 | 485 |
| `depth_height` L2 | 209 |
| `embedded_figures` L5 | 173 |
| `symmetry_pattern` L4 | 143 |
| `orthographic` L4 | 116 |
| `angle_estimation` L4 | 80 |
| `angle_estimation` L5 | 40 |
| `physical_stability` L2 | 5 |
| `shadow_inference` L5 | 3 |
| `occluded_pattern` L3 | 1 |
| `physical_stability` L4 | 1 |

No colour alias was added. In particular, `pink` is not `magenta`, and `cyan` is not `teal`.
