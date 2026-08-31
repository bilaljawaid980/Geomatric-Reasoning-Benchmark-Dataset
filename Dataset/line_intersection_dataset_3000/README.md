# Line Intersection Dataset

## 1. Dataset overview

The current v3 dataset contains **3,000 images** and **15,000 questions** (five ordered levels per image). It was generated using a fully synthetic, deterministic Python pipeline; no image was human-drawn and no answer was manually labeled. The visual design and dual-wording Level-2 format were adapted from an existing published methodology for testing line-intersection counting in vision-language models.

### Version 3 Level-5 counterfactual correction

The former 20-pixel downward translation was independently recomputed and found to preserve the intersection count in all 2,016 translation-template items because it was smaller than the generator's endpoint separation. Version 3 uses 60 pixels and always rebuilds the translated red coordinates before running the full red-blue segment-intersection search. This changes 1,400 Level-5 answers; the translated-minus-original distribution is recorded in `validation_metrics.json`. The other 984 Level-5 items retain the remove-first-red-segment template. The new overall Level-5 constant-answer baseline is 49.63%.

All five levels, point/segment and intersection-array invariants, leak statistics, guard injections, and all 3,000 PNGs are exhaustively revalidated. The long verbatim prompt below is retained as historical design provenance; the release description above and v3 generator are authoritative.

## 2. Full verbatim generation prompt

### Generation Prompt (verbatim)

