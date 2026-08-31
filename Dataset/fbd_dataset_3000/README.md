# GRIP Free Body Diagram Dataset 3000

Current version: `free-body-diagram-2.0.0`; the initial build is preserved under `archive/v1/`. V2 stores explicit `physical_frame`, `rendered_frame`, and `question_frame_policy` declarations. All 750 `wrong_diagram` items explicitly separate drawn-arrow judgments from physically correct calculations in both Levels 3 and 4.

Level 3 answer formatting uses structured tie groups and accepts any ordering within a tied group. The maximum tie-group-size distribution is: size 1 for 1,624 items, size 2 for 1,001, size 3 for 125, and size 4 for 250; thus fully tied four-force rankings occur in 250/3,000 items and do not dominate the dataset. PNG validation recovers the count and direction of every shown arrow in all 3,000 images.

## 1. Dataset overview

This is the third Physical/Mechanical Reasoning category in GRIP-Benchmark, following gear trains and physical stability. It contains 3,000 deterministic free-body-diagram images and 15,000 questions covering force identification, vector comparison, equilibrium, Newton’s second law, physical error/omission detection, and counterfactual force analysis.

The `wrong_diagram` preset parallels the global-consistency skill in `impossible_object_dataset_3000`, but applies it to mechanics rather than pure geometry. Images are synthetic and generated from exact physics parameters with `random.Random(image_index)`.

## 2. Visual scenarios and presets

Six scenario types are balanced at 500 images each:

- block on an incline;
- hanging mass;
- Atwood machine;
- block pushed against a wall;
- mass in an elevator;
- car on a banked curve.

Four presets are balanced at 750 images each: `equilibrium`, `accelerating`, `missing_force`, and `wrong_diagram`. Every record separates the complete physically correct `forces` list from `shown_forces`, the exact list rendered in the PNG. Missing and wrong diagrams therefore never overwrite the physical source of truth.

Force directions use 0° = right and 90° = up. Arrow lengths share one per-image Newton-to-pixel scale and are exactly proportional to shown magnitude. Weight, normal, friction, tension, applied force, and drag have fixed visual encodings on an off-white `#FDFAF4` background.

## 3. Five-level question structure

1. **Simple Description:** count rendered force arrows.
2. **Basic Relational:** identify a force’s arrow label; missing-force items also identify the omitted force.
3. **Comparative/Structural:** rank shown magnitudes, check shown vertical balance, and judge physical equilibrium.
4. **Compound Reasoning:** compute physical net force plus a scenario-specific derived quantity; wrong-diagram items also identify and explain the invalid arrow.
5. **Extrapolative/Counterfactual:** recompute direction after removing a force, or test whether an incline block would slip at 40°.

The original design contained ten question points: arrow count, downward-force identification, magnitude ranking, net force, friction/tension identification, vertical balance, equilibrium, removed-force direction, scenario-derived calculation, and incline-angle counterfactual. They were condensed respectively into Levels 1; 2; 3; 4; and 5 so the dataset follows GRIP’s unified five-level rubric without discarding those reasoning checks.

## 4. Physics and ground truth

Per-scenario solvers implement:

- incline decomposition using `mg sin(theta)`, `mg cos(theta)`, applied force, and friction;
- hanging-mass tension from `T = m(g-a)`;
- Atwood tension `T = 2 m1 m2 g / (m1+m2)`;
- wall normal equal to horizontal applied force and friction constrained by `mu*N`;
- elevator support force `N = m(g+a)`;
- banked-curve radial/vertical resolution, including the direction of required friction.

Each annotation stores physical parameters, correct forces, shown forces, physical and shown net vectors, acceleration, equilibrium, missing-force identity, wrong-force details, scenario-specific derived quantities, and five ground-truth questions.

## 5. Numeric-tolerance schema

Level 4 introduces GRIP’s first structured real-valued grading declaration:

```json
{"type":"numeric_tolerance","tolerance_percent":2}
```

This is private scoring metadata stored in `annotations.jsonl` and `answer_key.csv`. It is absent from public `question_set.csv`. The prompt asks for the physical values, while downstream scoring may accept answers within 2% of independently recomputed ground truth.

## 6. Independent validation and files

`validate_fbd_dataset.py` has independent per-scenario equations and does not import generation-time solvers. It recomputes every true force, reconstructs each controlled missing/wrong variant, vector-sums net force, re-derives acceleration and all five answers, verifies that omissions are physically required and wrong arrows genuinely invalid, checks exact 500/750 scenario/preset balance, validates public/private CSV separation, and probes every rendered arrow’s color, direction, and proportional length directly in the saved PNG.

Files:

- `images/fbd_0001.png` through `images/fbd_3000.png`
- `annotations.jsonl`
- `dataset_final.csv` and `dataset_final.jsonl`
- public `question_set.csv`
- private `answer_key.csv`
- `validation_report.txt`, `generation_stats.json`, `stats.md`
- `contact_sheet.png`, `review_sheet.png`, and `sample_test/`

Commands:

```powershell
python generate_fbd_dataset.py
python flatten_annotations.py
python validate_fbd_dataset.py
python make_artifacts.py
python -m pytest tests -q
python generate_fbd_dataset.py --sample
```

## 7. Known limitations

- Only six scenario families are represented.
- Forces are limited to weight, normal, friction, tension, applied force, and optional drag vocabulary.
- Diagrams use idealized point-mass/rigid-body introductory mechanics rather than deformation, torque, or fluid dynamics.
- Banked-curve equilibrium scenes represent a parked body; moving banked-curve scenes correctly retain centripetal acceleration.
- Real-valued Level 4 answers require 2% tolerance rather than exact-string grading.
- Missing and wrong diagrams are deliberately diagnostic and should not be treated as measurements of naturally occurring diagram error frequency.
