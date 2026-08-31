# GRIP Rotation Matching Dataset 3000 — v2

Version `rotation-matching-2.0.0` contains 3,000 dark-theme 2D mental-rotation puzzles and 15,000 questions. It replaces the previous distorted foils with congruent rigid transformations so edge-length comparison cannot solve the task.

## v2 candidate design

Every item contains exactly:

- one `target_rotation` at the stated target angle;
- two `wrong_angle_rotation` candidates at other allowed angles;
- one congruent `reflection`.

All angles are sampled directly from `45, 90, 135, 180, 225, 270, 315`; no continuous sampling or rounding is used. Each wrong angle differs from the target by at least 45°. `distorted` no longer appears. Because three candidates are now valid rigid rotations in the broad geometric sense, Level 2 explicitly asks for the candidate rotated by the stated target angle.

The stored frame is `image_plane_clockwise_degrees`. Positive mathematical rotation becomes clockwise after mapping centered coordinates to the image's downward-positive y axis.

## Vertex legibility guard

Reference figures have 5–8 vertices. Generation rejects figures with an exterior direction change below 25° at any vertex, an edge below the 0.32 normalized floor, or rotational/reflection symmetry within the 0.08 set-distance guard. The 25° threshold was calibrated above the requested 20° starting point. Across v2, 19,217 rejected reference proposals were resampled before 3,000 accepted scenes.

The validator checks every expected corner directly in the final PNG and confirms every candidate is congruent to the reference. Final PNG recovery is 3,000/3,000.

## Five questions

1. Count visibly recoverable reference vertices.
2. Select the candidate at the explicitly stated target angle.
3. Recover the exact discrete angle of a specified rigid candidate.
4. Identify the sole reflection.
5. Add 90° to the target rotation and normalize the result.

Level 5 is deliberately label-free. An intermediate design referenced a wrong-angle candidate, but its candidate label necessarily excluded both the target and reflection labels and retained Cramér's V near 0.334. The released question instead operates on the target angle itself; measured L2/L5 and L4/L5 associations are reported in `validation_metrics.json`.

## Validation and reporting

`validate_rotation_dataset.py` independently fits orientation-preserving and reflected transforms, verifies all raw angles and the 45° distractor separation, checks PNG corners for the reference and all candidates, re-derives all five answers, and runs the full leak/distribution/guard audit. The released v2 build passes 3,000 images and 15,000 questions with zero mismatches.

The superseded complete v1 build, including its original PNGs, is preserved under `archive/v1/`. Background, dimensions, palette, and line-art style are unchanged.

## Commands

```text
python generate_rotation_matching_dataset.py --n 3000 --output-dir .
python flatten_annotations.py annotations.jsonl
python validate_rotation_dataset.py .
```
