# Isometric Cube Structure Dataset

Current version: `cube-structure-2.0.0`; the initial build is preserved under `archive/v1/`. Every v2 record declares `vertical_axis: "z"`, and both `max_height`/`cubes_per_layer` and the Level 5 180-degree rotation use that same z axis. The isometric projection maps increasing z upward on screen. This agrees with `combination3d_dataset_3000`, whose corrected v2 convention also uses z as visual vertical.

V2 rejects `has_ambiguous_visual_floater` scenes. The flag condition is a raised cube whose supporting cube is geometrically present but has no face visible from the fixed view. The previous build contained 2,393 flagged scenes; the released v2 contains zero. A second PNG guard requires every cube classified as visible by geometry to retain recoverable face pixels after draw ordering. Independent validation recovers visible/hidden status for all 3,000 PNGs and independently recomputes opposite-view occlusion with zero Level 5 mismatches.

`cluster_counts` counts every cube assigned to a color cluster, including cubes hidden in the render. `hidden_members_per_cluster` reports those hidden members explicitly; cluster membership is geometric metadata and not merely a count of visible colored components.

## Dataset overview

This dataset contains 3,000 fully synthetic, programmatically rendered isometric voxel structures and 15,000 programmatically labeled questions. No image or label was human-drawn or manually estimated.

## Generation Prompt (verbatim)

