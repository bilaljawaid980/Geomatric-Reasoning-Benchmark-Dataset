# GRIP Physical Stability Dataset 3000

## 1. Overview

This is the second category in GRIP-Benchmark's **Physical/Mechanical Reasoning** family, alongside `gear_train_dataset_3000`. It tests intuitive and analytic understanding of stacked-object stability through cumulative centers of mass rather than judging each block independently.

The motivation is related to Chow et al.'s [PhysBench](https://arxiv.org/abs/2501.16411) (ICLR 2025), which reports broad limitations in VLM physical-world understanding, and Schulze Buschoff et al.'s [*Can Vision Language Models Learn Intuitive Physics from Interaction?*](https://arxiv.org/abs/2602.06033), which studies learning and generalization in block-tower construction and stability tasks. These are third-party works cited as context; the authors are not affiliated with this dataset.

## 2. Contents

- 3,000 deterministic 600 x 600 PNG diagrams
- 15,000 questions, exactly five ordered difficulty levels per image
- Exact block dimensions, positions, area-derived masses, joint moments, and answers in `annotations.jsonl`
- Public `question_set.csv` separated from private `answer_key.csv`
- Flattened CSV/JSONL, validation report, statistics, contact sheet, and human-calibration sheet

## 3. Five-level question design

1. **Simple Description:** count the blocks.
2. **Basic Relational:** compare one block's center with its support.
3. **Comparative/Structural:** find the block with the largest support-relative offset.
4. **Compound Reasoning:** determine whole-stack stability and the lowest failing joint.
5. **Extrapolative/Counterfactual:** remove the top block and recompute every remaining joint.

Four constructive scene families are exactly balanced at 750 images each: stable/remains stable, stable/becomes unstable after counterweight removal, unstable/becomes stable, and unstable/remains unstable. This provides a 50/50 split before and after removal without rejection-sampling on answers.

## 4. Generation

```powershell
python generate_physical_stability_dataset.py --sample
python generate_physical_stability_dataset.py --count 3000
python generate_physical_stability_dataset.py --count 3000 --metadata-only
python flatten_annotations.py annotations.jsonl
python make_stats.py
python make_contact_sheet.py
```

Blocks are ordered bottom-to-top and labeled A, B, C, and so on. Mass equals rectangle area. For every interface, the combined horizontal center of mass of all blocks above that interface is computed using an exact weighted average.

## 5. Independent validation

```powershell
python validate_physical_stability_dataset.py
pytest -q
```

The validator independently reconstructs block masses, geometric centers, vertical contact, horizontal overlap, cumulative moments, support intervals, lowest failure, top-removal stability, and all five answers. It also reads every final PNG, recovers the block rectangles from their pixels, checks their count/bounds/fill area/center-of-mass markers against the stored geometry, and compares all 15,000 rows across annotations, public questions, private answers, and flattened outputs.

## 6. Reasoning skills

- Uniform-density center-of-mass reasoning
- Cumulative weighted-average calculations
- Support-polygon and tipping-point analysis
- Multi-interface structural stability
- Counterfactual re-evaluation after removing a component

## 7. Limitations

Only rigid rectangular blocks are modeled. Density is uniform and material is shared, so mass is proportional to 2D area. The task considers planar tipping only, not perpendicular 3D toppling. Friction failure, sliding, deformation, impact dynamics, irregular bodies, and uncertain contact are outside scope.

This repository contains generation data and ground truth only. It includes no model inference, evaluation, scoring, or benchmark runner.

### Supplementary open-ended questions

Version `physical-stability-4.0.0` replaces the supplementary free-response set with the exact domain template in `OPEN_QUESTION_SPEC.md`. It includes `3000` eligible items and excludes `0` under `{}`. Every prompt uses visible evidence, asks for justification, and ends with a confidence score from 0 to 1.

- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.
- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.
- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.
- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.

Scored fields at or above 60% after template revision: `{}`. Targeted fields: `stability_conclusion`. Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.
