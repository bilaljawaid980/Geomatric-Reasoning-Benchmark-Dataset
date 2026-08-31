# Embedded Figures Dataset

## 1. Dataset overview

This dataset implements a synthetic, programmatically generated version of the classic Embedded Figures Test associated with Witkin (1950), as situated within the cognitively grounded spatial-reasoning taxonomy used by [Spatial-DISE](https://arxiv.org/abs/2510.13394). It contains 3,000 unique dark-theme puzzle images and 12,000 question-answer rows. Every target edge is part of the same undifferentiated line network as its distractors; no target highlighting appears in dataset images.

## 2. Full generation prompt

```text
Build a Python script that generates 3000 "embedded figures" puzzle images, testing 
figure-ground segregation — finding a simple target shape camouflaged within a more 
complex overlapping line drawing. This is a classic cognitive-psychology task (Witkin's 
Embedded Figures Test, 1950), distinct from occlusion-based counting tasks already in 
the suite: here the target shape's edges are fully present but visually disguised by 
surrounding distractor lines, not hidden behind other objects.

=== VISUAL SPEC ===

Canvas: 450-500px, DARK background (#1A1A1A), consistent with your dark-theme datasets.

- Generate a "complex figure": an irregular network of straight line segments (8-14 
  segments) forming a busy, angular line drawing, rendered in a single thin light-gray 
  stroke (matching your wireframe style, ~1px, no fill).
- Embed ONE simple target polygon (triangle, square, pentagon, or hexagon — 3 to 6 sides) 
  INTO the complex figure such that every edge of the target polygon is drawn as part of 
  the complex figure's line network (i.e. the target's edges literally ARE some subset of 
  the complex figure's segments — not overlaid separately, genuinely embedded/shared lines, 
  matching the reference EFT task design).
- To construct this correctly: 
  1. First generate the target polygon's vertex coordinates (regular or slightly 
     irregular N-gon).
  2. Then generate additional random distractor line segments that connect to and extend 
     from the target polygon's vertices and edges, in directions/lengths that visually 
     break up the target's silhouette (crossing through it, extending past its corners, 
     adding false additional angles near its vertices) so the target is not obviously 
     outlined as a clean isolated shape.
  3. Render the ENTIRE combined figure (target edges + distractor edges) in the SAME 
     single color/stroke style — no highlighting, no color difference between target and 
     distractor lines in the puzzle image itself (that would defeat the purpose).
- Below/beside the puzzle image area (or as a separate labeled row within the same canvas), 
  show 4 small "answer choice" candidate shapes (A, B, C, D): one is the correct target 
  shape (matching its actual vertex count and approximate proportions, but rendered as a 
  small clean isolated outline), the other 3 are plausible distractors (similar vertex 
  count but different angle/proportion, or a shape that appears elsewhere as a false cue 
  among the distractor lines but isn't actually validly embedded).

=== GROUND TRUTH DATA PER IMAGE ===

- target_shape_type: "triangle"|"square"|"pentagon"|"hexagon"
- target_vertices: the actual embedded coordinates within the complex figure
- num_total_segments: total line count in the complex figure (target + distractor combined)
- num_distractor_segments
- correct_answer_choice: "A"|"B"|"C"|"D" (which of the 4 shown candidates is correct)
- distractor_choices_info: brief description of why each wrong choice is wrong (right 
  vertex count wrong proportions / wrong vertex count entirely / etc.)

=== 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many straight line segments make up this complex figure in total?"
  ground_truth = num_total_segments

LEVEL 2 - Basic Relational (always include):
  "How many sides does the hidden target shape have (visible in the answer choices below)?"
  ground_truth = number of sides matching target_shape_type (3/4/5/6)
  (This is answerable just from looking at the answer choices' shapes without solving the 
  full embedding — intentionally the easiest "relational" question, calibration-style)

LEVEL 3 - Comparative/Structural (always include, this is the CORE question):
  "Which of the four candidate shapes (A, B, C, D) is actually hidden within the complex 
  figure above? Answer with the letter."
  ground_truth = correct_answer_choice

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "How many of the total line segments in the complex figure are NOT part of the 
     hidden target shape (i.e. are distractor lines)?"
     ground_truth = num_distractor_segments
  b) "If you removed all distractor lines and kept only the target shape's edges, would 
     the remaining figure be a closed polygon or an open/broken shape? Answer 'closed' 
     or 'open'."
     ground_truth = "closed" always by construction (state this explicitly as a 
     calibration/sanity question - the target is always validly closed by design) — 
     OR make this genuinely variable by occasionally (10%) embedding a target with one 
     edge deliberately using a slightly different line that doesn't quite close the 
     polygon, to make this discriminative. Recommend the variable version for real value.
  c) "One of the 3 incorrect answer choices shares the same number of sides as the correct 
     target shape. Does such a choice exist among the 4 options? Answer yes or no."
     ground_truth: precompute during generation whether at least one distractor choice 
     has the same side-count as the correct target (design ~50% of images this way, 
     50% where all distractors have different side counts, to keep this genuinely 
     variable and non-trivial)

=== METADATA, OUTPUT, VALIDATION (same pipeline pattern) ===

1. annotations.jsonl, images/embedded_figure_{index:04d}.png
2. flatten_annotations.py → dataset_final.csv (same schema/task mapping as other 11 datasets)
3. validate_embedded_figures_dataset.py:
   - Independently re-verify that target_vertices' edges are genuinely a subset of the 
     rendered complex figure's segment list (not just claimed in metadata)
   - Independently re-verify the "closed polygon" claim by checking edge connectivity
   - Re-derive every ground truth from stored data, confirm exact match
   - Confirm reasonably even distribution across the 4 target shape types (triangle/
     square/pentagon/hexagon) and across correct_answer_choice being A/B/C/D roughly 
     equally (avoid a "always answer C" shortcut)
4. --sample flag, 5 images — this is a HIGH manual-check-priority category: literally 
   try to visually find the hidden shape yourself in each of the 5 samples before trusting 
   generation at scale. If you personally cannot find it by eye within a reasonable time, 
   the puzzle is either too hard (interesting) or broken (the target isn't visually 
   findable due to a generation bug) — distinguish between these two cases manually.

=== TECHNICAL NOTES ===

- Use matplotlib or svgwrite+cairosvg. Implement generate_target_polygon(n_sides) for 
  the base shape, then generate_distractor_lines(target_vertices, count) that adds lines 
  connecting to/through/near target vertices without being collinear with target edges 
  (avoid accidentally extending a target edge into an ambiguous longer line).
- Implement is_valid_embedding(target_edges, full_segment_list) for validation — confirm 
  every target edge appears as an exact or sub-segment match within the full line list.
- Reuse random.seed(i) per image for reproducibility.

Output as: generate_embedded_figures_dataset.py

=== README (7-section format, citing Spatial-DISE / Witkin 1950) ===

Section 1: state this dataset implements a synthetic, programmatically-generated version 
of the classic Embedded Figures Test (Witkin, 1950), as catalogued in the Spatial-DISE 
taxonomy (arXiv 2510.13394) under spatial visualization tasks.

Known limitations: only straight-line polygon targets (3-6 sides), no curved shapes; 
distractor line generation is randomized rather than adversarially optimized to maximize 
difficulty; 4-choice multiple choice format may allow partial-credit guessing (25% baseline 
chance) unlike open-ended questions elsewhere in the suite — note this explicitly as a 
scoring consideration.

Reasoning skills tested: figure-ground segregation, camouflaged/embedded contour tracing, 
selective attention to relevant vs distractor visual elements, shape discrimination against 
plausible foils.

Output as: generate_embedded_figures_dataset.py
```

## 3. Question design rationale

The four levels progress from line-stroke counting and target side count to the core embedded-choice task, then distractor counting, closure, or same-side-foil reasoning. Actual template usage:

- Level 1: `total_segments` 3000
- Level 2: `target_side_count` 3000
- Level 3: `embedded_choice` 3000
- Level 4: `distractor_segment_count` 993, `same_side_foil_exists` 994, `target_closure` 1013

Target shapes are exactly balanced: hexagon=750, pentagon=750, square=750, triangle=750. Correct answer positions are exactly balanced: A=750, B=750, C=750, D=750. Same-side foils occur in 1500 images and are absent in 1500.

## 4. Ground truth generation and validation

Generation starts with a slightly irregular 3–6 sided closed polygon. Its exact edges are inserted into the shared segment list before 6–8 connected false continuations, chords, and crossing lines are added. The correct answer choice is a translated and uniformly scaled copy of the actual target coordinates; wrong choices differ in side count or proportions.

The independent validator reconstructs target edges from vertices, checks exact membership in the full segment list, verifies closed connectivity, confirms the correct candidate's normalized coordinates, and recomputes all answers. It also loads every final PNG and samples pixels along each target edge, proving the labeled contour was rendered. Final result: **3,000/3,000 images passed with 0 mismatches**. Five unhighlighted samples were visually traced by eye; a separate red-overlay review sheet confirms those same contours without altering dataset images.

## 5. Known limitations

- Targets are straight-line polygons with 3–6 sides; curved targets are excluded.
- Distractor generation is randomized and connected to target geometry rather than adversarially optimized for maximum difficulty.
- Four-choice questions have a 25% chance baseline, unlike open-ended tasks elsewhere in the suite; scoring should account for this.
- Intersections can visually subdivide a drawn stroke; `num_total_segments` counts the original straight strokes in the stored network, not atomic pieces created by crossings.
- The target is always closed; closure questions are calibration checks rather than discriminative cases.

## 6. Reasoning skills tested

- Figure-ground segregation
- Camouflaged contour tracing
- Selective attention to relevant versus distractor edges
- Shape and proportion discrimination against plausible foils
- Maintaining a closed contour through line crossings and false continuations

## 7. File structure, schema, and worked example

```text
embedded_figures_dataset_3000/
├── images/
├── annotations.jsonl
├── dataset_final.csv
├── dataset_final.jsonl
├── generate_embedded_figures_dataset.py
├── validate_embedded_figures_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── review_samples_contact_sheet.png
├── review_samples_target_overlay.png
├── generation_prompt.txt
└── README.md
```

Raw annotations store the target vertices/edges, complete segment network, all four candidate polygons, foil explanations, balance flags, seed, difficulty, and questions. Flattened metadata retains only compact target/count/choice fields.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | embedded_figure_0001.png | How many straight line segments make up this complex figure in total? | 10 |
| Basic Relational Reasoning | embedded_figure_0001.png | How many sides does the hidden target shape have (visible in the answer choices below)? | 3 |
| Comparative Reasoning | embedded_figure_0001.png | Which of the four candidate shapes (A, B, C, D) is actually hidden within the complex figure above? Answer with the letter. | A |
| Compound Reasoning | embedded_figure_0001.png | If you removed all distractor lines and kept only the target shape's edges, would the remaining figure be a closed polygon or an open/broken shape? | closed |