```text
Build a Python script that programmatically generates a dataset of 3000 "isometric cube 
structure" images, for testing 3D spatial reasoning, mental rotation, and occlusion 
inference in AI models.

=== VISUAL SPEC ===

Each image is a square canvas (400-430px range, randomize) with a plain off-white/cream 
background (#F1EFE8 or similar), matching the reference image style.

- Represent 3D structures as voxel/cube assemblies on an isometric grid, drawn using 
  rhombus faces (top, left, right) per visible cube face — standard isometric cube 
  rendering technique (each cube = 3 parallelograms: top face lightest shade, left face 
  medium shade, right face darkest shade, all from the SAME muted teal/slate-blue color 
  ramp, matching the reference image's blue-gray palette).
- Structure generation: build each structure as a set of cube positions on a 3D integer 
  grid (x, y, z), starting from a random footprint of 4-10 base cubes and stacking 
  additional cubes on top following gravity rules (a cube at height h can only exist if 
  there is a cube directly beneath it at height h-1, OR it's a height-0 base cube).
- Randomize per image:
  - Total cube count: between 8 and 22 cubes.
  - Footprint shape/irregularity (not just a solid rectangular block — allow L-shapes, 
    staggered towers, cubes with gaps, matching the organic/irregular look of the 
    reference image).
  - Presence of "floating-looking but actually supported" cubes — i.e. cubes that appear 
    ambiguous from this viewing angle because their support cube is hidden behind other 
    cubes. This is what makes the puzzle hard: some structurally valid cubes will look 
    like they might be floating unless the viewer mentally reconstructs the hidden support.
  - Isometric camera angle: keep FIXED at a standard 3-face-visible isometric projection 
    (30-degree angle) for all images — do NOT randomize viewing angle, since ground truth 
    for "hidden cube" questions depends on a consistent, known viewpoint.
  - Color: default single teal/slate ramp for ~75% of images; for ~25% of images, use TWO 
    different color ramps to distinguish two connected sub-clusters of cubes (e.g. one 
    "arm" of the structure in teal, another in warm gray) to support cluster-counting 
    questions.

- Every generated structure MUST be physically valid (no floating cubes with no support 
  chain to the ground) — this is a hard constraint, verify programmatically before rendering.
- Render with thin dark outline strokes (0.5-1px) on every visible face edge, matching 
  the reference image's clean line-art look. No drop shadows, no gradients.

=== GROUND TRUTH DATA TO TRACK PER IMAGE ===

Store the full voxel grid: list of all cube positions {x, y, z}, plus for each cube whether 
it is fully visible, partially occluded, or fully hidden from the fixed isometric viewpoint 
(compute via standard isometric visibility/painter's-algorithm occlusion check).

Also compute and store:
  - total_cube_count (ground truth for counting questions)
  - visible_cube_count (cubes with at least one face visible)
  - hidden_cube_count (cubes with zero visible faces from this viewpoint)
  - base_layer_count (cubes at z=0, i.e. touching the ground)
  - max_height (number of layers/z-levels)
  - cubes_per_layer: dict of {z_level: count}
  - color_cluster_count: 1 or 2 depending on whether color splitting was used

=== GROUND TRUTH GENERATION — EXACTLY 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many cubes make up this structure in total? Answer with a number in curly 
  brackets, e.g. {12}."
  ground_truth = total_cube_count
  (This requires inferring hidden cubes too, not just counting visible faces — 
  make this explicit in a short accompanying instruction line if needed, or keep 
  it implicit and let this be the "hardest simple-sounding question" by design.)

LEVEL 2 - Basic Relational (always include):
  "How many cubes are touching the ground (bottom layer)? Answer with a number in 
  curly brackets, e.g. {5}."
  ground_truth = base_layer_count

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "How many total layers (levels of height) does this structure have? Answer with 
     a number in curly brackets, e.g. {3}."
     ground_truth = max_height
  b) "Which layer (counting from the ground as layer 1) has the most cubes? Answer 
     with a number in curly brackets, e.g. {2}."
     ground_truth = the z-level (1-indexed) with the highest cube count 
     (if tied, pick the lowest such layer and note tie in metadata)
  c) "If color clusters are present: how many cubes are in the [color_name] cluster?" 
     ground_truth = count of cubes in that color group (only use when 
     color_cluster_count == 2; otherwise fall back to (a))

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "How many cubes in this structure are completely hidden from view (not visible 
     from any angle in this image)? Answer with a number in curly brackets, e.g. {2}."
     ground_truth = hidden_cube_count
  b) "Is this structure physically stable — i.e., does every cube have support beneath 
     it with no floating cubes? Answer yes or no."
     ground_truth = "yes" always (since generation enforces validity) — BUT for ~10% 
     of images, deliberately render one additional cube in a position that VISUALLY 
     appears to float relative to camera angle even though it may or may not be 
     supported, to test whether the model over- or under-trusts visual impression. 
     Track ground truth precisely based on actual generated structure, not visual 
     impression.
  c) "If this structure were rotated 180 degrees around the vertical (z) axis, how 
     many currently-hidden cubes would become visible? Answer with a number in curly 
     brackets, e.g. {3}."
     ground_truth = compute by re-running the visibility/occlusion check from the 
     opposite viewpoint (180-degree rotation) and counting cubes that flip from 
     hidden->visible

=== METADATA (per image) ===

{
  "id": "cube_structure_0001",
  "image_path": "images/cube_structure_0001.png",
  "canvas_size": [412, 420],
  "total_cube_count": 15,
  "visible_cube_count": 12,
  "hidden_cube_count": 3,
  "base_layer_count": 6,
  "max_height": 4,
  "cubes_per_layer": {"1": 6, "2": 4, "3": 3, "4": 2},
  "color_cluster_count": 1,
  "has_ambiguous_visual_floater": false,
  "seed": 1,
  "difficulty_score": <float, compute from: total_cube_count, hidden_cube_count 
    (more hidden = harder), max_height, color_cluster_count, has_ambiguous_visual_floater 
    (adds difficulty)>,
  "cubes": [
    {"x": 0, "y": 0, "z": 0, "visible": true, "color_cluster": "A"},
    ...
  ]
}

=== OUTPUT FORMAT (same pipeline as previous two datasets) ===

1. /dataset/annotations.jsonl — one JSON object per image with full metadata + 4-question 
   array (question_id, question_text, question_type, ground_truth, answer_format, 
   difficulty_level 1-4)
2. /dataset/images/cube_structure_{index:04d}.png
3. flatten_annotations.py → dataset_final.csv with columns: task, image, prompt, 
   groundtruth, metadata
   task mapping by difficulty_level:
     1 → "Image Description"
     2 → "Basic Relational Reasoning"
     3 → "Comparative Reasoning"
     4 → "Compound Reasoning"
   metadata column = compact JSON string with ONLY: difficulty_score, total_cube_count, 
   max_height, color_cluster_count, has_ambiguous_visual_floater, seed (exclude the full 
   "cubes" voxel array — keep that only in raw annotations.jsonl)
4. validate_cube_dataset.py: re-parses annotations.jsonl, re-derives every ground_truth 
   from the stored voxel/cubes array (recompute visibility, hidden count, layer counts, 
   180-degree-rotation visibility), flags mismatches. Also confirm: every image file 
   exists, every structure passes the gravity/support validity check, no cube position 
   is duplicated.
5. --sample flag for 5 test images first.

=== TECHNICAL NOTES ===

- Use svgwrite + cairosvg (or Pillow) for isometric rendering. Implement 
  iso_project(x, y, z) -> (screen_x, screen_y) using standard isometric transform 
  (30-degree axes).
- Implement is_cube_visible(cube, all_cubes, viewpoint) using painter's algorithm: 
  a cube face is hidden if fully covered by a nearer cube's face from the given viewpoint 
  — compute per-face, not just per-cube, but a cube counts as "visible" if AT LEAST ONE 
  of its 3 outward faces (top/left/right, or top/left/right from the 180-rotated view for 
  the Level 4c question) is unobstructed.
- Implement generate_valid_structure(num_cubes) using a randomized growth algorithm: 
  start with a random base footprint, then iteratively add cubes only at positions where 
  (x,y,z-1) is already occupied or z==0, until num_cubes is reached. Reject and retry if 
  the algorithm gets stuck before reaching the target count.
- Reuse random.seed(i) per image index for reproducibility.

Output the full script as: generate_cube_structure_dataset.py

=== README REQUIREMENT (for paper documentation) ===

In addition to the dataset files, generate a README.md in the dataset root folder that 
documents, in a format suitable for directly referencing in an academic paper's 
"Dataset Construction" or "Methodology" section:

1. **Dataset overview**: total image count, total question count, generation date, 
   generation method (fully synthetic/programmatic, not human-drawn or human-labeled).

2. **Full verbatim text of the generation prompt used** — reproduce the ENTIRE prompt 
   given to you (this exact prompt, word for word) in a clearly marked code block titled 
   "Generation Prompt (verbatim)", so the methodology is fully reproducible and citable.

3. **Question design rationale**: explain the 4-level difficulty structure (Level 1 = 
   simple description/counting, Level 2 = basic relational, Level 3 = comparative/
   structural, Level 4 = complex/compound reasoning requiring occlusion inference or 
   mental rotation) and why this progression was chosen (to measure reasoning depth, 
   not just perception).

4. **Ground truth generation method**: state clearly that ALL ground truth values were 
   derived programmatically and deterministically from the underlying 3D voxel data used 
   to render each image (not estimated, not manually labeled) — and that every value was 
   independently re-verified via a separate validation script that recomputes each answer 
   from raw geometry and confirms it matches the stored label, with the final validation 
   pass rate reported (e.g. "3000/3000 images validated, 0 mismatches").

5. **Known limitations**: state explicitly — fixed isometric camera angle only (no 
   varying viewpoints), simple cube/voxel primitives only (no other 3D shapes), 
   synthetic clean line-art rendering style only (not photorealistic), and any other 
   limitations you identify during generation.

6. **Reasoning skills tested**: list explicitly — object counting under occlusion, 
   amodal 3D completion (inferring hidden support structure), layer/height reasoning, 
   mental rotation (180-degree viewpoint change), and physical plausibility/stability 
   judgment.

7. **File structure and schema**: document the folder layout and the exact CSV/JSONL 
   column schema (task, image, prompt, groundtruth, metadata) with one worked example row.

Format this as clean Markdown suitable for direct inclusion or adaptation into a paper's 
appendix or supplementary methodology section.
```

