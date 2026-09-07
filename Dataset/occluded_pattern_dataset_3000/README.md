# Occluded Pattern Counting Dataset (3,000 images)

## 1. Dataset purpose

This dataset directly replicates and extends the amodal-counting task introduced by Pothiraj, Stengel-Eskin, Cho, and Bansal in *CAPTURe: Evaluating Spatial Reasoning in Vision Language Models via Occluded Object Counting*, [arXiv:2504.15485](https://arxiv.org/abs/2504.15485). CAPTURe evaluates whether models infer how regular patterns continue through unseen regions. Its reported experiments found higher counting error under occlusion across GPT-4o, InternVL2, Molmo, and Qwen2-VL. The gap was especially large when questions requested only the hidden portion. This dataset scales the controlled synthetic setting to 3,000 images and makes that hidden-only framing the fixed Level 4 task.

## 2. Visual design

Each 450–550 px dark-theme image contains identical objects in one regular arrangement:

- a 3–6 by 3–6 grid;
- 6–14 objects around a circle;
- a triangular arrangement with 3–5 rows.

Objects use one shape and color per image. Half the images use a hatched, visibly bounded occluder; half use a seamless background-colored erasure. Shapes are dots, squares, or triangles.

## 3. Occlusion and solvability

Every occluder hides at least two objects and 15–60% of the complete pattern while leaving at least 40% visible. Glyphs are either fully visible or fully hidden; placements that partially clip a counted object are rejected. Grid occluders cover a contiguous rectangular cell block and preserve complete row/column evidence. Circle and triangle cases retain broad horizontal and vertical pattern evidence.

The reasoning skills are amodal counting, pattern recognition under partial occlusion, spatial extrapolation, and isolation of hidden-region-only count from visible and total counts.

## 4. Annotations and questions

`annotations.jsonl` stores pattern parameters, every object center and occlusion flag, true/visible/hidden counts, occluder bounds and style, visual attributes, seed, and four ordered questions:

1. directly visible count;
2. inferred total count;
3. pattern type;
4. hidden-only count.

`dataset_final.csv` and `dataset_final.jsonl` flatten the data into 12,000 rows with columns `task`, `image`, `prompt`, `groundtruth`, and compact `metadata`.

## 5. Generation and reproducibility

Python 3 and Pillow are required. Image `i` uses `random.Random(i)`.

```powershell
python generate_occluded_pattern_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python make_contact_sheet.py --dataset-dir . --output contact_sheet.png --count 20 --columns 5
python make_contact_sheet.py --dataset-dir . --output human_calibration/review_sheet.png --count 5 --columns 5
```

Use `--sample` to generate five development examples.

## 6. Validation

```powershell
python validate_occluded_pattern_dataset.py --dataset-dir . --report validation_report.txt
```

The independent validator recomputes totals from closed-form formulas, reconstructs every pattern from its parameters, reclassifies every point by geometric containment, verifies all questions, checks inferability constraints and exact dataset balance, and reads every PNG. PNG validation detects color-connected object components, checks every visible/hidden center, and confirms whether the occluder is seamless or visibly distinct.

## 7. Known limitations

The dataset contains three abstract pattern families rather than CAPTURe-real's broader natural-object diversity. It uses one rectangular occluder and one object class per image. The visual style is synthetic line art, and it does not cover irregular, perspective-distorted, multiple-occluder, or photorealistic scenes.

### Supplementary open-ended questions

Version `occluded-pattern-4.0.0` rewrites the one parameterized free-response question per image without changing any image or existing five-level question or answer. Each plain-English prompt scores at most three visible sub-facts, does not name its own reasoning trap, requires a brief visual justification, and ends with a confidence score from 0 to 1.

- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.
- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.
- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.
- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.

The composite acceptance-set baseline is `0.089333`. Scored fields at or above 60% after template revision: `{}`. Targeted fields: `pattern_type, visible_count, hidden_count`. Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.
