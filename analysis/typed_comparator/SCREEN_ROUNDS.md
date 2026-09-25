# Universal below-5% screen rounds

The screen criterion is typed accuracy below 5% for all ten complete models. A hit is audited once; confirmed genuine failures are retained in the score but removed from the *unresolved comparator-defect queue*. This distinction is necessary: otherwise a genuine universally hard cell can never make the audit queue empty.

| Round | Hits | Stage | Finding |
|---|---|---|---|
| 1 | 1 | Initial sentence-valued screen | `physical_stability` L5 |
| 2 | 7 | Seven-cell follow-up | compass L5, FBD L5, gauge L4/L5, laser L5, optical L5, projectile L5 |
| 3 | 6 | Universal all-ten follow-up | depth L3, FBD L3/L4, gear L2, hex L5, projectile L4 |
| 4 | 1 | Typed-comparator raw screen | `compass_bearing` L5 |
| 5 | 0 | Unresolved-defect queue after Round-4 classification | empty |

## Round 4 classification: `compass_bearing` L5

The frozen typed rule requires all three components explicitly requested by the question: the offered landmark, endpoint distance, and bearing difference. Numeric values are exact-match only. The typed accuracies are below 5% for all ten models because responses commonly omit one or both numbers or estimate a different number—not because the parser compares fixed prose.

Ten verbatim failures, one per model:

| Model | Row | Key | Verbatim response |
|---|---|---|---|
| Claude Opus 5 | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B — The endpoint (~78, 98) lies about 76 px from B, far closer than C (~203 px) or D (~300 px); A→C's bearing is ~030°, so the 330° bearing swings the same distance to the northwest, near B.` |
| Claude Sonnet 5 | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B` |
| DeepSeek V4.1 Flash | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B` |
| Gemini 3.8 Flash | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B. A bearing of 330° corresponds to 30° west of north, closely aligning with landmark B (bearing ~320°, difference of only ~10° from A). Traveling the distance of A-to-C in this direction projects an endpoint northwest of A, which is much closer to B than to C or D.` |
| GPT-5.6 Luna | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B` |
| GPT-5.6 Sol | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B — the projected endpoint is nearest B; B lies almost exactly at bearing 330° from A and at roughly the A-to-C distance.` |
| Grok 4.6 | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B (330° NNW from A aligns nearest B; AC dist. overshoots but Δbearing << vs C/D)` |
| Inkling | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B` |
| Muse Glimmer 30B | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B` |
| Perplexity Sonar Pro | `compass_bearing:compass_bearing_0009_q5` | `B; projected endpoint is closest to B (76.7 map units away; bearing difference 10.1 degrees)` | `B – The projected endpoint from A at 330° lies closer to B than to C or D, and its bearing to B differs less from 330° than the bearings to C or D.` |

**Classification: genuine failure under the approved exact-component policy.** The key is templated and fully parseable; accepting these responses would require either dropping a requested component or introducing numeric tolerance, both expressly forbidden. Therefore Round 5's unresolved comparator-defect queue is empty, although the raw performance screen continues to contain this one genuine-failure cell.

No additional comparator schema was introduced after Round 4.