## Question design rationale

Each image has four ordered levels: Level 1 counts the complete structure, Level 2 reasons about the ground layer, Level 3 examines layers or color clusters, and Level 4 tests occlusion inference, stability, or a 180-degree mental viewpoint change. This progression measures reasoning depth rather than perception alone.

## Ground truth generation

All labels are derived deterministically from the same integer voxel coordinates used for rendering. Cube totals, supports, layers, visibility, hidden cubes, and opposite-view visibility are recomputed by `validate_cube_dataset.py`. Final result:

```text
Total images checked: 3000
Total mismatches found: 0
Summary: PASS
```

## Reasoning skills tested

- Object counting under occlusion
- Amodal 3D completion and hidden-support inference
- Layer and height reasoning
- Mental rotation through a 180-degree viewpoint change
- Physical plausibility and stability judgment

## Known limitations

- One fixed isometric camera orientation (plus a computed 180-degree metadata viewpoint)
- Voxel/cube primitives only
- Clean synthetic technical line art rather than photorealism
- Orthographic projection without perspective or illumination variation
- Visibility follows the documented fixed-view voxel occlusion model

## Files and schema

```text
cube_structure_dataset_3000/
  images/cube_structure_XXXX.png
  annotations.jsonl
  dataset_final.csv
  dataset_final.jsonl
  validation_report.txt
  generation_prompt.txt
  generate_cube_structure_dataset.py
  validate_cube_dataset.py
  flatten_annotations.py
  write_cube_readme.py
  README.md
```

Flattened columns are exactly `task,image,prompt,groundtruth,metadata`. Example:

```csv
Image Description,cube_structure_0001.png,"How many cubes make up this structure in total? Answer with a number in curly brackets, e.g. {12}.",15,"{"difficulty_score":0.42,"total_cube_count":15,"max_height":4,"color_cluster_count":1,"has_ambiguous_visual_floater":false,"seed":1}"
```

Raw `annotations.jsonl` retains full cube coordinates and all four question records. Flattened metadata intentionally excludes the voxel array.
