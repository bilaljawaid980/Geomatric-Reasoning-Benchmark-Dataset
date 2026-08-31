# Orthographic Multi-View Dataset

## 1. Dataset overview

This dataset contains **3,000 fully synthetic orthographic multi-view puzzles** and **12,000 programmatically labeled questions**. It was generated on 2026-08-14 from integer voxel coordinates; no image or answer was manually drawn or estimated.

The task implements classical third-angle orthographic/multiview reasoning used in engineering and technical drawing. It is the inverse-task complement to `cube_structure_dataset_3000`: that benchmark presents one isometric 3D view and asks about occlusion within it, whereas this benchmark presents top, front, and side 2D silhouettes and asks for reconstruction or cross-view inference.

Half of the images include four candidate isometric structures (A-D), with exactly one candidate matching all three views. The other half present the three views alone for direct reasoning.

## 2. Generation Prompt (verbatim)

```text
Build a Python script that generates 3000 "orthographic multi-view" puzzle images, testing 
classical engineering-drawing spatial reasoning — given the top, front, and side 
orthographic projections of a 3D voxel structure, reconstruct or verify properties of the 
original 3D shape. This is the natural inverse-task pairing with cube_structure_dataset_3000 
(which shows ONE isometric view and asks about occlusion within it); this dataset instead 
gives THREE flat 2D projections and asks the model to mentally reconstruct the 3D structure.

=== VISUAL SPEC ===

Canvas: 550-650px width, 450-500px height, DARK background (#1A1A1A), consistent with your 
dark-theme datasets.

- Generate a target 3D voxel structure (reuse generate_valid_structure() and gravity-support 
  logic from cube_structure_dataset_3000, 6-12 cubes).
- Render THREE separate orthographic projections in a row, each labeled clearly:
  a) TOP VIEW: looking straight down the z-axis — render as a 2D grid of filled squares 
     showing the (x,y) footprint (a cell is filled if ANY cube exists at that x,y column, 
     regardless of height).
  b) FRONT VIEW: looking along the y-axis — render as a 2D grid showing the (x,z) silhouette 
     (a cell filled if any cube exists at that x,z position, for any y).
  c) SIDE VIEW: looking along the x-axis — render as a 2D grid showing the (y,z) silhouette.
  Each view is a clean flat 2D grid diagram (thin outline squares, matching your wireframe 
  style), NOT an isometric/3D rendering — these are true flat orthographic silhouettes.
- Below or beside the three views, for ~50% of images, ALSO show 4 candidate isometric 3D 
  renders (A, B, C, D) — one of which is the TRUE structure that produces exactly these 
  3 views, and 3 distractors (structures that share at least one matching view but differ 
  in at least one other view, OR have the correct silhouettes but different actual cube count/
  arrangement achievable only if the views alone are ambiguous — use this ambiguity 
  deliberately as your hardest distractor type). For the other ~50% of images, skip the 
  candidate panel and instead just ask direct questions about the structure's properties 
  from the 3 views alone (no multiple choice) — this creates two puzzle sub-types of 
  differing difficulty.

=== GROUND TRUTH DATA PER IMAGE ===

- target_cubes: list of (x,y,z) voxel positions
- total_cube_count
- top_view_cells, front_view_cells, side_view_cells: the 2D silhouette grids for each 
  projection
- has_candidate_panel: true/false (which sub-type this image is)
- If has_candidate_panel: candidates list of {choice_label, cubes, matches_all_3_views: bool}, 
  correct_answer_choice
- is_uniquely_determined: true/false — whether the 3 given views uniquely determine the 
  cube structure, or whether multiple valid structures could produce the same 3 silhouettes 
  (a genuine and important property of orthographic projection — 3 views do NOT always 
  uniquely determine a 3D shape; compute this by checking whether any OTHER valid gravity-
  supported structure with the same total_cube_count also produces identical top/front/side 
  silhouettes)

=== 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many unit cells are filled in the top view?"
  ground_truth = count of filled cells in top_view_cells

LEVEL 2 - Basic Relational (always include):
  "Based on the three views shown, what is the minimum possible number of cubes in the 
  3D structure? Answer with a number in curly brackets."
  ground_truth = total_cube_count (by construction, using the actual generating structure — 
  note this is well-defined as the ACTUAL structure's count, framed as "minimum possible" 
  because in ambiguous cases a viewer might overcount if not careful, but ground truth is 
  always the true generating structure's count)

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "Which view (top, front, or side) shows the LARGEST filled area (most filled cells)?"
     ground_truth = whichever of the 3 views has the most filled cells
  b) IF has_candidate_panel: "Which candidate structure (A, B, C, or D) is consistent with 
     ALL THREE views shown? Answer with the letter."
     ground_truth = correct_answer_choice

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "Do these three views uniquely determine the 3D structure, or could a different 
     arrangement of cubes produce the exact same three views? Answer 'unique' or 
     'not unique'."
     ground_truth = "unique" if is_uniquely_determined else "not unique"
     (This is a genuinely hard, conceptually deep question — direct engagement with the 
     real mathematical property that orthographic views can be ambiguous)
  b) IF has_candidate_panel: "One of the incorrect candidates matches TWO of the three 
     views but not the third. Which view does it fail to match — top, front, or side?"
     ground_truth = the specific view where that distractor's silhouette differs
  c) "If you added one more cube directly on top of the tallest column in the structure, 
     which view(s) would change — top, front, side, or more than one? Answer accordingly."
     ground_truth: adding a cube on top of the tallest column never changes the top view 
     (footprint unchanged) but WILL change front and/or side view (height increases) — 
     compute precisely which of front/side actually changes based on that column's (x,y) 
     position, since it only affects the view(s) whose silhouette includes that x or y slice

=== METADATA, OUTPUT, VALIDATION (same pipeline pattern as your 19 existing datasets) ===

1. annotations.jsonl, images/orthographic_{index:04d}.png
2. flatten_annotations.py → dataset_final.csv (same schema/task mapping)
3. validate_orthographic_dataset.py:
   - Independently recompute top/front/side silhouettes from stored target_cubes via 
     projection (for each axis, project and take the union footprint), confirm exact 
     match with stored view grids
   - Independently re-verify is_uniquely_determined via actual search: enumerate 
     alternative gravity-valid structures with matching total_cube_count and check if any 
     produce identical 3-view silhouettes (bounded search — cap search space reasonably 
     given cube count range)
   - For has_candidate_panel images, re-verify each candidate's matches_all_3_views flag 
     by independently projecting that candidate's cubes and comparing to the target's 
     3 views
   - Confirm roughly 50/50 split on has_candidate_panel
   - Re-derive every question's ground truth, confirm exact match
4. --sample flag, 5 images — manually attempt to reconstruct the 3D structure from the 
   3 views for at least 2-3 samples before trusting at scale. This is a HIGH manual-check 
   priority category, same tier as cube-net and fold-punch — orthographic reconstruction 
   is exactly the kind of task where a subtle projection-axis mixup (e.g. swapping which 
   axis maps to "front" vs "side") would be silently wrong but internally self-consistent.

=== TECHNICAL NOTES ===

- Implement project_top(cubes), project_front(cubes), project_side(cubes) — each returning 
  a 2D boolean grid via set-based union projection along the relevant axis.
- Implement check_unique_determination(target_cubes, view_top, view_front, view_side) via 
  bounded enumeration of alternative valid structures.
- Reuse iso_project() and generate_valid_structure() from cube_structure_dataset_3000 for 
  the candidate-panel isometric renders.
- Reuse random.seed(i) per image for reproducibility.

Output as: generate_orthographic_dataset.py

=== README (7-section format) ===

Section 1: state this implements classical orthographic/multiview projection reasoning 
(third-angle projection, standard in engineering/technical drawing curricula), designed as 
the inverse-task complement to cube_structure_dataset_3000 in this suite — that dataset 
shows one 3D view and asks about occlusion within it; this dataset shows three 2D 
projections and asks for 3D reconstruction.

Known limitations: only 3 standard orthographic views (top/front/side), no axonometric or 
auxiliary views; is_uniquely_determined check uses a bounded search, not exhaustive 
enumeration, for larger cube counts; candidate panel distractors limited to the 4-choice 
format used elsewhere in the suite.

Reasoning skills tested: 3D reconstruction from multiple 2D projections, understanding 
projection ambiguity (multiple 3D shapes can share identical orthographic views), 
cross-view consistency checking, spatial consequence reasoning (how adding a cube affects 
different views differently).

Output as: generate_orthographic_dataset.py
```

