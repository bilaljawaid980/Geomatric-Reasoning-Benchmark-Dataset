# Open-question specification implementation report

## Per-domain validation and coverage

| Dataset | Version | Source | Included | Excluded | Exclusion reason(s) | Highest baseline | Result |
|---|---|---:|---:|---:|---|---:|---|
| `angle_estimation_dataset_3000` | `angle-estimation-9.0.0` | 3,000 | 3,000 | 0 | none | 0.501 | PASS |
| `clock_reading_dataset_3000` | `clock-reading-5.0.0` | 3,000 | 3,000 | 0 | none | 0.004 | PASS |
| `combination3d_dataset_3000` | `combination3d-5.0.0` | 3,000 | 3,000 | 0 | none | 0.353 | PASS |
| `combination_dataset_3000` | `combination-4.0.0` | 3,000 | 3,000 | 0 | none | 0.351 | PASS |
| `compass_bearing_dataset_3000` | `compass-bearing-8.0.0` | 3,000 | 3,000 | 0 | none | 0.264 | PASS |
| `coordinate_geometry_dataset_3000` | `coordinate-geometry-7.0.0` | 3,000 | 3,000 | 0 | none | 0.531 | PASS |
| `cube_net_dataset_3000` | `cube-net-5.0.0` | 3,000 | 3,000 | 0 | none | 0.178 | PASS |
| `cube_structure_dataset_3000` | `cube-structure-6.0.0` | 3,000 | 3,000 | 0 | none | 0.333 | PASS |
| `depth_height_dataset_3000` | `depth-height-7.0.0` | 3,000 | 3,000 | 0 | none | 0.023 | PASS |
| `embedded_figures_dataset_3000` | `embedded-figures-5.0.0` | 3,000 | 3,000 | 0 | none | 0.250 | PASS |
| `fbd_dataset_3000` | `free-body-diagram-6.0.0` | 3,000 | 3,000 | 0 | none | 0.122 | PASS |
| `fold_punch_dataset_3000` | `fold-punch-6.0.0` | 3,000 | 3,000 | 0 | none | 0.250 | PASS |
| `gauge_reading_dataset_3000` | `gauge-reading-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `gear_train_dataset_3000` | `gear-train-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `hex_pathfinding_dataset_3000` | `hex-pathfinding-7.0.0` | 3,000 | 3,000 | 0 | none | 0.419 | PASS |
| `impossible_object_dataset_3000` | `impossible-object-7.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `laser_mirror_dataset_3000` | `laser-mirror-5.0.0` | 3,000 | 3,000 | 0 | none | 0.697 | PASS |
| `line_intersection_dataset_3000` | `line-intersection-7.0.0` | 3,000 | 3,000 | 0 | none | 0.503 | PASS |
| `nested_hexagons_dataset_3000` | `nested-hexagons-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `nested_squares_dataset_3000` | `nested-squares-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `nested_triangles_dataset_3000` | `nested-triangles-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `occluded_pattern_dataset_3000` | `occluded-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.369 | PASS |
| `optical_illusion_dataset_3000` | `optical-illusion-6.0.0` | 3,000 | 3,000 | 0 | none | 0.512 | PASS |
| `orthographic_dataset_3000` | `orthographic-5.0.0` | 3,000 | 3,000 | 0 | none | 0.561 | PASS |
| `overlap_circles_dataset_3000` | `overlap-circles-6.0.0` | 3,000 | 3,000 | 0 | none | 0.254 | PASS |
| `physical_stability_dataset_3000` | `physical-stability-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `polyhedron_dataset_3000` | `polyhedron-8.0.0` | 3,000 | 3,000 | 0 | none | 0.895 | PASS |
| `projectile_motion_dataset_1000` | `projectile-motion-5.0.0` | 1,000 | 1,000 | 0 | none | 0.507 | PASS |
| `rotation_matching_dataset_3000` | `rotation-matching-5.0.0` | 3,000 | 3,000 | 0 | none | 0.260 | PASS |
| `route_dataset_3000` | `route-6.0.0` | 3,000 | 3,000 | 0 | none | 0.004 | PASS |
| `rpm_dataset_3000` | `rpm-6.0.0` | 3,000 | 3,000 | 0 | none | 0.151 | PASS |
| `shadow_inference_dataset_3000` | `shadow-inference-5.0.0` | 3,000 | 3,000 | 0 | none | 0.505 | PASS |
| `surface_topology_dataset_3000` | `surface-topology-7.0.0` | 3,000 | 3,000 | 0 | none | 0.750 | PASS |
| `symmetry_pattern_dataset_3000` | `symmetry-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |

## Defects found before fixes

- **Clock reading:** the former smaller-hand-angle sub-fact was deterministically recoverable from the exact-time sub-fact in all 3,000 items. This was reported before modification; the recommended fix was applied by retaining exact time and removing the redundant angle from the open question.
- **Surface topology:** the former Euler-characteristic sub-fact was deterministically fixed by genus and orientability in all 3,000 closed-surface items. This was reported before modification; the recommended fix was applied by retaining genus and orientability and removing the redundant Euler value from the open question.
- **Compass bearing ambiguity:** 283 of 3,000 scenes have a closest-versus-second-closest distance gap below 5%. The farthest-pair fallback recovers 248; the explicitly named A-to-B variant recovers the final 35 after render review confirmed legible labels and readable separation.
- **RPM option identity:** all 3,000 records admitted multiple answers under the matrix-derived semantic attributes. The pre-fix satisfying-option distribution was 2 options: 844, 3 options: 1,916, and 4 options: 240; `rpm_0151` admitted choices 1, 4, and 7. Rotation distinguished options in all 3,000 and size/shape spacing did so in 2,156, although neither was always taught; stroke width never discriminated. Equal circumradius also made triangles appear smaller than circles.
- **Orthographic convention:** all 3,000 stored projections consistently used top `(x,y)`, front `(x,z)`, and side `(y,z)`, with each first coordinate increasing left-to-right and z increasing bottom-to-top. The side panel did not print that direction, so a viewer could reasonably mirror it. Before the label repair, gravity support changed the computed minimum in 1,883 records and made no difference in 1,117; `orthographic_0223` required 11 cubes with gravity versus 10 without it.

## Final ambiguity and convention repairs

- **RPM:** all 3,000 images were regenerated. Options satisfying the independently derived rule set: `{"1": 3000}`; multi-valid items: 0. Undeclared option attributes are frozen: `{}`. Shape areas are normalised, spacing depends only on size/count, and stroke width is fixed.
- **Orthographic:** axes are printed as `{"front": "+x right; +z up", "side": "+y right; +z up", "top": "+x right; +y up"}`. The side projection agrees with the +y-right convention in 3000/3,000 records. Gravity-supported minus unconstrained minimum counts: `{"0": 1117, "1": 1044, "2": 677, "3": 156, "4": 6}`; gravity changes 1883 items and changes nothing in 1117. Item 0223 is 11 with gravity versus 10 without it.
- **Compass:** the guarded farthest-pair fallback recovered 248 closest-pair near-ties. The named A-to-B variant recovered the final 35; labels A and B were present and manually confirmed legible in 35/35 renders. Their separation ranged from 91.236 to 351.104 pixels. Remaining exclusions: 0.

### Named A-to-B fallback render audit

| Item | A-to-B distance (px) | A and B present | Labels legible | Bearing readable |
|---|---:|---|---|---|
| `compass_bearing_0071` | 314.102 | yes | yes | yes |
| `compass_bearing_0145` | 220.045 | yes | yes | yes |
| `compass_bearing_0440` | 231.294 | yes | yes | yes |
| `compass_bearing_0923` | 111.803 | yes | yes | yes |
| `compass_bearing_1004` | 274.855 | yes | yes | yes |
| `compass_bearing_1014` | 184.448 | yes | yes | yes |
| `compass_bearing_1055` | 284.522 | yes | yes | yes |
| `compass_bearing_1089` | 98.595 | yes | yes | yes |
| `compass_bearing_1110` | 202.371 | yes | yes | yes |
| `compass_bearing_1171` | 235.053 | yes | yes | yes |
| `compass_bearing_1175` | 263.412 | yes | yes | yes |
| `compass_bearing_1206` | 161.839 | yes | yes | yes |
| `compass_bearing_1309` | 269.757 | yes | yes | yes |
| `compass_bearing_1381` | 201.070 | yes | yes | yes |
| `compass_bearing_1397` | 116.108 | yes | yes | yes |
| `compass_bearing_1472` | 315.546 | yes | yes | yes |
| `compass_bearing_1541` | 201.675 | yes | yes | yes |
| `compass_bearing_1735` | 196.703 | yes | yes | yes |
| `compass_bearing_1843` | 158.858 | yes | yes | yes |
| `compass_bearing_1857` | 196.431 | yes | yes | yes |
| `compass_bearing_1947` | 118.701 | yes | yes | yes |
| `compass_bearing_1949` | 215.745 | yes | yes | yes |
| `compass_bearing_2059` | 198.093 | yes | yes | yes |
| `compass_bearing_2067` | 143.951 | yes | yes | yes |
| `compass_bearing_2081` | 142.299 | yes | yes | yes |
| `compass_bearing_2093` | 290.630 | yes | yes | yes |
| `compass_bearing_2319` | 186.207 | yes | yes | yes |
| `compass_bearing_2473` | 119.281 | yes | yes | yes |
| `compass_bearing_2493` | 279.546 | yes | yes | yes |
| `compass_bearing_2624` | 292.250 | yes | yes | yes |
| `compass_bearing_2626` | 171.680 | yes | yes | yes |
| `compass_bearing_2633` | 242.695 | yes | yes | yes |
| `compass_bearing_2679` | 203.000 | yes | yes | yes |
| `compass_bearing_2859` | 351.104 | yes | yes | yes |
| `compass_bearing_2881` | 91.236 | yes | yes | yes |

## Six manual-review findings

1. **Line intersection:** endpoint-order/parity exceptions: 0. The redundant endpoint-order sub-fact was replaced by left-edge higher colour; crossing counts now coexist with both colours, so neither answer determines the other.
2. **Coordinate geometry 0101:** points `{"A": [3, 6], "B": [-7, 8], "C": [-2, -1]}`; pairwise distances `{"A-B": 10.2, "A-C": 8.6, "B-C": 10.3}`; actual farthest pair `B-C`. The stored answer was correct but visually marginal. The 1-unit guard rejected 356 of 2000 multi-pair scenes from that template and routed them to the all-coordinates fallback without reducing coverage.
3. **Nested squares 0095:** factors `[0.7897489, 0.78974875, 0.78974863, 0.78974867, 0.78974906, 0.78974861, 0.78974893]` are equal within render precision, so `constant` is correct. Manual constant/changing agreement was 19/20 triangles, 19/20 squares, and 19/20 hexagons; the 1.35 span floor was retained.
4. **Rotation matching 0078:** nearest-candidate distance 0.391038 normalized (16.81 px); minimum turning angle 34.70729°. Transformations `{"reflection": 3000, "target_rotation": 3000, "wrong_angle_rotation": 6000}` contain no distortions. The existing 0.08 separation guard has 0 violations and was retained.
5. **Embedded figures:** `same_side_foil_exists` is `{"false": 1500, "true": 1500}`. The exact 1,500/1,500 balance is substantial, so no change was made.
6. **Hex pathfinding 0124:** renderer is pointy-top (vertices at top and bottom; vertical left/right sides). Axial-to-screen mapping in hex-size units is `{"left": [-1.7320508075688772, 0.0], "lower-left": [-0.8660254037844386, 1.5], "lower-right": [0.8660254037844386, 1.5], "right": [1.7320508075688772, 0.0], "upper-left": [-0.8660254037844386, -1.5], "upper-right": [0.8660254037844386, -1.5]}`. `(1,0)` is directly right at the same screen y; inadmissible stored directions: 0. No data change was needed.

## Laser zero-reflection recovery

All 750 zero-reflection scenes now use the straight-path prompt. Near-miss distribution: `{"0": 255, "1": 349, "2": 118, "3": 25, "4": 3}`; constant-answer baseline: 0.465.

## Sub-facts at or above 60%

| Dataset | Sub-fact | Baseline | Disposition |
|---|---|---:|---|
| `laser_mirror_dataset_3000` | `reflection_count` | 0.697 | Inherent among the nonzero-reflection trace variant; zero-reflection scenes now use a separate varying prompt. |
| `polyhedron_dataset_3000` | `convexity` | 0.895 | Inherent to the generated solid inventory after geometry-identity repair; retained and reported. |
| `surface_topology_dataset_3000` | `orientability` | 0.750 | Inherent to the generated surface inventory; retained and reported. |

## Previous empirical-redundancy findings: classification and treatment

| Dataset | Classification | Construction reason | Treatment |
|---|---|---|---|
| `angle_estimation_dataset_3000` | Deterministic | The single-angle boundary guard makes class uniquely recoverable from the rounded size. | Removed `angle_class`; retained the rounded size. |
| `depth_height_dataset_3000` | Deterministic | Nearest is the first depth-order entry and tallest is the final height-order entry. | Removed both extrema; retained each complete ordering. |
| `embedded_figures_dataset_3000` | Deterministic | Side count and correct candidate letter share the same modulo-4 item schedule. | Removed side count; retained candidate identity. |
| `fbd_dataset_3000` | Deterministic | The magnitude ranking enumerates every arrow label, revealing arrow count and the conventional weight label. | Removed arrow count and weight label; retained ranking. |
| `fold_punch_dataset_3000` | Deterministic | Fold parity and candidate letter share the item-index schedule. | Removed hole count; retained correct pattern. |
| `hex_pathfinding_dataset_3000` | Deterministic | Boundary and neighbour counts are functions of the same six-cell neighbourhood. | Removed boundary/count fields; retained hole directions. |

## Shared deterministic-dependency audit

Method: for each target sub-fact, the validator tests every one-to-three-field subset of the other populated sub-facts. It flags a mapping when repeated predictor tuples cover at least 80% of eligible rows and every tuple maps to exactly one target value. Explicit prohibited semantic identities are validation failures.

No empirical deterministic relationships were flagged.

## Twelve-domain manual render review

### `clock_reading_dataset_3000`

**Item:** `clock_reading_1501.png`

**Exact question:**

> Trace both hands from the centre of the dial out towards the printed numerals: work out which is the hour hand and which is the minute hand, and read the time they show. State your conclusion, justify it by describing where each hand tip falls among the numerals, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `time`: `11:38`

**Written derivation:**

1. The minute hand points to minute 38, or 228 degrees clockwise from 12.
2. The shorter hour hand lies between 11 and 12 at 349 degrees, so the displayed time is 11:38.

**Visual recoverability:** Both hand tips against the printed numerals; no occluded quantity is graded.

**Derivable redundancy:** The former angle field was exactly derivable from time in all 3,000 records and was removed.

**Nearest-alternative margin:** No candidate or extreme is selected.

**Answer distributions and baselines:**

- `time`: baseline 0.004; distribution 654 distinct answers; full counts in `clock_reading_dataset_3000/open_validation_metrics.json`

### `combination_dataset_3000`

**Item:** `combination_1501.png`

**Exact question:**

> Compare each separated piece of every candidate with the target shape: decide which single candidate could be slid and turned, without being flipped over, to reproduce the target exactly, and say what disqualifies one of the candidates you rejected. State your conclusion, justify it by describing how you tried to fit the pieces together, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `correct_candidate`: `A`
- `rejected_candidate`: `B`
- `rejection_reason`: `gap or overlap`

**Written derivation:**

1. The target cell set contains 9 cells.
2. Candidate A's two pieces contain 9 cells and can be translated and rotated to cover that set without reflection.
3. Candidate B also contains 9 cells but its stored geometric placement test produces a gap or overlap, so A is the valid candidate and B is the reported rejection.

**Visual recoverability:** Trace every unit-cell boundary in the target and separated candidate pieces; all graded evidence is visible.

**Derivable redundancy:** The chosen valid candidate does not determine which rejected candidate is sampled or its failure class.

**Nearest-alternative margin:** All 3,000 items contain exactly one valid candidate. Failure modes, rather than a single scalar distance, distinguish the wrong alternatives; the reviewed item had no visually indistinguishable panel.

**Answer distributions and baselines:**

- `correct_candidate`: baseline 0.250; distribution {"A": 750, "B": 750, "C": 750, "D": 750}
- `rejected_candidate`: baseline 0.259; distribution {"A": 769, "B": 742, "C": 776, "D": 713}
- `rejection_reason`: baseline 0.351; distribution {"gap or overlap": 1018, "requires being flipped over": 928, "wrong cell count": 1054}

### `combination3d_dataset_3000`

**Item:** `combination3d_1531.png`

**Exact question:**

> Compare each separated group of cubes in every candidate with the target structure: decide which single candidate could be moved and turned about the upright axis to reproduce the target exactly, and say what disqualifies one of the candidates you rejected. State your conclusion, justify it by describing how you tried to fit the groups together and how you accounted for cubes hidden behind others, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `correct_candidate`: `C`
- `rejected_candidate`: `B`
- `rejection_reason`: `requires turning about a forbidden axis`

**Written derivation:**

1. The stored target geometry has 11 cubes in a ten-cell footprint with one additional cube above a supported base cube.
2. Candidate C's pieces total 11 cubes and match the target under translations and rotations about z.
3. Candidate B also totals 11, but matching it requires a forbidden 3-D tumble, so C is correct and B supplies the rejection reason.

**Visual recoverability:** Use exposed top and side faces, visible column continuity, and the separated candidate groups. The supporting cube beneath the upper cube is inferred, but target cube count is not a graded sub-fact.

**Derivable redundancy:** The valid candidate does not determine the independently sampled rejected panel or failure class.

**Nearest-alternative margin:** Exactly one valid candidate exists in all 3,000 items. Wrong alternatives are separated by count, forbidden-axis, or fit constraints; no scalar pixel-gap field exists.

**Answer distributions and baselines:**

- `correct_candidate`: baseline 0.250; distribution {"A": 750, "B": 750, "C": 750, "D": 750}
- `rejected_candidate`: baseline 0.255; distribution {"A": 750, "B": 753, "C": 766, "D": 731}
- `rejection_reason`: baseline 0.353; distribution {"gap or overlap": 1060, "requires turning about a forbidden axis": 980, "wrong cube count": 960}

### `compass_bearing_dataset_3000`

**Item:** `compass_bearing_1403.png`

**Exact question:**

> Read the compass rose in the corner, then compare the straight-line displacement between every pair of landmarks: name the two landmarks that lie closest together, and give the bearing in degrees from the alphabetically earlier of them to the other, measuring clockwise from north and answering to the nearest 10 degrees. State your conclusion, justify it by describing the displacements you compared and how you read the direction against the rose, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `closest_pair`: `C-D`
- `bearing_degrees_nearest_10`: `70`

**Written derivation:**

1. The pairwise distances have minimum C-D = 82.873; the next smallest is B-C = 97.015, a 17.1% relative margin.
2. From C=(103,239) to D=(181,211), the screen displacement is 78 pixels right and 28 pixels up.
3. atan2(east displacement, north displacement) gives 70.253 degrees clockwise from north, which rounds to 70 degrees.

**Visual recoverability:** Compare landmark separations, then read the selected displacement against the rendered compass rose. No sector label is inferred.

**Derivable redundancy:** Closest-pair identity does not determine its bearing; the same pair labels occur with varying bearings.

**Nearest-alternative margin:** Closest-pair near-ties use the guarded farthest-pair fallback; dual-margin failures use the explicitly named A-to-B pair.

**Answer distributions and baselines:**

- `closest_pair`: baseline 0.264; distribution {"A-B": 674, "A-C": 716, "A-D": 239, "B-C": 657, "B-D": 206, "C-D": 225}
- `bearing_degrees_nearest_10`: baseline 0.049; distribution 36 distinct answers; full counts in `compass_bearing_dataset_3000/open_validation_metrics.json`

### `impossible_object_dataset_3000`

**Item:** `impossible_object_1501.png`

**Exact question:**

> Trace each beam through the structure and look closely at the points where one beam passes in front of another: count those crossings, then decide whether the depth relationships they imply could all hold at once in a real three-dimensional object. State your conclusion, justify it by describing which beam passes in front at the crossings that decide the matter, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `crossing_count`: `8`
- `constructible`: `yes`

**Written derivation:**

1. The stored crossing list X1-X8 contains 8 projected crossings.
2. Direct each depth constraint from front beam to back beam.
3. The ordering E, F, B, D, A, C satisfies every constraint, so the graph is acyclic and the object is constructible.

**Visual recoverability:** Count the rendered over/under crossing gaps and follow beam labels through them. Constructibility is computed from the jointly visible depth ordering, not directly printed.

**Derivable redundancy:** Crossing count does not determine whether the depth-constraint graph contains a cycle.

**Nearest-alternative margin:** No candidate or numerical extreme is selected.

**Answer distributions and baselines:**

- `crossing_count`: baseline 0.250; distribution {"6": 750, "7": 750, "8": 750, "9": 750}
- `constructible`: baseline 0.500; distribution {"no": 1500, "yes": 1500}

### `nested_hexagons_dataset_3000`

**Item:** `nested_hexagons_1501.png`

**Exact question:**

> Work outward from the innermost shape to the outermost: count how many shapes are nested inside one another, decide whether each step shrinks by roughly the same factor or by a changing one, and estimate through how many degrees the innermost shape has been turned relative to the outermost, giving a value from 0 to 60 degrees to the nearest 10. State your conclusion, justify it by describing how you matched corresponding corners between the innermost and outermost shapes, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `shape_count`: `12`
- `shrink_pattern`: `constant`
- `rotation_degrees_nearest_10`: `20`

**Written derivation:**

1. The hexagons array contains 12 outlines.
2. All eleven step factors lie near 0.821235, so their span is within the constant-ratio criterion.
3. The stored cumulative corner rotation is 21 degrees modulo 60, which rounds to 20 degrees.

**Visual recoverability:** Count separate outlines, compare successive side lengths, and match corresponding corners. Rotation is estimated rather than directly labelled.

**Derivable redundancy:** Count, shrink mode, and cumulative rotation vary independently in the generated design.

**Nearest-alternative margin:** The constant/changing decision uses the established 1.35 perceptibility span; manual review agreement was 19/20.

**Answer distributions and baselines:**

- `shape_count`: baseline 0.115; distribution {"10": 332, "11": 332, "12": 344, "4": 332, "5": 332, "6": 332, "7": 332, "8": 332, "9": 332}
- `shrink_pattern`: baseline 0.500; distribution {"changing": 1500, "constant": 1500}
- `rotation_degrees_nearest_10`: baseline 0.207; distribution {"0": 450, "10": 312, "20": 622, "30": 622, "40": 622, "50": 372}

### `nested_triangles_dataset_3000`

**Item:** `nested_triangles_1501.png`

**Exact question:**

> Work outward from the innermost shape to the outermost: count how many shapes are nested inside one another, decide whether each step shrinks by roughly the same factor or by a changing one, and estimate through how many degrees the innermost shape has been turned relative to the outermost, giving a value from 0 to 120 degrees to the nearest 10. State your conclusion, justify it by describing how you matched corresponding corners between the innermost and outermost shapes, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `shape_count`: `4`
- `shrink_pattern`: `constant`
- `rotation_degrees_nearest_10`: `60`

**Written derivation:**

1. The triangles array contains 4 outlines.
2. The three step factors are 0.47555406, 0.47555424, and 0.47555390, so the shrink pattern is constant.
3. The cumulative rotation is 61 degrees modulo 120, which rounds to 60 degrees.

**Visual recoverability:** Count outlines, compare successive side-length ratios, and match corresponding vertices. Rotation is estimated from visible corners.

**Derivable redundancy:** Count, shrink mode, and rotation are separately sampled.

**Nearest-alternative margin:** The constant/changing decision uses the 1.35 perceptibility span; manual review agreement was 19/20.

**Answer distributions and baselines:**

- `shape_count`: baseline 0.115; distribution {"10": 332, "11": 332, "12": 344, "4": 332, "5": 332, "6": 332, "7": 332, "8": 332, "9": 332}
- `shrink_pattern`: baseline 0.500; distribution {"changing": 1500, "constant": 1500}
- `rotation_degrees_nearest_10`: baseline 0.150; distribution {"0": 450, "100": 286, "20": 258, "30": 288, "40": 286, "50": 286, "60": 286, "70": 288, "80": 286, "90": 286}

### `orthographic_dataset_3000`

**Item:** `orthographic_1501.png`

**Exact question:**

> Compare the three orthographic views against one another: work out the smallest number of cubes a gravity-supported structure could have while still producing all three, and decide whether those views pin down a single arrangement or whether some different arrangement could produce the same three silhouettes. State your conclusion, justify it by describing which view constrains which direction, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `minimum_cube_count`: `10`
- `uniqueness`: `not unique`

**Written derivation:**

1. The top view requires five occupied columns at (-2,0), (-1,0), (-1,1), (-1,2), and (0,0).
2. Front maxima require heights 1, 4, and 2 for x=-2,-1,0; side maxima require heights 2,4,2 for y=0,1,2.
3. The minimum compatible heights are 1,1,4,2,2, totaling 10 cubes.
4. The (-1,0) height may be 1 or 2 while all silhouettes stay unchanged, so the structure is not unique.

**Visual recoverability:** Read filled cells in all three printed views. Minimum count and uniqueness are computed by reconciling the silhouettes; individual hidden cubes are inferred, not seen.

**Derivable redundancy:** Minimum count does not determine uniqueness; both unique and non-unique scenes occur at shared counts.

**Nearest-alternative margin:** No labelled candidate is selected; ambiguity is established by an explicit second compatible height assignment.

**Answer distributions and baselines:**

- `minimum_cube_count`: baseline 0.188; distribution {"10": 563, "11": 392, "12": 165, "6": 474, "7": 460, "8": 468, "9": 478}
- `uniqueness`: baseline 0.561; distribution {"not unique": 1318, "unique": 1682}

### `polyhedron_dataset_3000`

**Item:** `polyhedron_1501.png`

**Exact question:**

> Examine the solid's visible faces and the edges bounding them: say what shapes its faces are, and decide whether the solid is convex or whether some part of it folds inward. State your conclusion, justify it by describing the faces you could identify and how you judged convexity, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `face_shapes`: `pentagons`
- `convexity`: `convex`

**Written derivation:**

1. The faces array contains 12 faces and every face has arity 5, independently yielding pentagons.
2. The 20 vertices and every supporting face lie on the boundary of one convex hull.
3. The record is not a compound, so the direct face-support and hull test yields convex.

**Visual recoverability:** Count boundary edges of visible faces and inspect the silhouette for inward folds or interpenetrating components. Hidden faces are not counted.

**Derivable redundancy:** Face arity does not determine convexity; triangular and mixed-face records occur in both convex and non-convex classes.

**Nearest-alternative margin:** No candidate or numerical extreme is selected. Direct geometry mismatches for face shape and convexity: 0/3,000.

**Answer distributions and baselines:**

- `face_shapes`: baseline 0.369; distribution {"mixed": 1106, "pentagons": 315, "squares": 474, "triangles": 1105}
- `convexity`: baseline 0.895; distribution {"convex": 2684, "non-convex": 316}

### `rpm_dataset_3000`

**Item:** `rpm_1501.png`

**Exact question:**

> Read across the rows and down the columns of the matrix to work out what changes from one panel to the next: decide which of the numbered choices completes the pattern, and say which attributes had to change together for that choice to be the right one. State your conclusion, justify it by describing the progression you found along the rows and down the columns, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `correct_choice`: `4`
- `attributes_changed_together`: `["color","count"]`

**Written derivation:**

1. Within each row, the count decreases from three to two to one.
2. Within each column, the colour progresses from purple to blue to green.
3. The missing panel must therefore contain one green star; choice 4 is the only option that satisfies both progressions while shape, size, and rotation remain fixed.

**Visual recoverability:** Compare rendered colour and count progressions along perpendicular axes, then check the numbered choices; all untaught attributes are visibly frozen.

**Derivable redundancy:** The valid choice does not determine which two attributes were sampled as rules across the domain.

**Nearest-alternative margin:** Exactly one option satisfies the independently derived matrix patterns in every item; undeclared option attributes never vary.

**Answer distributions and baselines:**

- `correct_choice`: baseline 0.136; distribution {"1": 358, "2": 407, "3": 355, "4": 385, "5": 363, "6": 387, "7": 366, "8": 379}
- `attributes_changed_together`: baseline 0.151; distribution {"[\"color\",\"count\"]": 395, "[\"color\",\"rotation\"]": 318, "[\"rotation\",\"count\"]": 380, "[\"shape\",\"color\"]": 255, "[\"shape\",\"count\"]": 454, "[\"shape\",\"size\"]": 318, "[\"size\",\"color\"]": 256, "[\"size\",\"count\"]": 369, "[\"size\",\"rotation\"]": 255}

### `shadow_inference_dataset_3000`

**Item:** `shadow_inference_1501.png`

**Exact question:**

> Compare each object with the shadow it casts on the ground: say from which general direction the light is coming, and whether it sits high in the sky or low near the horizon. State your conclusion, justify it by describing the direction the shadows fall and how their length compares with the height of the objects casting them, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `light_direction`: `west`
- `light_height`: `high`

**Written derivation:**

1. The stored light azimuth is 310.672 degrees in the 0=front, 90=right convention; its westward component dominates, giving west.
2. The elevation is 53.026 degrees, above the 45-degree high/low threshold, giving high.

**Visual recoverability:** Read shadow direction opposite the light and compare shadow length with object height. Direction and elevation class are inferred from visible shadows.

**Derivable redundancy:** Azimuth bucket and elevation bucket are independently sampled.

**Nearest-alternative margin:** No candidate or numerical extreme is selected.

**Answer distributions and baselines:**

- `light_direction`: baseline 0.453; distribution {"east": 1358, "north": 143, "south": 146, "west": 1353}
- `light_height`: baseline 0.505; distribution {"high": 1514, "low": 1486}

### `surface_topology_dataset_3000`

**Item:** `surface_topology_1501.png`

**Exact question:**

> Examine the surface and trace how it closes back on itself: count how many holes or handles it has and decide whether it is orientable. State your conclusion, justify it by describing the feature that fixes the genus and whether the surface has a consistent inside and outside, and end with a confidence score from 0 to 1.

**Stored sub-facts:**

- `genus`: `2`
- `orientability`: `orientable`

**Written derivation:**

1. The rendered closed surface has two distinct handles, so genus is 2.
2. It has no twist or cross-cap and retains a consistent inside and outside, so it is orientable.

**Visual recoverability:** Count visible handles and inspect whether the surface contains a one-sided twist. Orientability is inferred from topology rather than printed.

**Derivable redundancy:** The former Euler field was determined by genus and orientability for all 3,000 closed surfaces and was removed.

**Nearest-alternative margin:** No candidate or numerical extreme is selected.

**Answer distributions and baselines:**

- `genus`: baseline 0.273; distribution {"0": 755, "1": 820, "2": 675, "3": 750}
- `orientability`: baseline 0.750; distribution {"non-orientable": 750, "orientable": 2250}


## Validation summary

- Independent ground-truth mismatches: 0.
- Deterministic sub-fact dependency violations: 0.
- Quantity-aware PNG recovery: 100,000/100,000 included images. Every per-domain metrics file states the image signal used for every sub-fact.
- Exact prompt wording, three-column public schema, answer-leak checks, numeric tolerances, and one-to-one resolution: PASS in all 34 domains.
- Combined open files: 100,000 questions and 100,000 answers; 100,000 image paths resolve.
- Full answer distributions and constant-answer baselines are retained in each `open_validation_metrics.json` and the consolidated JSON report.
