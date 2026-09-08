# Open-question specification implementation report

## Pre-change defect findings

- `fold_punch`: 312 of 3,000 items had identical L4 and L5 question text and the identical `exactly half` answer. L5 was replaced only on those rows with the existing additional-fold counterfactual; all 3,000 L5 rows are now distinct from L4.
- `overlap_circles`: 1,034 of 3,000 L3 rows stored the field name `target_density`. Those answers are now `spread` for target overlap densities 0.28/0.34 and `clustered` for 0.40/0.46/0.52.
- `symmetry_pattern_0143`: no stored or rendered six-shape defect was present. The record has eight visible shapes in two complete 4-fold orbits. Across all 1,500 intact patterns, zero shape counts violate divisibility by rotational order. The permanent validator now asserts this invariant.

## Per-domain validation and exclusions

| Dataset | Version | Source | Included | Excluded | Exclusion reason(s) | Highest sub-fact baseline | Fields at or above 60% | Result |
|---|---|---:|---:|---:|---|---:|---|---|
| `angle_estimation_dataset_3000` | `angle-estimation-7.0.0` | 3,000 | 3,000 | 0 | none | 0.748 | largest_angle_vertex: 0.748 | PASS |
| `clock_reading_dataset_3000` | `clock-reading-4.0.0` | 3,000 | 3,000 | 0 | none | 0.040 | none | PASS |
| `combination3d_dataset_3000` | `combination3d-5.0.0` | 3,000 | 3,000 | 0 | none | 0.353 | none | PASS |
| `combination_dataset_3000` | `combination-4.0.0` | 3,000 | 3,000 | 0 | none | 0.351 | none | PASS |
| `compass_bearing_dataset_3000` | `compass-bearing-5.0.0` | 3,000 | 1,118 | 1,882 | closest_pair_bearing_within_15_degrees_of_sector_boundary: 1882 | 0.260 | none | PASS |
| `coordinate_geometry_dataset_3000` | `coordinate-geometry-5.0.0` | 3,000 | 3,000 | 0 | none | 0.649 | relation_to_10: 0.649 | PASS |
| `cube_net_dataset_3000` | `cube-net-5.0.0` | 3,000 | 3,000 | 0 | none | 0.178 | none | PASS |
| `cube_structure_dataset_3000` | `cube-structure-5.0.0` | 3,000 | 3,000 | 0 | none | 0.333 | none | PASS |
| `depth_height_dataset_3000` | `depth-height-5.0.0` | 3,000 | 1,500 | 1,500 | not_depth_ordering_scene: 1500 | 0.209 | none | PASS |
| `embedded_figures_dataset_3000` | `embedded-figures-4.0.0` | 3,000 | 3,000 | 0 | none | 0.250 | none | PASS |
| `fbd_dataset_3000` | `free-body-diagram-5.0.0` | 3,000 | 3,000 | 0 | none | 0.833 | weight_arrow: 0.833 | PASS |
| `fold_punch_dataset_3000` | `fold-punch-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `gauge_reading_dataset_3000` | `gauge-reading-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `gear_train_dataset_3000` | `gear-train-4.0.0` | 3,000 | 3,000 | 0 | none | 0.618 | last_direction_relation: 0.618 | PASS |
| `hex_pathfinding_dataset_3000` | `hex-pathfinding-5.0.0` | 3,000 | 3,000 | 0 | none | 0.535 | none | PASS |
| `impossible_object_dataset_3000` | `impossible-object-7.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `laser_mirror_dataset_3000` | `laser-mirror-4.0.0` | 3,000 | 2,250 | 750 | zero_reflections: 750 | 0.697 | reflection_count: 0.697 | PASS |
| `line_intersection_dataset_3000` | `line-intersection-6.0.0` | 3,000 | 3,000 | 0 | none | 0.588 | none | PASS |
| `nested_hexagons_dataset_3000` | `nested-hexagons-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `nested_squares_dataset_3000` | `nested-squares-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `nested_triangles_dataset_3000` | `nested-triangles-11.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `occluded_pattern_dataset_3000` | `occluded-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.369 | none | PASS |
| `optical_illusion_dataset_3000` | `optical-illusion-6.0.0` | 3,000 | 3,000 | 0 | none | 0.512 | none | PASS |
| `orthographic_dataset_3000` | `orthographic-4.0.0` | 3,000 | 3,000 | 0 | none | 0.561 | none | PASS |
| `overlap_circles_dataset_3000` | `overlap-circles-5.0.0` | 3,000 | 3,000 | 0 | none | 0.720 | any_isolated: 0.720 | PASS |
| `physical_stability_dataset_3000` | `physical-stability-4.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |
| `polyhedron_dataset_3000` | `polyhedron-8.0.0` | 3,000 | 3,000 | 0 | none | 0.895 | convexity: 0.895 | PASS |
| `projectile_motion_dataset_1000` | `projectile-motion-4.0.0` | 1,000 | 1,000 | 0 | none | 0.654 | peak_above_20_m: 0.654 | PASS |
| `rotation_matching_dataset_3000` | `rotation-matching-5.0.0` | 3,000 | 3,000 | 0 | none | 0.260 | none | PASS |
| `route_dataset_3000` | `route-6.0.0` | 3,000 | 3,000 | 0 | none | 0.004 | none | PASS |
| `rpm_dataset_3000` | `rpm-5.0.0` | 3,000 | 3,000 | 0 | none | 0.220 | none | PASS |
| `shadow_inference_dataset_3000` | `shadow-inference-5.0.0` | 3,000 | 3,000 | 0 | none | 0.505 | none | PASS |
| `surface_topology_dataset_3000` | `surface-topology-6.0.0` | 3,000 | 3,000 | 0 | none | 0.750 | orientability: 0.750 | PASS |
| `symmetry_pattern_dataset_3000` | `symmetry-pattern-5.0.0` | 3,000 | 3,000 | 0 | none | 0.500 | none | PASS |

## Coverage audit

- `angle_estimation` scene types: `{"comparison": 1050, "single": 1200, "triangle": 750}`; variant mapping violations: 0.
- `route` endpoint counts: `{"4": 994, "5": 1020, "6": 986}`; chosen targets with degree below 1: 0.
- `compass_bearing`: 1,882 exclusions, all from the 15-degree sector-boundary ambiguity guard; other reasons: 0.
- `depth_height`: 1,500 stack-height exclusions because those scenes have no depth cues; template-failure exclusions: 0.
- `laser_mirror`: 750 exclusions, all zero-reflection items; other reasons: 0.

A stack-height prompt exists for later review and was not generated in this pass:

> Compare the coloured stacks by counting the visible blocks from the common baseline upward: rank every stack from shortest to tallest by colour, and name which one is tallest. State your conclusion, justify it by describing how you counted the blocks in each stack, and end with a confidence score from 0 to 1.

## Validation summary

- Independent ground-truth mismatches: 0.
- PNG/file recovery: 95,868/95,868 included images.
- Public schema: exactly `question_id,image,prompt` in every domain.
- Exact template wording, answer-leak checks, rendered-vocabulary checks, numeric tolerance checks, and one-to-one question/answer resolution: PASS in all 34 domains.
- Combined open files: 95,868 questions and 95,868 answers; 95,868 referenced image paths resolve.
- Gauge exact-tick frequency and every complete answer distribution/baseline are retained in the per-domain `open_validation_metrics.json` files and the consolidated JSON report.
- Closed combined suite remains 500,000 questions, 500,000 answers, and 100,000 images.