## 3. Question design rationale

Every image has exactly four questions in increasing difficulty:

1. **Level 1 - description:** count filled cells in the top projection.
2. **Level 2 - basic relational:** infer the minimum number of gravity-supported cubes consistent with all three silhouettes.
3. **Level 3 - comparative/structural:** compare filled projection areas or select the sole candidate consistent with all views.
4. **Level 4 - compound:** determine reconstruction uniqueness, diagnose a candidate's failed view, or infer which projections change after adding a cube.

This progression separates direct visual counting from cross-view matching, constrained 3D reconstruction, and reasoning about projection ambiguity.

Two ambiguities in the source specification were resolved conservatively. The Level 2 answer is the **true mathematical minimum** over all gravity-supported structures matching the views, because the generating target can contain more cubes than the views force. Likewise, `is_uniquely_determined` ranges over all matching gravity-supported structures, not only structures with the target's hidden cube count. The narrower same-count result is retained separately as `is_uniquely_determined_same_count`.

## 4. Ground-truth generation and validation

Top, front, and side cells are deterministic set projections of the target voxel set along the z, y, and x axes respectively. Gravity-supported structures are height maps over the top-view footprint. A finite constraint search assigns each occupied column a height while enforcing the exact front row-maxima and side column-maxima. This search provides the minimum possible cube count and whether another valid height assignment exists.

