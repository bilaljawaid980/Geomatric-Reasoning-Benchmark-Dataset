# Fold and Punch Dataset (3,000 images)

## 1. Dataset purpose

This dataset implements the classic **Fold and Punch** spatial-visualization test catalogued by Huang et al. in *Spatial-DISE: A Unified Benchmark for Evaluating Spatial Reasoning in Vision-Language Models*, [arXiv:2510.13394](https://arxiv.org/abs/2510.13394). It tests sequential 2D reflection and layered-state tracking. It is distinct from `cube_net_dataset_3000`, which folds a 2D net into 3D, and `rotation_matching_dataset_3000`, which rotates whole 2D figures without folding.

## 2. Visual design

Each 550–650 × 400–450 PNG has a dark `#1A1A1A` background. Two or three fold diagrams appear across the top with dashed center lines and directional arrows, followed by the folded paper and punch dot. Four labeled full-sheet patterns appear below. Paper and marks use one consistent neutral technical-diagram palette.

## 3. Exact simulation and reasoning skills

The generator represents the original sheet as `[0,1] × [0,1]`. `FoldState` maintains current bounds and an affine inverse transform for every stacked layer. Each center-bisecting fold doubles the transforms. Applying every transform to the final punch yields exactly `2^num_folds` unfolded holes.

The task tests sequential transformation tracking, layered-state simulation, reflection symmetry, geometric doubling, and discrimination between correct and plausible hole patterns.

## 4. Candidates, questions, and annotations

Every image contains exactly one correct candidate and three verified distractors:

- a different hole count;
- the correct count and reflection symmetries but different positions;
- the correct count but a deliberately broken required symmetry.

`annotations.jsonl` stores the fold sequence, absolute folded punch coordinate, final bounds, exact unfolded positions, candidates, answer, seed, and four ordered questions. `dataset_final.csv` and `dataset_final.jsonl` provide 12,000 flattened question rows.

## 5. Generation and reproducibility

Python 3 and Pillow are required. Image `i` uses `random.Random(i)`.

```powershell
python generate_fold_punch_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python make_contact_sheet.py --dataset-dir . --output contact_sheet.png --count 20 --columns 4
python make_contact_sheet.py --dataset-dir . --output human_calibration/review_sheet.png --count 5 --columns 5
```

Use `--sample` for a five-image development set.

To redraw PNGs from existing annotations without changing any metadata or ground truth:

```powershell
python generate_fold_punch_dataset.py --rerender-only --output-dir .
```

## 6. Validation

```powershell
python validate_fold_punch_dataset.py --dataset-dir . --report validation_report.txt
```

The validator does not import the generator. It independently derives every intermediate fold bound, reverses the fold sequence to reproduce all original punch coordinates, enforces the power-of-two count, verifies distractor count/position/symmetry claims, recomputes every question answer, audits answer and fold-count balance, and reads every PNG. Its PNG check counts dark connected components inside each candidate sheet and checks a rendered dot at every annotated coordinate.

## 7. Known limitations

Folds are restricted to horizontal or vertical center bisectors, so every fold uniformly doubles coverage and the hole count is always a power of two. Each puzzle has only 2–3 folds and one punch. Diagonal and off-center folds, partial folds, thick-paper effects, and multiple punches are not represented.
# v2 distractor correction

`wrong_symmetry` now means a complete pattern reflected about explicitly wrong fold axes. It is not a small coordinate perturbation. The validator checks the structural symmetry violation, candidate semantics, rendered dot recovery, and the 0.04 normalized-sheet minimum displacement.
