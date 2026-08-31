# Angle Estimation Dataset (3,000 images)

## 1. Dataset purpose

This dataset fills a gap in the existing spatial-reasoning suite: no earlier category directly tests angle measurement, despite angle judgment being foundational to classical plane geometry. It covers marked single angles, angle comparison independent of ray length, and triangle-angle classification.

For comparison-scene Level 4, the public rule is explicit: `right` means within 15° of 90°, `straight` means within 15° of 180°, and all other sums are `neither`. Generation keeps sums at least 2° away from either decision boundary and balances these three outcomes.

## 2. Visual design

Every 450–500 px dark-theme image contains one of three scenes. Single scenes show two rays and an orange arc that disambiguates the selected minor or reflex sweep. Comparison scenes place two independently sized angles side by side. Triangle scenes show labeled vertices and marked interior arcs. Thin teal geometry, orange arcs, and coral vertices provide consistent technical-diagram styling.

## 3. Ground-truth construction

All measures are computed from stored coordinates using the dot-product formula `acos((u·v)/(|u||v|))`. Reflex single angles are represented as `360° − minor_angle` and explicitly marked by the long arc. Triangle angles are independently computed at A, B, and C and must sum to 180°. Dataset composition is 40% single, 35% comparison, and 25% triangle; triangle classes are exactly balanced.

The supplied Level 1 single-angle template defines “obtuse” as any marked angle greater than 90°, so reflex marked sweeps follow that benchmark-specific bucket even though classical geometry normally treats reflex as a separate category.

## 4. Questions and outputs

Each image has four ordered questions covering description/classification, core angle estimation or comparison, structural reasoning, and compound/theorem reasoning. `annotations.jsonl` preserves all coordinates and exact measures. `dataset_final.csv` and `dataset_final.jsonl` provide 12,000 flattened rows.

## 5. Generation and reproducibility

Python 3 and Pillow are required. Image `i` uses `random.Random(i)`.

```powershell
python generate_angle_estimation_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python make_contact_sheet.py --dataset-dir . --output contact_sheet.png --count 20 --columns 5
python make_contact_sheet.py --dataset-dir . --output human_calibration/review_sheet.png --count 5 --columns 5
```

Use `--sample` for five varied development examples.

## 6. Validation

```powershell
python validate_angle_dataset.py --dataset-dir . --report validation_report.txt
```

The validator independently recomputes every angle from coordinates, verifies reflex conversion, enforces comparison separation, checks triangle sums/classes/extrema, re-derives every answer, audits distributions, and reads every PNG to sample the expected ray segments, marked arc sweep, and triangle edges.

## 7. Known limitations

Nearest-15-degree estimation has intentional tolerance rather than requiring pixel-perfect reading. Triangle classification uses a ±2° right-angle band. Scenes are clean synthetic line drawings without perspective or hand-drawn distortion. The Level 1 bucket follows the provided greater-than-90° wording for reflex angles.
