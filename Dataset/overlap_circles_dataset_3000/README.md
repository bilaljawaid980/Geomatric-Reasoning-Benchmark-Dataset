# Overlapping Circles Visual-Reasoning Dataset

Current version: `overlap-circles-2.0.0`; the initial build is preserved under `archive/v1/`. V2 samples a target overlap density before placement and accepts only non-near-complete graphs in the realized 0.2182–0.5833 range. Maximum stack depth is capped at four; 18,730 over-depth proposals were rejected. Final depth counts are 146 at depth 2, 1,041 at depth 3, and 1,813 at depth 4.

All 3,000 PNGs pass per-circle outline recovery, so distinct outline colors were not needed and the original background, fill, outline palette, and line-art style remain unchanged. Ratio questions declare an absolute tolerance of 0.1 in answer-key-side `answer_format`; scoring metadata is absent from `question_set.csv`.

## 1. Dataset overview

This dataset contains 3,000 reproducible PNG diagrams of 5–12 overlapping, semi-transparent teal circles on off-white square canvases. Each image has exactly five questions ordered from difficulty Level 1 through Level 5, giving 15,000 question-answer rows. V2 uses independently sampled target overlap-density bands rather than the superseded clustered/spread placement split.

## 2. Full generation prompt

```text
Build a Python script that programmatically generates a dataset of 3000 "overlapping 
circles" puzzle images, for testing visual counting under occlusion, region/set-relation 
reasoning, and size/area estimation.

=== VISUAL SPEC (matches reference image style) ===

Each image is a square canvas (400-420px range, randomize) with a plain off-white/cream 
background (#F1EFE8 or similar).

- Draw N circles per image, where N is randomized between 5 and 12.
- Each circle: randomized center (cx, cy) and radius, with SEMI-TRANSPARENT fill 
  (single muted teal/slate-blue color, ~15-20% opacity per circle, so overlapping 
  regions visibly darken/layer where 2, 3, 4+ circles stack — matching the reference 
  image exactly) and a thin dark teal outline stroke (1-1.5px, fully opaque, no transparency 
  on the stroke itself).
- Circles must overlap substantially and cluster together (like the reference image) — 
  do NOT scatter circles evenly across the canvas. Generate via a clustering approach: 
  pick a rough cluster center, then place each circle's center within a randomized radius 
  of that cluster center (with enough variation that circles differ in size and don't 
  perfectly coincide), ensuring at least 60% of circle-pairs overlap.
- Radius range per circle: 12% to 30% of canvas width, randomized per circle (varying 
  sizes, matching the reference image which has clearly different-sized circles).
- Enforce a minimum separation so no two circles are IDENTICAL (same center + radius) 
  and no circle is fully contained with a near-zero gap making it visually indistinguishable 
  from another (reject/regenerate if two circles' centers and radii are within 3px of 
  each other on all dimensions).
- No fill color variation — every circle uses the exact same base color and opacity, so 
  the only visual counting cue is the outline boundaries and layered transparency depth 
  (this is the actual source of difficulty, matching the reference image).

=== GROUND TRUTH DATA TO TRACK PER IMAGE ===

For every circle: {index, center: [cx,cy], radius}.

Compute and store:
- total_circle_count = N
- pairwise_overlaps: list of {circle_i, circle_j} for every pair whose distance between 
  centers < (radius_i + radius_j) (i.e. they overlap at all)
- total_overlapping_pairs: count of the above
- non_overlapping_circles: list of circle indices with ZERO overlaps with any other circle 
  (should usually be empty/rare given the clustering generation method, but track it — 
  useful as a rare "trick" case)
- largest_circle_index, smallest_circle_index (by radius)
- max_stack_depth: the maximum number of circles that overlap at any single point in the 
  image (compute via a fine grid-sampling approach: for a grid of points across the canvas, 
  count how many circles contain each point, take the max across all grid points) — this 
  is the ground truth for "darkest region" questions
- max_stack_location: approximate (x,y) of where max_stack_depth occurs

=== GROUND TRUTH GENERATION — EXACTLY 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many distinct circles are in this image? Answer with a number in curly brackets, 
  e.g. {8}."
  ground_truth = total_circle_count

LEVEL 2 - Basic Relational (always include, pick ONE at random per image):
  a) "Is there any circle that does not overlap with any other circle? Answer yes or no."
     ground_truth = "yes" if len(non_overlapping_circles) > 0 else "no"
  b) "How many pairs of circles overlap with each other? Answer with a number in curly 
     brackets, e.g. {10}."
     ground_truth = total_overlapping_pairs

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "Which is larger: the biggest circle or the smallest circle? Estimate the ratio of 
     their sizes (diameter), rounded to 1 decimal, e.g. {2.3}."
     ground_truth = round(largest_radius / smallest_radius, 1)
  b) "Roughly how many circles overlap at the most densely overlapped point in the image? 
     Answer with a number in curly brackets, e.g. {4}."
     ground_truth = max_stack_depth
  c) "Are the circles clustered tightly in one area, or spread evenly across the whole 
     image? Answer 'clustered' or 'spread'."
     ground_truth = "clustered" always for this generation method (state explicitly in 
     README that this question type always resolves to "clustered" by design — included 
     as a sanity/calibration question, not a discriminative one; OR make this genuinely 
     variable by allowing ~10% of images to use a spread-out generation mode instead of 
     clustered, recommend this variant for real discriminative value)

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "If you removed the largest circle from the image, how many circles would remain 
     that don't overlap with any other circle? Answer with a number in curly brackets."
     ground_truth = recompute non_overlapping_circles count with the largest circle's 
     overlaps excluded from consideration
  b) "How many circles have a radius larger than the AVERAGE radius of all circles in 
     this image? Answer with a number in curly brackets."
     ground_truth = count of circles with radius > mean(all radii)
  c) "Estimate what percentage of circles in this image overlap with at least 3 other 
     circles. Answer as a whole number percentage in curly brackets, e.g. {40}."
     ground_truth = round(100 * count(circles with >=3 overlap partners) / total_circle_count)

=== METADATA (per image) ===

{
  "id": "overlap_circles_0001",
  "image_path": "images/overlap_circles_0001.png",
  "canvas_size": [410, 410],
  "total_circle_count": 9,
  "total_overlapping_pairs": 24,
  "non_overlapping_count": 0,
  "max_stack_depth": 5,
  "largest_radius": 95.2,
  "smallest_radius": 41.8,
  "seed": 1,
  "difficulty_score": <float, compute from: total_circle_count, total_overlapping_pairs, 
    max_stack_depth (higher stack = harder to visually parse), radius variance>,
  "circles": [
    {"index": 0, "center": [180, 200], "radius": 95.2},
    ...
  ]
}

=== OUTPUT FORMAT (same pipeline as previous four datasets) ===

1. /dataset/annotations.jsonl — one JSON object per image, full metadata + 4-question 
   array (question_id, question_text, question_type, ground_truth, answer_format, 
   difficulty_level 1-4)
2. /dataset/images/overlap_circles_{index:04d}.png
3. flatten_annotations.py → dataset_final.csv with columns: task, image, prompt, 
   groundtruth, metadata
   task mapping by difficulty_level:
     1 → "Image Description"
     2 → "Basic Relational Reasoning"
     3 → "Comparative Reasoning"
     4 → "Compound Reasoning"
   metadata column = compact JSON with ONLY: difficulty_score, total_circle_count, 
   total_overlapping_pairs, max_stack_depth, seed (exclude the full "circles" array — 
   keep that only in raw annotations.jsonl)
4. validate_overlap_circles_dataset.py: re-parses annotations.jsonl, independently 
   RECOMPUTES every ground truth value from the stored circles array (overlap pairs 
   via distance check, max_stack_depth via grid resampling, radius ratios, averages), 
   and confirms exact match to stored ground truth. Also confirm: every image file 
   exists, no two circles are near-duplicates, all circle centers/radii keep the full 
   circle within canvas bounds (or intentionally allow slight edge-clipping — decide 
   and document this choice).
5. --sample flag for 5 test images first — manually count circles by eye against all 5 
   before trusting the pipeline at scale (this category has the highest risk of 
   human-vs-model disagreement on the Level 1 "how many circles" question itself, so 
   establish your own ground-truth confidence here early).

=== TECHNICAL NOTES ===

- Use matplotlib or svgwrite+cairosvg for rendering with true alpha-transparency layering 
  (needed for the visual "darker where more circles overlap" effect matching the reference 
  image) — matplotlib's patches.Circle with alpha parameter is straightforward for this.
- Implement compute_max_stack_depth(circles, canvas_size, grid_resolution=2px) via dense 
  grid sampling — for each grid point, count circles containing it, track the max.
- Implement circles_overlap(c1, c2) via simple distance-between-centers vs sum-of-radii check.
- Reuse random.seed(i) per image index for reproducibility.

Output the full script as: generate_overlap_circles_dataset.py

=== README REQUIREMENT (same 7-section paper-ready format as previous datasets) ===

Follow the exact same structure as cube_structure_dataset_3000's README: dataset overview, 
full verbatim generation prompt in a code block, question design rationale with real 
template-usage distribution from annotations.jsonl, ground truth generation method + 
validation pass rate, known limitations, reasoning skills tested, file structure + schema 
with one real worked 4-row example.

Known limitations to state explicitly:
- Circles only — no other overlapping shape types (ellipses, polygons) tested
- Single fixed opacity/color for all circles — no color-based sub-grouping variant
- Clustered generation mode only (unless the ~10% spread-mode variant was implemented — 
  state which decision was made)
- max_stack_depth computed via grid sampling at a fixed resolution — a theoretical edge 
  case at extremely fine sub-pixel scale is approximated, not exact

Reasoning skills tested to list explicitly:
- Object counting under heavy occlusion (subitizing breakdown at N>6-7)
- Pairwise relational reasoning (overlap detection)
- Amodal boundary tracing (distinguishing individual circle outlines within dense clusters)
- Size/ratio estimation from visual proportions
- Statistical reasoning over a set (above-average count, percentage estimation)
```

