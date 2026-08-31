# Symmetry Breaking Dataset

## 1. Dataset overview

This dataset contains 3,000 reproducible dark-theme diamond-pattern images for exhaustive visual comparison. It contains exactly 1500 broken and 1500 unbroken patterns, with four difficulty-ordered questions per image and 12,000 flattened rows. Every image has 6 or 8 shapes, within the specified 6–9 range.

## 2. Full generation prompt

```text
Build a Python script that programmatically generates a dataset of 3000 "symmetry breaking" 
puzzle images, for testing exhaustive visual comparison — detecting a single deliberately 
altered element within an otherwise regular/symmetric arrangement.

=== VISUAL SPEC (matches reference image style) ===

Each image is a canvas (400-450px range) with a DARK background (#1A1A1A), consistent with 
your other dark-theme datasets (cube_net, shadow_inference, impossible_object).

- Draw a grid arrangement of N identical small shapes (diamonds/rotated squares, matching 
  the reference image), arranged in a symmetric layout: pick ONE symmetry type per image 
  from {rotational (2-fold, 3-fold, 4-fold, 6-fold), horizontal mirror, vertical mirror, 
  both-axis mirror (4-fold reflective)}. Grid size: 6-9 shapes per image, positioned 
  according to the chosen symmetry group around a canvas center point.
- Shape style: thin outline (1-1.5px stroke, muted purple/indigo color matching reference), 
  NO fill for all shapes EXCEPT exactly one shape per image (in the "broken" images — see 
  below), which gets a SOLID fill in the same color family (matching reference image's 
  filled purple diamond).
- Randomize per image whether the pattern is: 
  (a) ~50% "broken" — one shape is altered in ONE of several ways: filled instead of 
  outline (matching reference), OR rotated differently than its symmetric position requires, 
  OR shifted slightly off its correct symmetric position, OR sized differently (slightly 
  larger/smaller) than the others. Randomize WHICH type of break is used.
  (b) ~50% "unbroken" — perfectly symmetric, no altered element (all outline, all correctly 
  positioned/sized/rotated) — this is the essential negative-control class, same principle 
  as the impossible-object dataset's possible/impossible balance.

=== GROUND TRUTH DATA TO TRACK PER IMAGE ===

- symmetry_type: "rotational_2" | "rotational_3" | "rotational_4" | "rotational_6" | 
  "mirror_horizontal" | "mirror_vertical" | "mirror_both"
- is_broken: true/false
- break_type: "fill" | "rotation" | "position" | "size" | null (if unbroken)
- broken_shape_index: index of the altered shape, or null
- broken_shape_position: [x,y] of the altered shape, or null
- num_shapes: total shape count
- shapes: full list of {index, center, rotation_angle, size, filled: bool}

=== GROUND TRUTH GENERATION — EXACTLY 4 QUESTIONS PER IMAGE ===

LEVEL 1 - Simple Description (always include):
  "How many shapes are in this pattern?"
  ground_truth = num_shapes

LEVEL 2 - Basic Relational (always include — core question of this dataset):
  "Is this pattern symmetric, or is there an element that breaks the symmetry? 
  Answer 'symmetric' or 'broken'."
  ground_truth = "broken" if is_broken else "symmetric"

LEVEL 3 - Comparative/Structural (pick based on is_broken):
  - If is_broken: "Which shape breaks the symmetry — describe its approximate location 
    (top-left, top-right, center, bottom-left, bottom-right, etc.)."
    ground_truth = location bucket derived from broken_shape_position relative to canvas center
  - If NOT broken: "What type of symmetry does this pattern have — rotational or 
    mirror/reflective? Answer 'rotational' or 'mirror'."
    ground_truth = derived from symmetry_type (rotational_* → "rotational", mirror_* → "mirror")

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "If is_broken: In what way does the odd shape differ from the others — is it 
     filled instead of outlined, rotated at a different angle, shifted out of position, 
     or a different size? Answer with one of those four options."
     ground_truth = break_type (mapped to readable label)
     (only for is_broken=true images; for is_broken=false, use option (b) below)
  b) "If this pattern were rotated 90 degrees, would it look identical to its current 
     appearance? Answer yes or no."
     ground_truth: depends on symmetry_type AND is_broken. For unbroken rotational_4 
     or rotational_6 patterns (evenly divide 90 degrees rotation into their symmetry), 
     answer "yes". For unbroken mirror-only or rotational_2/3 patterns, answer "no" 
     (90-degree rotation isn't a symmetry operation for those groups). For ANY broken 
     pattern, answer "no" (the break itself prevents the rotation from mapping the 
     pattern onto itself, regardless of underlying symmetry type) — compute this 
     precisely per symmetry_type, don't hardcode a guess
  c) "How many of the shapes in this pattern are positioned at the exact mirror-image 
     location of another shape (i.e., form a symmetric pair)? Answer with a number." 
     ground_truth = count of shapes with a valid symmetric partner under the pattern's 
     defined symmetry_type (for broken patterns, the altered shape typically loses its 
     partnership — compute this exactly from shape positions, not by assumption)

=== METADATA, OUTPUT, VALIDATION (same pipeline as previous 8 datasets) ===

1. annotations.jsonl with full metadata + 4-question array
2. images/symmetry_pattern_{index:04d}.png
3. flatten_annotations.py → dataset_final.csv (same schema, same difficulty_level → task 
   name mapping as all previous datasets)
4. validate_symmetry_dataset.py:
   - Independently RE-CHECK symmetry from raw shape data: for each image, apply the 
     claimed symmetry_type's transformation (rotate by 360/n degrees, or reflect across 
     the relevant axis) to every shape's position/rotation/size, and verify whether the 
     transformed pattern maps onto itself (within a small tolerance) — this confirms 
     is_broken/symmetric status independently, not by re-trusting the generation flag
   - For broken images, confirm the identified broken_shape_index is really the one (and 
     only one) shape that breaks the symmetry — no accidental second break introduced by 
     the randomization
   - Confirm roughly 50/50 broken/unbroken split
   - Confirm distribution across all symmetry types and all break types is reasonably even
   - Re-derive every question's ground truth from stored geometry, confirm exact match
5. --sample flag for 5 images — manually verify symmetry-type and broken/unbroken status 
   by eye for all 5 before trusting at scale (same caution level as the impossible-object 
   and cube-net datasets, since this again involves a geometric TRUTH claim, not just a count)

=== README (same 7-section format) ===

Known limitations to state: only diamond/rotated-square shapes used (no other shape types); 
only 4 break types tested (fill, rotation, position, size) — no compound breaks (multiple 
simultaneous alterations); symmetry types limited to standard rotational (2/3/4/6-fold) 
and mirror (horizontal/vertical/both) groups, no more exotic symmetry groups (glide 
reflection, etc.); grid sizes limited to 6-9 shapes.

Reasoning skills tested: exhaustive visual comparison (no shortcut — every element must 
be checked against its symmetric counterpart), symmetry-type classification, precise 
localization of anomalies, understanding how a local perturbation affects global pattern 
properties (Level 4b's 90-degree rotation question).

Output as: generate_symmetry_pattern_dataset.py
```

