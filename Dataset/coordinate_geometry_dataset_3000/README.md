# Coordinate Geometry Dataset (3,000 images)

## 1. Dataset purpose

This dataset fills the analytic/coordinate-geometry gap in the existing spatial-reasoning suite. Earlier categories are primarily visual-geometric without an explicit numeric coordinate system; this category grounds reasoning in the exact Cartesian coordinates used in traditional algebra and geometry coursework.

## 2. Visual design

Each 500–550 px dark-theme PNG contains a square Cartesian grid from −10 to 10, minor unit gridlines, emphasized axes, labels every two units, and 2–4 labeled integer-coordinate points. Coral points and white labels contrast with the neutral grid. Labels have small background masks and direction-aware offsets to remain legible near gridlines and borders.

## 3. Geometry construction

Coordinates are integers from −8 to 8. Pairwise distances use the Euclidean formula, midpoints use exact coordinate averages, and collinearity uses the integer cross product. All pairwise squared distances within an image are unique, eliminating closest/farthest ties. Exactly 900 images contain one collinear triple; the other 2,100 contain no collinear triple.

The skills tested are coordinate reading, Euclidean distance, midpoint computation, exact collinearity judgment, pairwise comparison, and multi-point arithmetic.

## 4. Questions and outputs

Each image has four difficulty-ordered questions: coordinate reading, pair distance, midpoint/closest/farthest structure, and collinearity/distance comparison/x-coordinate aggregation. `annotations.jsonl` stores all pairwise distances and midpoints plus exact coordinates. `dataset_final.csv` and `dataset_final.jsonl` contain 12,000 flattened rows.

## 5. Generation and reproducibility

Python 3 and Pillow are required. The originally suggested Matplotlib renderer is not required; the included Pillow renderer provides explicit pixel mapping that the PNG validator independently reproduces. Image `i` uses `random.Random(i)`.

```powershell
python generate_coordinate_geometry_dataset.py --n 3000 --output-dir .
python flatten_annotations.py --dataset-dir .
python make_contact_sheet.py --dataset-dir . --output contact_sheet.png --count 20 --columns 5
python make_contact_sheet.py --dataset-dir . --output human_calibration/review_sheet.png --count 5 --columns 5
```

Use `--sample` for five varied development examples.

## 6. Validation

```powershell
python validate_coordinate_dataset.py --dataset-dir . --report validation_report.txt
```

The validator independently recomputes every distance, midpoint, collinear triple, closest/farthest pair, and question answer. It enforces integer/range constraints, uniqueness, exact 2/3/4-point and 30/70 distributions, and reads each PNG to confirm every colored point appears at the expected coordinate-grid pixel and that the axes are present.

## 7. Known limitations

Points use integer coordinates only and a fixed moderate range. This dataset tests straight-line collinearity but not slope calculation, parallelism, perpendicularity, conic sections, or coordinate transformations; those are natural future extensions.
