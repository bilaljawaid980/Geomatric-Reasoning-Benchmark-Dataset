# GRIP Projectile Motion Dataset 1000

## 1. Overview

This focused Physical/Mechanical Reasoning category contains 1,000 synthetic projectile-motion diagrams and 5,000 questions. It tests classical two-dimensional kinematics with every initial condition explicitly printed on the image. Unlike ambiguous sports photographs, each diagram supplies the scale, speed, and launch angle needed for exact ground truth. It is intentionally smaller than the 3,000-image core categories.

## 2. Visual design

Images use 550–650 px by 400–450 px off-white canvases. Each shows a labeled launch vector, ground line, mathematically sampled dashed trajectory, peak marker, and landing flag. Exactly 300 images include a labeled rectangular obstacle. The renderer scales meters to pixels only for presentation; stored physical quantities remain unchanged.

## 3. Physics and ground truth

The generator assumes level-ground launch and landing, no air resistance, and constant gravity `g = 9.8 m/s²`. Speed is sampled from 10–40 m/s and angle from 15–75°. It computes flight time, maximum height, range, velocity components, peak position, and—when present—trajectory height at the wall from the standard projectile equations.

## 4. Unified five-level questions

1. Read the explicitly labeled launch angle.
2. Determine whether maximum height exceeds 20 m.
3. Compute the horizontal location of the peak.
4. Compute total flight time and range, with a private 2% numeric tolerance.
5. Determine obstacle clearance/collision, or recompute how a 45° launch changes range.

## 5. Files and usage

- `generate_projectile_motion_dataset.py`: deterministic generator and renderer
- `annotations.jsonl`: complete answer-key-side physics and questions
- `dataset_final.csv` / `.jsonl`: flattened research tables
- `question_set.csv`: public model-facing prompts only
- `answer_key.csv`: private scoring answers
- `validate_projectile_motion_dataset.py`: independent physics recomputation
- `contact_sheet.png` and `review_sheet.png`: visual review assets

Run `python generate_projectile_motion_dataset.py`, then `python flatten_annotations.py`, `python validate_projectile_motion_dataset.py`, and `python make_review_sheets.py`. Use `--sample` to render five deterministic examples.

## 6. Validation methodology

The validator independently recomputes all physical quantities directly from stored speed and angle, re-evaluates trajectory height at every obstacle, rebuilds the 45° counterfactual, and reconstructs all five answers. It also checks all 1,000 PNG paths and enforces exactly 5,000 public/private rows. The public `question_set.csv` is asserted to contain only `question_id`, `task`, `image`, and `prompt`.

## 7. Scope and limitations

The benchmark models idealized 2D motion only: no drag, wind, spin, non-level landing, or 3D effects. Obstacles occur in 30% of scenes and are simple rectangles. These constraints make answers exact and independently auditable while testing equation application, time/height/range computation, obstacle clearance, and 45° maximum-range counterfactual reasoning.
