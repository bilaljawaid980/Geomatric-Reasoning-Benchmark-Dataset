# Shadow Inference Dataset

## 1. Dataset overview

This dataset contains 3,000 reproducible dark-theme images for inverse physical reasoning from projected shadows. Scenes contain one to three colored wireframe primitives and exactly four difficulty-ordered questions, totaling 12,000 flattened rows. 620 scenes (20.7%) contain one deliberately inconsistent shadow.

## 2. Full generation prompt

```text
Build a Python script that programmatically generates a dataset of 3000 "shadow inference" 
puzzle images, for testing inverse physical reasoning — inferring an invisible cause (light 
direction) from a visible effect (shadow shape and position).

=== VISUAL SPEC (matches reference image style) ===

Each image is a canvas (650-700px width, 350-400px height range) with a DARK background 
(#1A1A1A or similar), matching the reference image's theme (consistent with cube_net_dataset's 
dark theme choice).

- Draw a horizontal ground line (thin gray line, ~0.5px, spanning most of the canvas width, 
  positioned roughly 75-80% down the canvas height).
- Place 1 to 3 simple geometric objects ABOVE the ground line: choose from {cube (isometric 
  wireframe outline, no fill), sphere (circle outline, no fill), cone (triangle outline), 
  cylinder (rectangle with ellipse cap)} — randomize which shapes and how many per image.
  Match reference style: thin colored outline only (each object gets its own distinct color 
  from a muted palette: blue, orange/red, teal, purple), NO fill.
- For EACH object, draw a corresponding shadow: a flattened ellipse or parallelogram shape 
  on the ground line, positioned and stretched according to a randomly chosen light source 
  direction and angle (azimuth 0-360 degrees, elevation 20-70 degrees from horizontal).
  ALL objects in a single image share the SAME light source (consistent shadow directions) 
  for ~80% of images (the "solvable" case), but for ~20% of images, deliberately make one 
  object's shadow INCONSISTENT with the others (as if lit by a different light) — this 
  creates the hardest question type (detecting the inconsistent one).
- Shadow rendering: same outline-only style, very low opacity fill (~10-15%) or thin outline 
  ellipse, positioned so its long axis and offset direction correctly encode the light's 
  azimuth (shadow points AWAY from light source) and elevation (higher elevation = shorter/
  more compressed shadow, lower elevation = longer/more stretched shadow).

=== GROUND TRUTH — LIGHT GEOMETRY MUST BE EXACT ===

For each object: store its 3D-approximated position (x, y_base on ground line, and object 
type), and compute its shadow's actual rendered position/shape from the light vector using 
real projective shadow math (project object base point along the light ray onto the ground 
plane) — do not hand-place shadows arbitrarily disconnected from the light vector; the light 
vector is the ONLY generator of shadow position/length, ensuring shadows are always 
geometrically consistent with a specific, recoverable light direction (except for the 
deliberately-inconsistent object in the 20% "trick" images).

Store per image:
- light_azimuth_degrees (0-360, where 0 = light from directly right, 90 = from directly 
  behind/top in 2D projection, etc. — define your convention explicitly in metadata)
- light_elevation_degrees
- objects: list of {type, color, position, shadow_position, shadow_length, consistent: bool}
- num_objects
- has_inconsistent_shadow: true/false
- inconsistent_object_index: index of the object with mismatched shadow, or null

=== GROUND TRUTH GENERATION — EXACTLY 4 QUESTIONS PER IMAGE ===

LEVEL 1 - Simple Description (always include):
  "How many objects are casting a shadow in this image?"
  ground_truth = num_objects

LEVEL 2 - Basic Relational (always include, only for images where has_inconsistent_shadow 
  is false — i.e. all shadows consistent):
  "From which general direction is the light coming — left, right, front, or back? 
  Answer with one word."
  ground_truth = derived from light_azimuth_degrees, bucketed into left/right/front/back 
  (define clear azimuth-to-bucket boundaries, e.g. 315-45deg=front, 45-135=right, etc.)
  (For the has_inconsistent_shadow=true images, use this alternate Level 2 question instead:
  "Do all objects in this image appear to be lit by the same light source? Answer yes or no."
  ground_truth = "no")

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "Which object casts the LONGEST shadow?" (only for images with 2+ objects)
     ground_truth = object color/type with max shadow_length
  b) "Is the light source high in the sky (steep angle) or low near the horizon (shallow 
     angle)? Answer 'high' or 'low'." 
     ground_truth = "high" if light_elevation_degrees > 45 else "low"

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "If has_inconsistent_shadow: Which object's shadow does NOT match the lighting 
     direction of the others? Answer with that object's color."
     ground_truth = color of inconsistent_object_index
     (only generate this question for the 20% inconsistent-shadow images; for the other 
     80%, use fallback (b) or (c) below)
  b) "Estimate the light source's approximate elevation angle above the horizon, rounded 
     to the nearest 15 degrees (e.g. 30, 45, 60)."
     ground_truth = round(light_elevation_degrees / 15) * 15
  c) "If the light source moved to the exact opposite direction (180 degrees azimuth 
     rotation), would the shadows lengthen, shorten, or stay the same length? Answer 
     'lengthen', 'shorten', or 'same'."
     ground_truth = "same" always (rotating azimuth 180 degrees doesn't change elevation, 
     hence shadow length is unchanged — only direction flips) — this is a genuine physics 
     reasoning question, not a lookup

=== METADATA, OUTPUT FORMAT, VALIDATION ===

Follow the exact same pipeline structure as your previous 6 datasets:
- annotations.jsonl with full metadata + 4-question array
- images/shadow_inference_{index:04d}.png
- flatten_annotations.py → dataset_final.csv (task/image/prompt/groundtruth/metadata columns, 
  same difficulty_level → task name mapping as before)
- validate_shadow_dataset.py: independently recompute every shadow's expected position/length 
  from stored light_azimuth/elevation and object position, confirm rendered shadow matches 
  within tolerance; recompute every ground_truth answer from stored geometry; flag mismatches
- --sample flag for 5 images, manually verify light-direction answers by eye against 
  each sample

=== README ===

Same 7-section paper-ready format as previous datasets. Known limitations to state: 
shadows are 2D-projected approximations, not physically-accurate raytraced shadows; only 
4 object primitive types; light source is a simple directional model, not a point-light 
with realistic falloff; the 20% "inconsistent shadow" trick images use a single deliberately-
mismatched object, not multiple.

Output as: generate_shadow_inference_dataset.py
```

