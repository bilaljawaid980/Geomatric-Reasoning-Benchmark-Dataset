# GRIP Gear Train Dataset 3000

## 1. Overview

This dataset is GRIP-Benchmark's first **Physical/Mechanical Reasoning** category. It complements the suite's geometric and spatial categories by testing causal propagation through an external-gear mechanism: rotation direction, angular-speed ratios, multi-step transmission, and component-change counterfactuals.

The mechanical rules are standard: meshed external gears rotate in opposite directions, and their angular speeds are inversely proportional to tooth count. Broader motivation comes from recent interest in physical reasoning for vision-language models, including PhysBench (ICLR 2025) and PhysVLM (arXiv:2503.08481). These works are related context and are not authored by this dataset's creator.

## 2. Contents

- 3,000 deterministic 600 x 600 PNG images
- 15,000 questions: exactly five ordered difficulty levels per image
- `annotations.jsonl`: full graph, tooth counts, input state, exact computed rotations, and answers
- `question_set.csv`: public questions without ground truth
- `answer_key.csv`: private question/answer key
- `dataset_final.csv` and `dataset_final.jsonl`: flattened research tables
- `validation_report.txt`, `stats.md`, contact sheet, and human-calibration sheet

## 3. Five-level question design

1. **Simple Description:** count the gears.
2. **Basic Relational:** infer the direction of a gear directly meshed with the driver.
3. **Comparative/Structural:** identify the largest-tooth or fastest gear.
4. **Compound Reasoning:** propagate exact RPM across two or more meshes.
5. **Extrapolative/Counterfactual:** double one selected gear's tooth count and recompute the chosen output's speed and direction.

For Level 5, the changed gear may be the driver, target, an intermediate gear, or an off-path branch. The complete modified graph is recomputed; answers are not assigned from a fixed heuristic. Scenario parameters intentionally yield 1,000 increase, 1,000 decrease, and 1,000 unchanged answers without rejection-sampling on the answer.

## 4. Generation

```powershell
python generate_gear_train_dataset.py --sample
python generate_gear_train_dataset.py --count 3000
python generate_gear_train_dataset.py --count 3000 --metadata-only
python flatten_annotations.py annotations.jsonl
python make_stats.py
python make_contact_sheet.py
```

Each image uses `random.Random(image_index)`. Gear meshes form a connected tree, which avoids physically inconsistent odd external-gear cycles. Tooth counts are unique integers from 8 through 40, and visual radius is proportional to tooth count.

## 5. Independent validation

```powershell
python validate_gear_train_dataset.py
pytest -q
```

The validator reconstructs the mesh graph and performs its own BFS from the driver. It independently re-derives every gear direction and exact fractional RPM, verifies each mesh relation and branch, re-derives all five answers, checks PNG integrity, checks the 70/30 arrangement distribution, and audits flattened row counts.

## 6. Reasoning skills

- Mechanical direction propagation through external meshes
- Inverse tooth-count ratio calculation
- Multi-step causal and ratio chaining
- Structural comparison across the complete train
- Counterfactual intervention on a component

## 7. Limitations

The images are clean 2D schematics rather than photorealistic mechanisms. Trains contain 3-5 gears so every Level 4 target can be at least two meshes from the driver. Branches use one idler driving two outputs. Planetary, internal, helical, bevel, compound-shaft, backlash, torque, slip, and dynamic-load effects are outside the current scope.

This repository contains generation data and ground truth only. It includes no model inference, evaluation, scoring, or benchmark runner.

### Supplementary open-ended questions

Version `gear-train-3.0.0` rewrites the one parameterized free-response question per image without changing any image or existing five-level question or answer. Each plain-English prompt scores at most three visible sub-facts, does not name its own reasoning trap, requires a brief visual justification, and ends with a confidence score from 0 to 1.

- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.
- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.
- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.
- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.

The composite acceptance-set baseline is `0.009333`. Scored fields at or above 60% after template revision: `{}`. Targeted fields: `rotation_direction, speed_rpm_nearest_whole`. Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.