```text
Build a Python script that programmatically generates a dataset of 3000 "line intersection" 
puzzle images, for testing precise geometric/visual reasoning — specifically intersection 
counting, spatial relation judgment, and coordinate-level estimation.

=== VISUAL SPEC (matches reference figure style) ===

Each image is a clean white/off-white canvas (500x400px range, randomize slightly), no axes, 
no gridlines, no ticks — just two colored polylines on blank background, matching the 
reference figure exactly.

- Draw exactly 2 polylines per image: one RED, one BLUE (fixed colors, consistent across 
  the whole dataset — do not randomize these two colors, since the question templates 
  reference "red" and "blue" by name).
- Each polyline is defined by a randomized number of points: between 3 and 6 points per 
  line (the reference example uses exactly 3 points / 2 segments — extend this range to 
  add difficulty variation, with simpler 3-point lines for ~40% of images and more complex 
  4-6 point lines for the remaining 60%).
- X-coordinates of each line's points are evenly spaced across a shared horizontal range 
  (matching the reference style where both lines share the same x-positions) — this keeps 
  the "two lines crossing" visual clean and comparable to the reference paper's methodology.
- Y-coordinates are randomly sampled per point, WITH a controlled generation process 
  (see below) that guarantees exact intersection counts, matching the reference's 
  described method to produce 0, 1, or 2+ intersections.
- Extend intersection count range beyond the reference's 0-2: generate images spanning 
  0 to 5 total intersection points (more segments = more possible crossings), giving a 
  wider difficulty range for your 4-level question structure.
- Line thickness: 2px, solid, no markers/dots at vertices (matching reference, clean line 
  only — do not show the underlying points).
- No legend needed in-image — but track underlying point coordinates in metadata.

=== INTERSECTION GENERATION METHOD (critical for correctness) ===

Do not just draw random lines and hope to count intersections after the fact with 
floating-point geometry alone (risk of near-miss/tangent ambiguity). Instead:

1. Generate line segments as before (random y-coordinates at fixed/shared x-positions 
   for both lines).
2. Compute EXACT intersection points between every segment-pair of line A vs every 
   segment-pair of line B using robust 2D line-segment intersection math (parametric 
   line intersection formula, checking t and u both in [0,1]).
3. Explicitly reject and regenerate any image where an intersection lands exactly on a 
   shared endpoint (ambiguous edge case) or where two segments are collinear/overlapping 
   (degenerate case) — keep regenerating until you get a clean set of well-defined 
   crossing points.
4. Store the EXACT computed intersection coordinates (not estimated) as ground truth.

=== GROUND TRUTH DATA TO TRACK PER IMAGE ===

- red_points: list of (x,y) vertices defining the red polyline
- blue_points: list of (x,y) vertices defining the blue polyline
- num_red_segments, num_blue_segments
- intersections: list of {x, y, red_segment_index, blue_segment_index} for every 
  computed crossing point
- total_intersections: count
- leftmost_intersection_x, rightmost_intersection_x (for spatial questions)
- red_above_blue_at_start: true/false (whether red line starts higher than blue line 
  on the y-axis, at the leftmost shared x-position)
- red_above_blue_at_end: true/false (same, at rightmost x-position)
- crossed_from_above_to_below: true if red_above_blue_at_start != red_above_blue_at_end 
  (i.e. the lines' relative vertical order flipped — a necessary condition tied to 
  odd/even intersection count)

=== GROUND TRUTH GENERATION — EXACTLY 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include, pick ONE at random per image):
  a) "How many line segments make up the red line?"
     ground_truth = num_red_segments
  b) "How many line segments make up the blue line?"
     ground_truth = num_blue_segments

LEVEL 2 - Basic Relational (always include, use BOTH wordings from the reference paper 
  as a randomized pair — pick ONE wording per image, 50/50 split, to build in the 
  paraphrase-robustness testing the reference example demonstrates):
  a) "How many times do the blue and red lines touch each other? Answer with a number 
     in curly brackets, e.g. {5}."
  b) "Count the intersection points where the blue and red lines meet. Put your answer 
     in curly brackets, e.g. {2}."
  ground_truth = total_intersections (same ground truth regardless of which wording 
  is selected — this tests wording-robustness, note this explicitly in metadata via 
  a "wording_variant" field)

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "At the leftmost point of the image, which line is higher: red or blue?"
     ground_truth = "red" or "blue" based on red_above_blue_at_start
  b) "Does the red line end above or below the blue line (at the rightmost point)?"
     ground_truth = "above" or "below" based on red_above_blue_at_end
  c) "Is the leftmost intersection point closer to the left edge or the right edge of 
     the image? Answer 'left' or 'right'."
     ground_truth = compare leftmost_intersection_x against canvas midpoint 
     (only use if total_intersections >= 1; otherwise fall back to (a))

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "If the two lines intersect an odd number of times, the line that starts higher 
     must end lower (and vice versa). Based on this rule, do these two lines intersect 
     an odd or even number of times? Answer 'odd' or 'even'."
     ground_truth = "odd" if crossed_from_above_to_below else "even" — BUT this rule 
     only strictly holds for simple non-self-intersecting polylines with generic 
     crossings; verify this logically holds for your generated data before using it 
     as ground truth (if a line's OWN segments cross each other, this heuristic breaks — 
     either prevent self-intersecting polylines during generation, or exclude this 
     question type for images where a line self-intersects)
  b) "How many intersection points occur in the left half of the image versus the 
     right half? Answer as two numbers separated by a comma, e.g. {2,1}."
     ground_truth = "{left_count},{right_count}" split by canvas horizontal midpoint
  c) "If you removed the segment of the red line closest to the left edge, how many 
     intersection points would remain? Answer with a number in curly brackets."
     ground_truth = total_intersections minus count of intersections involving 
     red_segment_index == 0

=== METADATA (per image) ===

{
  "id": "line_intersect_0001",
  "image_path": "images/line_intersect_0001.png",
  "canvas_size": [520, 400],
  "num_red_segments": 3,
  "num_blue_segments": 3,
  "total_intersections": 2,
  "intersections": [{"x": 210.5, "y": 145.2, "red_segment_index": 1, "blue_segment_index": 1}, ...],
  "wording_variant": "touch_each_other" | "intersection_points",
  "red_self_intersecting": false,
  "blue_self_intersecting": false,
  "seed": 1,
  "difficulty_score": <float, compute from: total_intersections, num_red_segments + 
    num_blue_segments, whether Level 4 required exact coordinate math>,
  "red_points": [[x,y], ...],
  "blue_points": [[x,y], ...]
}

=== OUTPUT FORMAT (same pipeline as previous three datasets) ===

1. /dataset/annotations.jsonl — one JSON object per image, full metadata + 4-question array 
   (question_id, question_text, question_type, ground_truth, answer_format, difficulty_level)
2. /dataset/images/line_intersect_{index:04d}.png
3. flatten_annotations.py → dataset_final.csv with columns: task, image, prompt, 
   groundtruth, metadata
   task mapping by difficulty_level:
     1 → "Image Description"
     2 → "Basic Relational Reasoning"
     3 → "Comparative Reasoning"
     4 → "Compound Reasoning"
   metadata column = compact JSON with ONLY: difficulty_score, total_intersections, 
   num_red_segments, num_blue_segments, wording_variant, seed (exclude full point/
   intersection coordinate arrays — keep those only in raw annotations.jsonl)
4. validate_line_intersect_dataset.py: re-parses annotations.jsonl, independently 
   RE-COMPUTES every intersection from the stored red_points/blue_points using the 
   same robust segment-intersection math, and confirms the recomputed count and 
   coordinates match stored ground truth exactly. Also confirm: no degenerate/collinear 
   cases slipped through, no endpoint-exact-intersection edge cases, every image file exists.
5. --sample flag for 5 test images first — manually verify intersection counts by eye 
   against the rendered image for all 5.

=== TECHNICAL NOTES ===

- Use matplotlib (closest match to the reference figure's exact visual style — plain 
  white background, no axes/ticks, thin clean lines) OR svgwrite+cairosvg for consistency 
  with your other 3 datasets. Prefer matplotlib with axes turned off if visual fidelity 
  to the reference image matters most; note this decision in the README.
- Implement segment_intersection(p1, p2, p3, p4) using the standard parametric line 
  intersection formula, returning None if parallel/no intersection, else the exact (x,y) 
  point and t,u parameters.
- Implement is_self_intersecting(points) to check a single polyline against itself, used 
  to filter Level 4(a) eligibility.
- Reuse random.seed(i) per image index for reproducibility.

Output the full script as: generate_line_intersection_dataset.py

=== README REQUIREMENT (same paper-ready format as previous datasets) ===

Generate README.md in the dataset root, following the EXACT same 7-section structure 
used for cube_structure_dataset_3000's README (dataset overview, full verbatim generation 
prompt in a code block, question design rationale with real template-usage distribution 
pulled from annotations.jsonl, ground truth generation method + validation pass rate, 
known limitations, reasoning skills tested, file structure + schema with one real worked 
4-row example).

Additionally, in section 1 (dataset overview), explicitly note that this dataset's visual 
design and Level-2 dual-wording question format were adapted from an existing published 
methodology for testing line-intersection counting in vision-language models, extended 
here with a 4-level difficulty structure, segment-count variation, self-intersection 
handling, and coordinate-level Level 4 questions not present in the original reference design.

Known limitations to state explicitly:
- Only 2 lines per image (red vs blue) — no 3+ line variants
- Only polylines (straight segments) — no curves
- X-coordinates are shared/aligned between both lines — does not test fully independent 
  arbitrary line placement
- Level 4(a)'s odd/even intersection rule depends on non-self-intersecting lines and is 
  explicitly excluded for the small subset of images where either line self-intersects

Reasoning skills tested to list explicitly:
- Precise visual counting of crossing points
- Spatial relation judgment (which line is higher/lower at a given position)
- Regional/spatial partitioning (left-half vs right-half counting)
- Compositional reasoning (removing a segment and recomputing a downstream count)
- Topological inference (odd/even crossing rule from endpoint positions)
```