## 3. Question design rationale

Questions progress from object counting through coarse source-direction inference, shadow-length/elevation comparison, and compound physical or inconsistency reasoning. Actual usage:

- Level 1: `object_count` 3000
- Level 2: `light_direction_bucket` 2380, `same_light_source` 620
- Level 3: `light_height_class` 1768, `longest_shadow` 1232
- Level 4: `elevation_nearest_15` 1188, `inconsistent_shadow_object` 620, `opposite_azimuth_length_change` 1192

## 4. Ground truth generation and validation

Convention: 0° means light from the front, 90° from the right, 180° from the back, and 270° from the left. Each shadow is projected away from its effective light azimuth. Its cast extent combines `0.55 × object_height / tan(elevation)` with the object's base radius. Round-footprint objects use a tapered 25-section almond silhouette; cubes use a sheared footprint quadrilateral. Shadows always use one neutral dark-gray layer, independent of caster color, over a lighter neutral floor gradient. Every silhouette touches the object base and remains above the ground line. In trick scenes exactly one object receives a 75–145° azimuth perturbation.

The independent validator recomputes each endpoint, footprint radius, length, and screen angle from stored object dimensions and light geometry within a 0.08-pixel tolerance. It then reads every PNG from disk and checks sky/floor colors, neutral shadow tone, centerline, endpoint, multiple transverse widths, base contact, clipping, and ground-line placement before recomputing all answers. Final result: **3,000/3,000 passed; 0 mismatches**.

## 5. Known limitations

- Shadows are 2D projected approximations, not physically accurate ray-traced penumbrae.
- Only cube, sphere, cone, and cylinder primitives are included.
- Lighting uses a directional model without point-light falloff.
- Trick images contain exactly one mismatched object, never multiple mismatches.
- The four-direction azimuth answer deliberately quantizes a continuous direction.

## 6. Reasoning skills tested

- Inverse physical reasoning from effect to invisible cause
- Direction inference from consistent projected displacement
- Comparing shadow extent across differently sized objects
- Detecting violations of a shared-scene lighting constraint
- Separating azimuth changes from elevation-dependent shadow length

## 7. File structure, schema, and worked example

```text
shadow_inference_dataset_3000/
├── images/
├── annotations.jsonl
├── dataset_final.csv
├── dataset_final.jsonl
├── generate_shadow_inference_dataset.py
├── validate_shadow_dataset.py
├── flatten_annotations.py
├── build_dataset_docs.py
├── validation_report.txt
├── contact_sheet.png
├── generation_prompt.txt
└── README.md
```

Raw annotations preserve source geometry, effective per-object azimuth, projected endpoint and length, consistency flag, rendering metadata, seed, and all questions. Flattened metadata contains only difficulty score, object count, inconsistency flag, and seed.

| task | image | prompt | groundtruth |
|---|---|---|---|
| Image Description | shadow_inference_0001.png | How many objects are casting a shadow in this image? | 2 |
| Basic Relational Reasoning | shadow_inference_0001.png | From which general direction is the light coming — left, right, front, or back? Answer with one word. | front |
| Comparative Reasoning | shadow_inference_0001.png | Is the light source high in the sky (steep angle) or low near the horizon (shallow angle)? Answer 'high' or 'low'. | high |
| Compound Reasoning | shadow_inference_0001.png | Estimate the light source's approximate elevation angle above the horizon, rounded to the nearest 15 degrees. | 60 |
# v2 projection-legibility correction

Version 2 excludes light azimuths near the front/back projection axes and requires every rendered shadow to have at least 18 pixels of lateral extent. This corrects geometrically collapsed shadows that palette/contrast changes alone could not repair. Every record stores the screen and azimuth conventions explicitly.
