# Qualitative export: data-defect check

This is a report-only audit. No dataset, result, prompt, answer key, or image was modified.

## L4/L5 exact-text comparison

The table compares the full stored L4 and L5 prompt text for every image in each domain's `question_set.csv`.

| Domain | L4/L5 identical? | Affected images | Images compared |
|---|---:|---:|---:|
| `angle_estimation` | no | 0 | 3,000 |
| `clock_reading` | no | 0 | 3,000 |
| `combination3d` | no | 0 | 3,000 |
| `combination` | no | 0 | 3,000 |
| `compass_bearing` | no | 0 | 3,000 |
| `coordinate_geometry` | no | 0 | 3,000 |
| `cube_net` | no | 0 | 3,000 |
| `cube_structure` | no | 0 | 3,000 |
| `depth_height` | no | 0 | 3,000 |
| `embedded_figures` | no | 0 | 3,000 |
| `fbd` | no | 0 | 3,000 |
| `fold_punch` | no | 0 | 3,000 |
| `gauge_reading` | no | 0 | 3,000 |
| `gear_train` | no | 0 | 3,000 |
| `hex_pathfinding` | no | 0 | 3,000 |
| `impossible_object` | no | 0 | 3,000 |
| `laser_mirror` | no | 0 | 3,000 |
| `line_intersection` | no | 0 | 3,000 |
| `nested_hexagons` | no | 0 | 3,000 |
| `nested_squares` | no | 0 | 3,000 |
| `nested_triangles` | no | 0 | 3,000 |
| `occluded_pattern` | no | 0 | 3,000 |
| `optical_illusion` | no | 0 | 3,000 |
| `orthographic` | no | 0 | 3,000 |
| `overlap_circles` | no | 0 | 3,000 |
| `physical_stability` | no | 0 | 3,000 |
| `polyhedron` | no | 0 | 3,000 |
| `projectile_motion` | no | 0 | 1,000 |
| `rotation_matching` | no | 0 | 3,000 |
| `route` | no | 0 | 3,000 |
| `rpm` | no | 0 | 3,000 |
| `shadow_inference` | yes | 627 | 3,000 |
| `surface_topology` | no | 0 | 3,000 |
| `symmetry_pattern` | no | 0 | 3,000 |

## Physical-stability L5 ground truth and strict scoring

- Full-corpus L5 ground truths classified as sentence-valued (>5 whitespace-delimited words): **3,000/3,000 (100.00%)**.
- Strictly correct stored Test-1 L5 responses across evaluated models: **0/500 (0.00%)**.
- The response fraction uses the existing strict comparator and the stored Test-1 evaluation sample; no semantic regrading was applied.
- Sentence-valued keys can penalize semantically compatible paraphrases under exact comparison; this audit reports the exposure without changing scores.