## 3. Question design rationale

The levels progress from shape counting through symmetry-break detection, anomaly localization or symmetry-family classification, and perturbation/rotation/partner reasoning. Actual usage:

- Level 1: `shape_count` 3000
- Level 2: `symmetry_status` 3000
- Level 3: `broken_location` 1500, `symmetry_family` 1500
- Level 4: `break_type` 1500, `symmetric_partner_count` 1500

Symmetry distribution:

- `mirror_both`: 428
- `mirror_horizontal`: 428
- `mirror_vertical`: 428
- `rotational_2`: 429
- `rotational_3`: 429
- `rotational_4`: 429
- `rotational_6`: 429

Break distribution (`None` denotes unbroken):

- `None`: 1500
- `fill`: 375
- `position`: 375
- `rotation`: 375
- `size`: 375

## 4. Ground truth generation and validation

Unbroken patterns are built from complete geometric orbits under their claimed rotation or reflection. A broken image changes exactly one orbit member's fill, orientation, position, or size. The independent validator applies the claimed transformations to raw shape records, matches transformed centers and attributes within 0.08 pixels/degrees, confirms the identified anomaly lies in the sole affected orbit, recomputes positional partners, and re-derives every answer.

Final result: **3,000/3,000 images passed with 0 mismatches**. The five-image sample covered both classes and five symmetry groups and was visually inspected before full generation.

## 5. Known limitations

- Only diamonds/rotated squares are used; no other shape families are included.
- Only fill, rotation, position, and size breaks are tested, with no compound anomalies.
- Symmetry is limited to 2/3/4/6-fold rotation and horizontal/vertical/both-axis reflection; glide reflections and other groups are excluded.
- Pattern sizes are limited to 6–9 shapes; the realized orbit-compatible counts are 6 and 8.
- Location answers use coarse regions rather than exact coordinates.

## 6. Reasoning skills tested

- Exhaustive element-by-element visual comparison
- Symmetry-type and symmetry-family classification
- Precise localization and characterization of a single anomaly
- Understanding how local perturbations change global invariance
- Matching transformed objects while accounting for orientation and scale

## 7. File structure, schema, and worked example

```text
symmetry_pattern_dataset_3000/
├── images/
├── annotations.jsonl
├── dataset_final.csv
├── dataset_final.jsonl
├── generate_symmetry_pattern_dataset.py
├── validate_symmetry_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── generation_prompt.txt
└── README.md
```

Raw annotations retain symmetry type, every shape's center/orientation/size/fill/orbit, anomaly data, partner count, seed, difficulty score, and questions. Flattened metadata keeps only difficulty, symmetry type, break status/type, count, and seed.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | symmetry_pattern_0001.png | How many shapes are in this pattern? | 6 |
| Basic Relational Reasoning | symmetry_pattern_0001.png | Is this pattern symmetric, or is there an element that breaks the symmetry? Answer 'symmetric' or 'broken'. | broken |
| Comparative Reasoning | symmetry_pattern_0001.png | Which shape breaks the symmetry? Answer with its approximate location, such as top-left, top-right, bottom-left, bottom-right, or center. | bottom-left |
| Compound Reasoning | symmetry_pattern_0001.png | In what way does the odd shape differ — filled instead of outlined, rotated at a different angle, shifted out of position, or a different size? | filled |
