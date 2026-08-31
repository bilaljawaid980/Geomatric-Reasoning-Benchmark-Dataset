# GRIP 3D Combination Dataset 3000 — v2

Version `combination3d-2.0.0` contains 3,000 dark-theme voxel-assembly images and 15,000 questions. Each target has 8–14 cubes and four candidate piece sets: one valid z-spin assembly, one full-rotation-resistant gap/overlap near miss, one wrong-count set, and one set that succeeds only after a 3D tumble.

## Explicit coordinate convention

The dataset uses a right-handed `(x,y,z)` voxel frame. The isometric renderer maps:

```text
screen_x = 0.8660254 * (x - y)
screen_y = 0.5 * (x + y) - z
```

Therefore **z is the visual vertical axis**: increasing z moves a cube upward on screen. `max_height_layers` is the inclusive z extent, and the permitted “rotation around the vertical axis” in Levels 2 and 5 is a z-axis rotation. Every record stores `vertical_axis: "z"`, `coordinate_frame`, `renderer_projection`, and `permitted_piece_rotation_axes: ["z"]` so the convention cannot drift.

Manual-review item `combination3d_0017` has y extent 3 and z extent 4; its stored height 4 is correct because the renderer and questions both use z. Across the previous build, zero Level 4 count-and-height answers were wrong.

## Five questions

1. Count target cubes.
2. Select the candidate that tiles the target using translation and z-axis spins only.
3. Compare piece count or cube total.
4. Identify a failure class or combine total count with z-height.
5. Apply a whole-structure z rotation or add a cube above the highest z layer.

## Exhaustive validation

The validator independently enumerates four z-axis orientations and all 24 proper cube orientations, searches translations and non-overlapping exact covers, and confirms for every item that exactly one candidate succeeds under the permitted transform set. It also independently verifies all four failure reasons. Final results: zero correct-candidate failures, zero successful distractors, and zero failure-reason mismatches.

Every final PNG is checked for target presence, exact candidate piece-panel recovery, canvas dimensions, and the structure signature needed by cube count, piece count, and z-height questions. The report also includes all five answer distributions and constant baselines, the unfiltered stored-feature leak audit, full parameter distributions, reference-frame audit, and guard injection tests. The final v2 build passes 3,000 images and 15,000 questions with zero mismatches.

The superseded metadata and reports are under `archive/v1/`; the unchanged image renderer is shared by the builds.

## Commands

```text
python generate_combination3d_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python validate_combination3d_dataset.py --dataset-dir .
```
## Public evaluation and feature classification

`question_set.csv` is the only model-facing file and contains exactly `question_id`, `task`, `image`, and `prompt`. The remaining tabular files are private answer-key-side artifacts; do not expose `annotations.jsonl` to a tested model.

`target_cube_count` and the z-derived target height are definitional for Level 4, which explicitly asks for target count and height. They are non-definitional for Level 5 rotation-invariance answers. Their bias-corrected Cramér's V values against Level 5 are 0.8084 and 0.8104 respectively, but both values live only in private answer-key-side annotations and never appear in `question_set.csv`. The complete post-cleanup matrix is recorded in the suite-level `release_hygiene_audit.json`.
