# Open-question specification implementation report

## Per-domain validation and coverage

| Dataset | Version | Source | Included | Excluded | Exclusion reason(s) | Highest baseline | Result |
|---|---|---:|---:|---:|---|---:|---|
| `angle_estimation_dataset_3000` | `angle-estimation-8.0.0` | 3,000 | 3,000 | 0 | none | 0.501 | PASS |
| `clock_reading_dataset_3000` | `clock-reading-4.0.0` | 3,000 | 3,000 | 0 | none | 0.040 | PASS |
| `combination3d_dataset_3000` | `combination3d-5.0.0` | 3,000 | 3,000 | 0 | none | 0.353 | PASS |
| `combination_dataset_3000` | `combination-4.0.0` | 3,000 | 3,000 | 0 | none | 0.351 | PASS |
| `compass_bearing_dataset_3000` | `compass-bearing-5.0.0` | 3,000 | 1,118 | 1,882 | closest_pair_bearing_within_15_degrees_of_sector_boundary: 1882 | 0.260 | PASS |
| `coordinate_geometry_dataset_3000` | `coordinate-geometry-7.0.0` | 3,000 | 3,000 | 0 | none | 0.531 | PASS |
| `cube_net_dataset_3000` | `cube-net-5.0.0` | 3,000 | 3,000 | 0 | none | 0.178 | PASS |
| `cube_structure_dataset_3000` | `cube-structure-6.0.0` | 3,000 | 3,000 | 0 | none | 0.333 | PASS |
| `depth_height_dataset_3000` | `depth-height-6.0.0` | 3,000 | 3,000 | 0 | none | 0.213 | PASS |
| `embedded_figures_dataset_3000` | `embedded-figures-4.0.0` | 3,000 | 3,000 | 0 | none | 0.250 | PASS |
| `fbd_dataset_3000` | `free-body-diagram-5.0.0` | 3,000 | 3,000 | 0 | none | 0.833 | PASS |
| `fold_punch_dataset_3000` | `fold-punch-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `gauge_reading_dataset_3000` | `gauge-reading-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `gear_train_dataset_3000` | `gear-train-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `hex_pathfinding_dataset_3000` | `hex-pathfinding-6.0.0` | 3,000 | 3,000 | 0 | none | 0.535 | PASS |
| `impossible_object_dataset_3000` | `impossible-object-7.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `laser_mirror_dataset_3000` | `laser-mirror-5.0.0` | 3,000 | 3,000 | 0 | none | 0.697 | PASS |
| `line_intersection_dataset_3000` | `line-intersection-7.0.0` | 3,000 | 3,000 | 0 | none | 0.503 | PASS |
| `nested_hexagons_dataset_3000` | `nested-hexagons-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `nested_squares_dataset_3000` | `nested-squares-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `nested_triangles_dataset_3000` | `nested-triangles-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `occluded_pattern_dataset_3000` | `occluded-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.369 | PASS |
| `optical_illusion_dataset_3000` | `optical-illusion-6.0.0` | 3,000 | 3,000 | 0 | none | 0.512 | PASS |
| `orthographic_dataset_3000` | `orthographic-4.0.0` | 3,000 | 3,000 | 0 | none | 0.561 | PASS |
| `overlap_circles_dataset_3000` | `overlap-circles-6.0.0` | 3,000 | 3,000 | 0 | none | 0.254 | PASS |
| `physical_stability_dataset_3000` | `physical-stability-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |
| `polyhedron_dataset_3000` | `polyhedron-8.0.0` | 3,000 | 3,000 | 0 | none | 0.895 | PASS |
| `projectile_motion_dataset_1000` | `projectile-motion-5.0.0` | 1,000 | 1,000 | 0 | none | 0.507 | PASS |
| `rotation_matching_dataset_3000` | `rotation-matching-5.0.0` | 3,000 | 3,000 | 0 | none | 0.260 | PASS |
| `route_dataset_3000` | `route-6.0.0` | 3,000 | 3,000 | 0 | none | 0.004 | PASS |
| `rpm_dataset_3000` | `rpm-5.0.0` | 3,000 | 3,000 | 0 | none | 0.220 | PASS |
| `shadow_inference_dataset_3000` | `shadow-inference-5.0.0` | 3,000 | 3,000 | 0 | none | 0.505 | PASS |
| `surface_topology_dataset_3000` | `surface-topology-6.0.0` | 3,000 | 3,000 | 0 | none | 0.750 | PASS |
| `symmetry_pattern_dataset_3000` | `symmetry-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | PASS |

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
| `fbd_dataset_3000` | `weight_arrow` | 0.833 | Inherent label convention: the rendered weight arrow is normally labelled W; retained and reported. |
| `laser_mirror_dataset_3000` | `reflection_count` | 0.697 | Inherent among the nonzero-reflection trace variant; zero-reflection scenes now use a separate varying prompt. |
| `polyhedron_dataset_3000` | `convexity` | 0.895 | Inherent to the generated solid inventory after geometry-identity repair; retained and reported. |
| `surface_topology_dataset_3000` | `orientability` | 0.750 | Inherent to the generated surface inventory; retained and reported. |

## Validation summary

- Independent ground-truth mismatches: 0.
- Deterministic sub-fact dependency violations: 0.
- Quantity-aware PNG recovery: 98,118/98,118 included images. Every per-domain metrics file states the image signal used for every sub-fact.
- Exact prompt wording, three-column public schema, answer-leak checks, numeric tolerances, and one-to-one resolution: PASS in all 34 domains.
- Combined open files: 98,118 questions and 98,118 answers; 98,118 image paths resolve.
- Full answer distributions and constant-answer baselines are retained in each `open_validation_metrics.json` and the consolidated JSON report.
