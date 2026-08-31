# Depth and Height Perception Dataset

## 1. Dataset overview

This dataset directly extends [GeoMeter](https://arxiv.org/abs/2408.11748)'s documented depth-perception and height-perception failure cases, using a similarly styled but larger and more systematically difficulty-tiered synthetic dataset. It contains 3,000 unique dark-theme images: 1,500 depth-ordering scenes with explicit perspective size/vertical-position cues and 1,500 flat stack-height scenes. Each current item has five questions (15,000 flattened rows). The category is therefore mixed **Projective Geometry / Height Comparison**; exactly half contains projective depth content.

## 2. Full generation prompt

```text
Build a Python script that generates 3000 "depth and height perception" images, testing 
whether models can correctly judge relative distance-from-camera and relative height 
using perspective/size cues alone — directly extending GeoMeter's documented failure 
cases (e.g. models misjudging which of two objects is closer, or which block stack is 
taller).

=== VISUAL SPEC ===

Canvas: 550-650px width, 350-400px height, DARK background (#1A1A1A), consistent with 
your dark-theme datasets.

Generate TWO distinct image types, randomized ~50/50 per image:

TYPE A - "Depth ordering" (which object is closer to camera):
- Place 2-4 simple solid-colored shapes (circle/sphere, square/cube, triangle/cone — 
  filled, not wireframe, so size cues read clearly) scattered across the canvas at 
  different vertical positions (higher on canvas = further away, lower = closer, standard 
  perspective convention) and different sizes (closer objects rendered larger, farther 
  objects smaller, using a consistent perspective scale factor — e.g. size = base_size * 
  (1 - 0.4 * normalized_depth)).
- Each shape gets a distinct color (from a fixed palette matching reference: teal, 
  magenta/pink, orange, blue, purple).
- Store each object's TRUE depth value (0.0 = closest, 1.0 = farthest) used to generate 
  its size/position — this is ground truth, not inferred after the fact.

TYPE B - "Stack height comparison":
- Draw 2-4 vertical stacks of small colored rectangular blocks (like stacked bricks), 
  positioned at different horizontal locations across the canvas, each stack built from 
  a randomized number of blocks (2-7 blocks per stack).
- Each stack's blocks share one random color for that stack (distinct color per stack, 
  same palette as Type A).
- Store each stack's true block_count and computed pixel height.

=== GROUND TRUTH DATA PER IMAGE ===

Type A: 
- objects: list of {color, shape_type, depth_value, canvas_position, rendered_size}
- closest_object_color, farthest_object_color
- depth_ordering: list of colors sorted closest-to-farthest

Type B:
- stacks: list of {color, position_x, block_count, pixel_height}
- tallest_stack_color, shortest_stack_color
- height_ordering: list of colors sorted tallest-to-shortest

=== 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

FOR TYPE A (depth ordering) IMAGES:

LEVEL 1 - Simple Description:
  "How many objects are shown in this scene?"
  ground_truth = count of objects

LEVEL 2 - Basic Relational:
  "Which object is closer to the camera: the {color1} {shape1} or the {color2} {shape2}?" 
  (randomly pick 2 of the objects present)
  ground_truth = the color of whichever has the lower depth_value

LEVEL 3 - Comparative/Structural:
  "Rank all objects in this scene from closest to farthest, by color."
  ground_truth = depth_ordering (full list)

LEVEL 4 - Complex/Compound:
  "If the {color} object moved twice as far from the camera as its current distance, 
  would it still appear larger, smaller, or about the same size as the {color2} object? 
  Answer 'larger', 'smaller', or 'same'."
  ground_truth: compute new_depth = min(1.0, depth_value * 2), derive new_size from the 
  same perspective formula, compare against the other named object's current rendered_size

FOR TYPE B (stack height) IMAGES:

LEVEL 1 - Simple Description:
  "How many separate stacks of blocks are shown in this image?"
  ground_truth = number of stacks

LEVEL 2 - Basic Relational:
  "Which stack is taller: the {color1} stack or the {color2} stack?" (pick 2 stacks)
  ground_truth = color of whichever has more blocks (or greater pixel_height if block 
  sizes ever vary — keep block size FIXED across all stacks for this dataset so height 
  is purely a function of block_count, avoiding a confound)

LEVEL 3 - Comparative/Structural:
  "Rank all stacks from tallest to shortest, by color."
  ground_truth = height_ordering (full list)

LEVEL 4 - Complex/Compound:
  "How many total blocks are there across all stacks combined?"
  ground_truth = sum of all block_counts
  OR (randomize between this and):
  "If you moved 2 blocks from the tallest stack to the shortest stack, would the shortest 
  stack become the new tallest? Answer yes or no."
  ground_truth = compute (shortest_count + 2) > (tallest_count - 2), handle ties per your 
  existing tie-handling convention (require a UNIQUE new max, else skip/reroll this question)

=== METADATA, OUTPUT, VALIDATION (same pipeline pattern as your other 10 datasets) ===

1. annotations.jsonl, images/depth_height_{index:04d}.png
2. flatten_annotations.py → dataset_final.csv (same schema, same difficulty_level → task 
   name mapping)
3. validate_depth_height_dataset.py:
   - Independently recompute each object's expected rendered size from stored depth_value 
     and the perspective formula, confirm actual rendered pixel size matches within tolerance
   - Independently recompute each stack's expected pixel_height from block_count and fixed 
     block size, confirm match
   - Re-derive every question's ground truth from stored data, confirm exact match
   - Confirm roughly 50/50 Type A / Type B split
4. --sample flag, 5 images of EACH type (10 total) — manually verify depth ordering and 
   stack height by eye. This is a repeat-offender risk category (same class of bug as the 
   shadow dataset — visual perspective cues are easy to get subtly wrong even when the 
   underlying numbers are internally consistent), so treat the visual check as mandatory, 
   not optional, given what just happened with shadow_inference.

=== README (7-section format, citing GeoMeter) ===

Section 1: state this dataset directly extends GeoMeter's (arXiv 2408.11748) documented 
depth-perception and height-perception failure cases, using a similarly styled but larger 
and more systematically difficulty-tiered synthetic dataset.

Known limitations: perspective/depth cues are a simplified linear size-scaling model, not 
true camera-projection math; Type B block stacks use uniform block size (no size variance 
confound, but also less visually realistic); only 2-4 objects/stacks per image.

Reasoning skills tested: relative depth judgment from size cues, relative height comparison, 
multi-object ranking, counting, hypothetical/counterfactual size reasoning (Level 4a).

Output as: generate_depth_height_dataset.py
```

## 3. Question design rationale

Depth scenes progress from counting through pair comparison, full ranking, and counterfactual distance scaling. Stack scenes progress through counting, pair comparison, full ranking, and total/transfer arithmetic. Actual usage:

- Level 1: `object_count` 1500, `stack_count` 1500
- Level 2: `pair_closer` 1500, `pair_taller` 1500
- Level 3: `depth_ordering` 1500, `height_ordering` 1500
- Level 4: `counterfactual_size` 1500, `total_blocks` 991, `transfer_blocks` 509

## 4. Ground truth generation and validation

For depth scenes, `rendered_size = base_size × (1 − 0.4 × depth)`, with depth 0 closest and 1 farthest. Vertical position independently reinforces the same ordering: farther objects appear higher. Depths are separated by at least 0.12 to avoid ambiguous comparisons. Stack blocks use fixed 54×21-pixel bodies and a 24-pixel pitch, so `pixel_height = (count−1)×24 + 21`.

The independent validator recomputes all expected sizes, heights, rankings, transfers, and counterfactual answers. Crucially, it reads every saved PNG, segments each unique RGB object within its predicted region, and compares the measured bounding box against the expected rendered size/height. Final result: **3,000/3,000 images passed with 0 mismatches**. Five samples of each type were visually inspected before full generation.

## 5. Known limitations

- Perspective uses a simplified linear size-scaling model rather than a calibrated projective camera.
- Block stacks use uniform block dimensions, removing size confounds but reducing realism.
- Images contain only 2–4 objects or stacks.
- Depth scenes use color and primitive shape diversity but no texture, lighting, or occlusion cues.
- Stack counts are unique within each image to keep tallest/shortest answers unambiguous.

## 6. Reasoning skills tested

- Relative depth judgment from size and vertical-position cues
- Relative height comparison
- Multi-object ordering and ranking
- Object, stack, and block counting
- Counterfactual size reasoning under changed distance
- Arithmetic state updates after transferring blocks

## 7. File structure, schema, and worked example

```text
depth_height_dataset_3000/
├── images/
├── annotations.jsonl
├── dataset_final.csv
├── dataset_final.jsonl
├── generate_depth_height_dataset.py
├── validate_depth_height_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── review_samples_contact_sheet.png
├── generation_prompt.txt
└── README.md
```

Raw depth records store depth, position, shape, RGB, rendered size, ordering, and base scale. Stack records store count, position, fixed dimensions, pixel height, and ordering. Flattened metadata contains only difficulty, scene type, and seed.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | depth_height_0001.png | How many objects are shown in this scene? | 2 |
| Basic Relational Reasoning | depth_height_0001.png | Which object is closer to the camera: the teal circle or the orange square? | teal |
| Comparative Reasoning | depth_height_0001.png | Rank all objects in this scene from closest to farthest, by color. | teal, orange |
| Compound Reasoning | depth_height_0001.png | If the orange object moved twice as far from the camera as its current distance, would it appear larger, smaller, or about the same size as the teal object? | smaller |