## 3. Question design rationale

Level 1 measures segment description, Level 2 measures direct intersection counting under two paraphrases, Level 3 measures endpoint order or intersection location, and Level 4 requires parity inference, spatial partitioning, or counterfactual segment removal. This progression measures reasoning depth rather than perception alone and enables difficulty-stratified reporting.

### Actual template distribution

| Level | Role | Question type | Uses |
|---:|---|---|---:|
| 1 | Simple description/counting | `blue_segment_count` | 1,492 |
| 1 | Simple description/counting | `red_segment_count` | 1,508 |
| 2 | Basic relational reasoning | `intersection_count` | 3,000 |
| 3 | Comparative/structural reasoning | `higher_at_start` | 1,110 |
| 3 | Comparative/structural reasoning | `leftmost_intersection_side` | 781 |
| 3 | Comparative/structural reasoning | `red_end_relation` | 1,109 |
| 4 | Complex/compound reasoning | `intersection_half_counts` | 1,030 |
| 4 | Complex/compound reasoning | `intersection_parity` | 986 |
| 4 | Complex/compound reasoning | `remove_first_red_segment` | 984 |

## 4. Ground truth generation method

All labels were derived deterministically from the stored red and blue vertex coordinates used to render each image. The generator controls the sign changes of the vertical line separation to construct a target crossing count, then computes every crossing using parametric segment-intersection equations. The independent validator re-parses the vertices, recomputes coordinates and counts, rejects endpoint/collinear degeneracies, verifies self-intersection flags, and re-derives all four answers.

