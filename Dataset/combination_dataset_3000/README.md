# 2D Combination Dataset (3,000 images)

## 1. Dataset purpose

This synthetic dataset implements the **2D Combination** task in the Spatial-DISE taxonomy. It tests part-whole spatial composition: mentally rotating and placing smaller pieces to reconstruct a target. This differs from transformation matching, which compares whole shapes, and cube-net folding, which requires 2D-to-3D reasoning. The taxonomy reference is Huang et al., *Spatial-DISE: A Unified Benchmark for Evaluating Spatial Reasoning in Vision-Language Models*, [arXiv:2510.13394](https://arxiv.org/abs/2510.13394).

## 2. Visual design

Each 550–600 × 400–450 PNG uses a dark `#1A1A1A` background and one light outline color. A connected 6–10-cell target appears above four labeled candidate sets. Visible unit-cell boundaries make area and piece shape inspectable without color hints. Each candidate contains 2–4 connected polyomino pieces.

## 3. Candidate construction and reasoning skills

Every image has exactly one rotation-and-translation solution and exactly three verified distractors:

- equal area but no exact cover, even when reflection is allowed;
- wrong total area;
- equal area and solvable with reflection, but not with rotation alone.

The tasks exercise part-whole composition, mental piece rotation and placement, area-based elimination, and rejection of plausible mirrored or non-fitting assemblies.

## 4. Questions and annotations

`annotations.jsonl` contains one record per image with `target_cells`, `target_cell_count`, four candidate piece sets, failure reasons, the correct choice, seed, canvas size, and four ordered questions:

1. target cell count;
2. the core exact-assembly choice;
3. candidate piece count or candidate/target area comparison;
4. reflection distractor, wrong-area distractor, or attached-cell connectivity.

The flattened `dataset_final.csv` and `dataset_final.jsonl` contain exactly 12,000 question rows using columns `task`, `image`, `prompt`, `groundtruth`, and compact `metadata`.

## 5. Generation and reproducibility

Python 3 and Pillow are required. Image `i` uses `random.Random(i)`, so generation is reproducible.

```powershell
python generate_combination_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python make_contact_sheet.py --dataset-dir . --output contact_sheet.png --count 20
python make_contact_sheet.py --dataset-dir . --output human_calibration/review_sheet.png --count 5 --columns 5
```

For a five-image development run, use `python generate_combination_dataset.py --sample --output-dir sample_output`.

## 6. Validation

Run:

```powershell
python validate_combination_dataset.py --dataset-dir . --report validation_report.txt
```

The validator is independent of the generator. It reconstructs rotations, reflections, translations, and exact-cover search; checks each declared failure reason; recomputes all question answers; verifies A/B/C/D answer balance; confirms files and sizes; and reads every PNG to check that expected target and piece cell boundaries were actually rendered. A successful full run reports zero mismatches.

## 7. Known limitations

Shapes are restricted to unit-grid polyominoes for exact verification rather than free-form polygons. Candidate sets contain only 2–4 pieces. Reflection is strictly invalid for the core question, with no partial credit for an almost-correct mirrored construction. The images test spatial composition but do not model physical thickness, material, or real-world assembly constraints.