`validate_orthographic_dataset.py` is separate from the generator and independently:

- reconstructs all three projections from raw `target_cubes`;
- checks cube uniqueness, the 6-12 count range, and gravity support;
- re-runs the bounded/exact height-map search for minimum count and uniqueness;
- reprojects every candidate and verifies each per-view match flag;
- confirms exactly one candidate matches all views and at least one distractor matches exactly two;
- re-derives all four question answers; and
- reads the final PNG and samples every rendered view-grid cell to detect image/annotation divergence.

Final full validation result:

```text
Total images checked: 3000
Total mismatches found: 0
Summary: PASS
```

## 5. Reasoning skills tested

- 3D reconstruction from multiple 2D projections
- Axis-aware top/front/side projection interpretation
- Projection ambiguity and non-unique reconstruction
- Cross-view candidate consistency checking
- Minimum-cardinality reconstruction under gravity constraints
- Spatial consequence reasoning after adding a voxel

## 6. Known limitations

- Only the three standard top, front, and side views are used; no auxiliary or axonometric views are supplied as evidence.
- Shapes contain only axis-aligned unit voxels and clean synthetic line art.
- All structures are gravity-supported vertical columns; overhangs and bridges are excluded.
- Candidate panels use a fixed four-choice A-D format.
- Search is exact within the finite height bounds encoded by the three silhouettes, but the small 6-12 cube regime does not represent large engineering assemblies.
- Orthographic silhouettes omit hidden edges and internal material, so some structures are intentionally non-unique.

## 7. Files and schema

```text
orthographic_dataset_3000/
  images/orthographic_XXXX.png
  annotations.jsonl
  dataset_final.csv
  dataset_final.jsonl
  contact_sheet.png
  human_calibration/review_sheet.png
  generation_prompt.txt
  generate_orthographic_dataset.py
  validate_orthographic_dataset.py
  flatten_annotations.py
  make_contact_sheet.py
  validation_report.txt
  tests/test_orthographic.py
```

`annotations.jsonl` stores the full target voxel list, projection-cell lists, candidates, ambiguity/minimum-search results, render metadata, and four question records. Each question contains `question_id`, `question_text`, `question_type`, `ground_truth`, `answer_format`, and `difficulty_level`.

The flattened `dataset_final.csv` and `dataset_final.jsonl` use exactly these columns:

```text
task, image, prompt, groundtruth, metadata
```

The compact metadata contains only `difficulty_score`, `total_cube_count`, `minimum_possible_cube_count`, `has_candidate_panel`, `is_uniquely_determined`, and `seed`; full voxel coordinates remain only in raw annotations.

Example flattened row:

```csv
Image Description,orthographic_0001.png,How many unit cells are filled in the top view?,5,"{""difficulty_score"":0.31,""has_candidate_panel"":false,""is_uniquely_determined"":false,""minimum_possible_cube_count"":7,""seed"":1,""total_cube_count"":8}"
```