## 3. Question design rationale

The four fixed levels progress from visible-object counting, through pairwise overlap reasoning, to comparison and compound counterfactual/statistical reasoning. One template is selected reproducibly within each level's permitted pool. Actual usage:

- Level 1: `total_circle_count` 3000
- Level 2: `has_non_overlapping_circle` 1491, `overlapping_pair_count` 1509
- Level 3: `cluster_distribution` 983, `largest_smallest_ratio` 1025, `max_stack_depth` 992
- Level 4: `above_average_radius_count` 913, `isolated_after_largest_removal` 1019, `three_plus_overlap_percent` 1068

## 4. Ground truth generation and validation

Circle parameters—not pixels guessed by a model—are the source of truth. Pairwise overlaps use center distance `< r1 + r2`; isolated circles are derived from the resulting graph; size comparisons use stored radii; and maximum simultaneous coverage is recomputed on an independent 2-pixel grid. The validator also checks image existence, four-level question completeness, near-duplicates, full canvas containment, and every stored answer. Final result: **3,000/3,000 images passed; 0 mismatches**.

Run `python validate_overlap_circles_dataset.py .` from this directory to reproduce the report.

## 5. Known limitations

- Circles only; ellipses and polygons are not tested.
- All circles use one fixed color and opacity, so there is no color-based subgrouping.
- A 10% spread-mode variant was implemented; the other 90% are deliberately clustered.
- `max_stack_depth` uses fixed 2-pixel grid sampling, so extremely fine sub-pixel maxima are approximated rather than analytically exact.
- Transparency accumulation and antialiasing may vary slightly if images are regenerated under a materially different Pillow version.

