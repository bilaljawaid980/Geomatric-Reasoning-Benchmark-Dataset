# GRIP Compass Bearing and Map Navigation Dataset 3000

## 1. Overview

This dataset extends the abstract angle-estimation and coordinate-geometry categories into applied map navigation. It tests compass-standard bearings, north/south spatial relations, changes in facing direction, and counterfactual path projection. North always points toward the top of the image, and bearings increase clockwise from North.

This repository contains synthetic data and ground truth only. It includes no model inference, scoring, accuracy calculation, or evaluation harness.

## 2. Contents

- 3,000 deterministic 500–550 px light-theme map diagrams
- Exactly 1,500 three-landmark and 1,500 four-landmark maps
- Exactly 1,500 maps with dashed directed paths and 1,500 without paths
- Five ordered questions per image, totaling 15,000
- Every ordered pairwise bearing and every unordered Euclidean distance
- Public questions, private answers, raw geometry, statistics, contact sheets, tests, and PNG-aware validation

The visual request allowed 2–4 landmarks, but the implemented minimum is three. Level 4 requires three distinct landmarks and Level 5 requires multiple candidate destinations; a two-landmark scene cannot support the required five rigorous questions.

## 3. Exact geometry

For image coordinates, east is positive x while north is negative image y. The compass bearing from point 1 to point 2 is therefore:

    dx = x2 - x1
    north_component = y1 - y2
    bearing = degrees(atan2(dx, north_component)) mod 360

This gives 0° North, 90° East, 180° South, and 270° West. Distances use ordinary Euclidean pixel distance and are described as abstract map units. Reverse ordered bearings are stored explicitly and differ by 180°.

## 4. Unified five-level questions

1. **Simple Description:** count landmarks.
2. **Basic Relational:** classify one landmark as north, south, or at the same latitude as another.
3. **Comparative/Structural:** derive an ordered compass bearing and round it half-up to the nearest 10°, represented canonically from `000` to `350`.
4. **Compound Reasoning:** compare two bearings from a common origin and derive the shorter turn plus clockwise/counterclockwise direction.
5. **Extrapolative/Counterfactual:** travel a reference distance along a new bearing, project the new endpoint, and identify the nearest candidate landmark.

Level 4 excludes near-zero and near-180° turns. Level 5 requires an 18-pixel minimum separation between the closest and second-closest candidate distances. Dashed paths maintain 38-pixel clearance from every unrelated landmark.

## 5. Commands and files

    python generate_compass_bearing_dataset.py --sample
    python flatten_annotations.py sample_test/annotations.jsonl
    python validate_compass_bearing_dataset.py sample_test

    python generate_compass_bearing_dataset.py --count 3000
    python flatten_annotations.py
    python make_stats.py
    python make_contact_sheet.py
    python validate_compass_bearing_dataset.py
    pytest -q test_compass_bearing_dataset.py

Outputs include `annotations.jsonl`, `images/`, `dataset_final.csv`, `dataset_final.jsonl`, `question_set.csv`, `answer_key.csv`, `stats.md`, `contact_sheet.png`, `review_sheet.png`, and `validation_report.txt`.

## 6. Independent validation

The validator independently recomputes every bearing and distance from landmark coordinates, checks reverse-bearing separation, reconstructs Level 4 turns and Level 5 projected endpoints, and re-derives all five answers. Hard-coded convention tests verify exact cardinal directions. Every final PNG is opened to verify canvas properties, landmark positions, and dashed-path alignment, and every flattened public/private row is cross-checked against raw annotations.

Manual launch checks included three independent Level 3 samples: 113.52°→110°, 291.06°→290°, and 254.21°→250°.

## 7. Reasoning scope and limitations

Skills tested include coordinate-to-bearing conversion, ordered directional reasoning, relative north/south judgment, shortest-turn direction, projection along a bearing, and nearest-point comparison.

Limitations: maps are flat 2D abstractions rather than spherical Earth navigation; distances use abstract map units rather than a geographic scale; there is no terrain, route obstruction, magnetic declination, or great-circle calculation; landmark count is limited to three or four; and bearings are inferred from clean schematic diagrams rather than noisy real maps.