Final validation:

```text
Total images checked: 3000
Total mismatches found: 0
Summary: PASS
```

## 5. Known limitations

- Exactly two lines per image (red and blue); no 3+ line variants are included.
- Polylines use straight segments only; curved paths are absent.
- Both lines share aligned x-coordinates, so fully independent arbitrary placement is not tested.
- The Level-4 odd/even rule assumes non-self-intersecting lines and is excluded whenever that condition is not satisfied. In the released construction, monotonic x-order prevents self-intersection.
- Rendering is clean synthetic line art rather than a natural or photographed scene.

## 6. Reasoning skills tested

- Precise visual counting of crossing points
- Spatial relation judgment (which line is higher or lower)
- Regional partitioning (left-half versus right-half counts)
- Compositional reasoning after removing a segment
- Topological inference from odd/even crossing parity

## 7. File structure and schema

```text
line_intersection_dataset_3000/
  images/
  annotations.jsonl
  dataset_final.csv
  dataset_final.jsonl
  validation_report.txt
  README.md
  generation_prompt.txt
  generate_line_intersection_dataset.py
  validate_line_intersect_dataset.py
  flatten_annotations.py
  finalize_dataset.py
  contact_sheet.png
```

| Column | Meaning |
|---|---|
| `task` | Difficulty-level task label. |
| `image` | PNG filename only. |
| `prompt` | Question text. |
| `groundtruth` | Programmatically computed plain-string answer. |
| `metadata` | Compact JSON with difficulty, crossing count, segment counts, wording variant, and seed. |

Full point and intersection arrays remain only in `annotations.jsonl`.

### Worked four-level example for `line_intersect_0001.png`

```csv
task,image,prompt,groundtruth,metadata
Image Description,line_intersect_0001.png,How many line segments make up the blue line?,3,"{""difficulty_score"":0.2967,""num_blue_segments"":3,""num_red_segments"":3,""seed"":1,""total_intersections"":2,""wording_variant"":""touch_each_other""}"
Basic Relational Reasoning,line_intersect_0001.png,"How many times do the blue and red lines touch each other? Answer with a number in curly brackets, e.g. {5}.",2,"{""difficulty_score"":0.2967,""num_blue_segments"":3,""num_red_segments"":3,""seed"":1,""total_intersections"":2,""wording_variant"":""touch_each_other""}"
Comparative Reasoning,line_intersect_0001.png,"At the leftmost point of the image, which line is higher: red or blue?",blue,"{""difficulty_score"":0.2967,""num_blue_segments"":3,""num_red_segments"":3,""seed"":1,""total_intersections"":2,""wording_variant"":""touch_each_other""}"
Compound Reasoning,line_intersect_0001.png,"If you removed the segment of the red line closest to the left edge, how many intersection points would remain? Answer with a number in curly brackets.",1,"{""difficulty_score"":0.2967,""num_blue_segments"":3,""num_red_segments"":3,""seed"":1,""total_intersections"":2,""wording_variant"":""touch_each_other""}"
```