## 6. Reasoning skills tested

- Object counting under heavy occlusion (including subitizing breakdown beyond 6–7 objects)
- Pairwise relational reasoning and overlap detection
- Amodal boundary tracing within dense clusters
- Size and ratio estimation from visual proportions
- Statistical reasoning over a set, including above-average counts and percentages
- Counterfactual graph reasoning after removing the largest circle

## 7. File structure, schema, and worked example

```text
overlap_circles_dataset_3000/
├── images/                         # 3,000 PNG files
├── annotations.jsonl               # full geometry, metadata, and five questions/image
├── dataset_final.csv               # flattened 15,000-row table
├── dataset_final.jsonl             # flattened JSONL equivalent
├── generate_overlap_circles_dataset.py
├── validate_overlap_circles_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── generation_prompt.txt
└── README.md
```

Each raw annotation stores identifiers, canvas size, circle centers/radii, pairwise overlap data, derived statistics, seed, difficulty score, and a five-object `questions` array. `question_set.csv` exposes exactly `question_id`, `task`, `image`, and `prompt`; scoring fields remain answer-key-side.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | overlap_circles_0001.png | How many distinct circles are in this image? Answer with a number in curly brackets, e.g. {8}. | 6 |
| Basic Relational Reasoning | overlap_circles_0001.png | Is there any circle that does not overlap with any other circle? Answer yes or no. | no |
| Comparative Reasoning | overlap_circles_0001.png | Which is larger: the biggest circle or the smallest circle? Estimate the ratio of their sizes (diameter), rounded to 1 decimal, e.g. {2.3}. | 2.3 |
| Compound Reasoning | overlap_circles_0001.png | Estimate what percentage of circles in this image overlap with at least 3 other circles. Answer as a whole number percentage in curly brackets, e.g. {40}. | 100 |
