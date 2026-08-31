# Colored Route Puzzle Dataset

## 1. Dataset overview

The dataset contains **3,000 images** and **12,000 questions**. It was generated on **2026-08-10** through a fully synthetic, deterministic Python pipeline; images were not human-drawn and labels were not human-annotated.

## 2. Full verbatim generation prompt

### Generation Prompt (verbatim)

```text
Build a Python script that programmatically generates a dataset of 3000 "colored route puzzle" 
images, similar to a subway-map-style diagram, for testing visual/spatial reasoning in AI models.

=== VISUAL SPEC ===

Each image is a square canvas (582x580 to 600x600 px range, randomize slightly) with a plain 
off-white/cream background (#FDFAF4 or similar).

- Place 4 to 6 labeled endpoints around the edges of the canvas, labeled with letters A, B, C, D, E, F 
  (always start from A, add letters sequentially — e.g. if using 5 endpoints, use A,B,C,D,E).
  Distribute labels roughly evenly around the perimeter (top, right, bottom, left, and if 5-6, 
  add extra on remaining sides). Render each letter in bold black text just outside the canvas edge.

- Generate 6 to 12 distinct "routes" (colored paths). Each route:
    - Has a single solid color (pick from a pool of up to 12 visually distinct colors: 
      teal, orange, blue, green, red, purple, brown, amber/gold, magenta/pink, cyan, olive, gray-blue).
    - Connects exactly two of the letter endpoints (start and end can repeat across different 
      routes — i.e. multiple colors can connect the same pair of letters, and a single letter 
      can have multiple route-stubs coming from it, as shown in the reference images).
    - Is drawn as an orthogonal (Manhattan-style) path: only horizontal and vertical segments, 
      with random right-angle turns (3 to 8 bends per route). No diagonal lines.
    - Line width should mostly be consistent (2.5-3px) but for ~20% of generated images, randomly 
      thin out some or all lines (1-1.5px) to increase visual difficulty.
    - Routes should overlap and cross each other frequently (do NOT avoid overlaps — crossings 
      are the entire point of the puzzle, similar to the reference image).
    - Use a snapped grid (e.g. 10-20px grid) for coordinates so lines align cleanly like the 
      reference examples.

- Randomize: canvas size, endpoint positions along edges, number of endpoints (4-6), number of 
  routes (6-12), route colors (no duplicate colors within one image), route paths/bend patterns, 
  and line width, for every single generated image. Use a seeded RNG per image so generation 
  is reproducible from the seed alone.

- Save each image as a PNG in /dataset/images/ named: 
  route_puzzle_{index:04d}.png  (e.g. route_puzzle_0001.png)

=== GROUND TRUTH GENERATION (per image) ===

While generating each image, track the full adjacency data: for every route, record 
{color_name, start_letter, end_letter, num_bends, line_width}.

From this adjacency data, auto-generate exactly 2 question/answer pairs per image:

QUESTION 1 (always this template, fixed format):
  Randomly pick a valid pair of letters that appears in this image's routes.
  "Count the one-colored routes that go from {X} to {Y}. Answer with a number in curly brackets 
  e.g. {1}"
  ground_truth = count of routes whose (start,end) matches that unordered pair {X,Y}
  (Always confirm this count is >= 1 by picking pairs known to have at least one connecting route; 
  occasionally pick a pair with 0 connections as a harder negative-case variant, ~15% of the time.)

QUESTION 2 (randomly select ONE template per image from this pool, to add variety/difficulty):
  a) "Which letter has the most route endpoints connected to it?"  
     ground_truth = the letter with highest degree (count as int + letter name)
  b) "How many total distinct colored routes are in this image?"  
     ground_truth = total route count
  c) "Is there any color that connects a letter to itself (i.e., starts and ends at the same 
     letter)? Answer yes or no."  
     ground_truth = yes/no (should almost always be "no" unless you intentionally generate a 
     rare self-loop case ~5% of the time)
  d) "Which two letters have the most routes directly connecting them?"  
     ground_truth = the letter pair with the highest count (and that count)
  e) "List all letter-pairs that have exactly one connecting route between them."  
     ground_truth = list of pairs
  f) "How many routes does letter {X} have in total (i.e., how many colored lines touch {X})?"  
     ground_truth = degree of that letter

  Each question dict should include: question_text, question_type (from the list above), 
  ground_truth, and answer_format ("numeric" / "letter" / "yes_no" / "list").

=== METADATA (per image, no pixel-level annotation needed) ===

Save one JSON entry per image with this schema:

{
  "id": "route_puzzle_0001",
  "image_path": "images/route_puzzle_0001.png",
  "canvas_size": [582, 580],
  "num_endpoints": 5,
  "endpoint_letters": ["A","B","C","D","E"],
  "num_routes": 9,
  "colors_used": ["teal","orange","blue","green","red","purple","brown","amber","magenta"],
  "line_width_px": 2.5,
  "seed": 10432,
  "routes": [
    {"color": "teal", "start": "A", "end": "C", "num_bends": 4},
    {"color": "orange", "start": "B", "end": "D", "num_bends": 6},
    ...
  ],
  "difficulty_score": 0.72,   // compute from: num_routes, num_endpoints, num_bends avg, 
                              // line_width (thinner = harder), and total crossing count 
                              // (count pairwise segment intersections across all routes)
  "questions": [
    {
      "question_id": "route_puzzle_0001_q1",
      "question_text": "Count the one-colored routes that go from C to D. Answer with a number in curly brackets e.g. {1}",
      "question_type": "count_routes_between_pair",
      "ground_truth": "3",
      "answer_format": "numeric"
    },
    {
      "question_id": "route_puzzle_0001_q2",
      "question_text": "...",
      "question_type": "...",
      "ground_truth": "...",
      "answer_format": "..."
    }
  ]
}

Save ALL entries in a single file: /dataset/annotations.jsonl (one JSON object per line, 
NOT a giant array — this is easier to stream/parse for 3000 entries).

Do NOT generate any pixel-level or bounding-box annotations — only the route-level 
adjacency + question/answer metadata described above.

=== TECHNICAL REQUIREMENTS ===

- Use Python with either `svgwrite` + `cairosvg` (render SVG then export PNG) or `Pillow` 
  with manual line drawing — svgwrite/cairosvg preferred for clean anti-aliased line rendering.
- Implement a `generate_route(start_point, end_point, canvas_bounds, num_bends)` function that 
  produces a valid orthogonal path between two points with the given number of bends, snapped 
  to a grid.
- Implement `compute_crossings(routes)` to count total pairwise line-segment intersections 
  for the difficulty_score.
- Implement `assign_endpoints(num_endpoints, canvas_size)` to place letters roughly evenly 
  spaced around the four sides.
- Wrap the whole thing in a `generate_dataset(n=3000, output_dir="dataset/")` function with 
  a progress bar (tqdm), and make each image generation reproducible via `random.seed(i)` 
  per index i.
- Include a `--sample` flag to generate just 5 images first for visual sanity-checking before 
  running the full 3000.
- Include a final validation pass that re-parses annotations.jsonl and confirms: every image 
  file referenced actually exists, every ground_truth for question_type 
  "count_routes_between_pair" matches a recount from the stored routes list (catch generation bugs).

Output the full script as a single Python file: generate_route_dataset.py
```

### Question Redesign Prompt (verbatim)

The question array was subsequently replaced by the following metadata-only redesign prompt; route coordinates, seeds, and PNGs were not regenerated.

```text
Modify the dataset generation pipeline to produce EXACTLY 4 questions per image, 
ordered by increasing difficulty (Level 1 to Level 4), with ground truth for every question.

=== QUESTION LEVELS (fixed templates, values filled per image) ===

LEVEL 1 - Simple Description (always include, pick ONE at random per image):
  a) "How many distinct colored routes are visible in this image?"
     ground_truth = num_routes
  b) "How many labeled endpoints (letters) are shown in this image?"
     ground_truth = num_endpoints

LEVEL 2 - Basic Relational (always include this exact template):
  "Count the one-colored routes that go from {X} to {Y}. Answer with a number in 
  curly brackets e.g. {1}"
  - Randomly select a valid letter pair from this image's routes.
  - ~15% of the time, deliberately pick a pair with 0 connecting routes 
    (negative case), ground_truth = "0"
  - Otherwise ground_truth = count of routes matching that unordered pair

LEVEL 3 - Comparative/Structural (pick ONE at random per image from this pool):
  a) "Which letter has the most routes connected to it?"
     ground_truth = the single letter with max degree (count both start+end).
     ONLY use this template if there is a unique maximum (no ties) - otherwise 
     fall back to template (b) or (c) below for this image.
  b) "Which two letters have the most routes directly connecting them?"
     ground_truth = the letter pair with highest direct-connection count 
     (must be unique max; else fallback to (c))
  c) "How many routes does letter {X} have in total (i.e. touching {X})?"
     ground_truth = degree of a randomly chosen letter X (always well-defined, 
     use as safe fallback for this level)

LEVEL 4 - Complex/Compound (pick ONE at random per image from this pool):
  a) "List all letter-pairs that have exactly one connecting route between them."
     ground_truth = list of such pairs (can be empty list if none exist - 
     that's a valid answer, represent as "[]" or "none")
  b) "Is there any letter-pair with zero directly connecting routes? If yes, 
     name one such pair; if no, answer 'none'."
     ground_truth = one valid zero-connection pair, or "none" if every possible 
     pair has at least one route
  c) "Among all letters, list them in order from most connected routes to 
     least connected routes."
     ground_truth = ordered list of letters by degree, descending 
     (ties broken alphabetically, note ties explicitly if any exist in the list)

=== IMPLEMENTATION REQUIREMENTS ===

1. Every image must end up with EXACTLY 4 questions - one per level, no skipping.
   If a Level 3 template would be ambiguous (tie), automatically fall back to 
   the safe alternative template within that same level (as noted above) rather 
   than skipping the level entirely.

2. Each question object keeps the same fields as before:
   {question_id, question_text, question_type, ground_truth, answer_format}
   plus add a new field: "difficulty_level": 1 | 2 | 3 | 4

3. Re-run this ONLY as a metadata regeneration pass - do NOT re-render images, 
   do NOT change routes/seeds. Use the existing validated routes data in 
   annotations.jsonl as the source of truth, just regenerate the questions array 
   for each image to contain 4 entries per the above spec instead of 2.

4. After regenerating, re-run the full validation script (recompute every 
   ground_truth from stored routes and confirm it matches what was written) - 
   report total mismatches, expect 0.

5. Update flatten_annotations.py so the final CSV now produces 4 rows per image 
   (12,000 rows total for 3000 images) instead of 2, with the "task" column 
   set based on difficulty_level:
     Level 1 → "Image Description"
     Level 2 → "Route Counting"
     Level 3 → "Comparative Reasoning"  
     Level 4 → "Compound Reasoning"

6. Print a final summary: count of images per difficulty_level template used 
   (to confirm reasonable distribution across the random template choices), 
   and confirm every image has exactly 4 questions.
```

## 3. Question design rationale

Level 1 describes route or endpoint counts; Level 2 counts direct routes between a selected pair; Level 3 compares graph degrees or direct pair connectivity; Level 4 aggregates singleton, absent, or degree-ordered relationships. This progression separates perceptual counting from increasingly compositional graph reasoning and supports difficulty-stratified accuracy reporting.

### Actual template distribution

| Level | Role | Question type | Uses |
|---:|---|---|---:|
| 1 | Simple description/counting | `num_labeled_endpoints` | 1,520 |
| 1 | Simple description/counting | `num_routes_visible` | 1,480 |
| 2 | Basic relational reasoning | `count_routes_between_pair` | 3,000 |
| 3 | Comparative/structural reasoning | `highest_degree_letter` | 704 |
| 3 | Comparative/structural reasoning | `letter_degree` | 1,545 |
| 3 | Comparative/structural reasoning | `most_connected_pair` | 751 |
| 4 | Complex/compound reasoning | `degree_ordering` | 1,047 |
| 4 | Complex/compound reasoning | `single_route_pairs` | 981 |
| 4 | Complex/compound reasoning | `zero_connection_pair` | 972 |

## 4. Ground truth generation method

All ground truth was derived deterministically from stored route endpoints and orthogonal polyline coordinates, which are the same structures used to render each image. Labels were not visually estimated or manually assigned. During validation, a `highest_degree_letter` tie-handling defect was found: the initial logic could select a lower uniquely occurring degree when the global maximum was tied. The fix counts both route starts and ends, permits the template only for a unique global maximum, replaces ambiguous cases with an unambiguous template, and revalidates the full corpus.

Final independent validation: **3,000/3,000 images checked, 0 mismatches, PASS**.

## 5. Known limitations

- Only orthogonal (Manhattan-style) routing is used; diagonal and curved routes are absent.
- The color pool is fixed to at most 12 named colors; colorblind accessibility was not controlled.
- Canvas dimensions vary only within approximately 580–600 px; extreme aspect ratios are not represented.
- Line width uses normal and thin tiers rather than unrestricted continuous variation.

## 6. Reasoning skills tested

- Visual path tracing under overlap and crossing-line occlusion (Pathfinder-style connectivity)
- Perceptual grouping and figure–ground segregation across crossing routes
- Graph-relational reasoning, including degree counts and most-connected-pair identification
- Multi-step comparative reasoning over simultaneous paths

## 7. File structure and schema

```text
route_dataset_3000/
  images/
  annotations.jsonl
  dataset_final.csv
  dataset_final.jsonl
  validation_report.txt
  README.md
```

Companion reproducibility scripts in the parent workspace: `generate_route_dataset.py`, `validate_route_dataset.py`, `flatten_annotations.py`, `regenerate_four_questions.py`.

### Flattened schema

| Column | Meaning |
|---|---|
| `task` | Difficulty-level task label. |
| `image` | PNG filename only. |
| `prompt` | Question text presented to a model or human. |
| `groundtruth` | Programmatically derived answer in plain-string form. |
| `metadata` | Compact JSON containing selected image-level generation attributes only. |

Metadata keys for this dataset: `difficulty_score, num_routes, num_endpoints, colors_used, crossing_count, line_width_px, seed`. Full geometry remains only in `annotations.jsonl`.

### Worked example: four levels for `route_puzzle_0001.png`

The following four rows are copied directly from the current `dataset_final.csv`:

```csv
task,image,prompt,groundtruth,metadata
Image Description,route_puzzle_0001.png,How many distinct colored routes are visible in this image?,8,"{""colors_used"":[""orange"",""amber"",""olive"",""cyan"",""brown"",""magenta"",""gray-blue"",""teal""],""crossing_count"":83,""difficulty_score"":0.4971,""line_width_px"":2.95,""num_endpoints"":4,""num_routes"":8,""seed"":1}"
Route Counting,route_puzzle_0001.png,Count the one-colored routes that go from A to D. Answer with a number in curly brackets e.g. {1},1,"{""colors_used"":[""orange"",""amber"",""olive"",""cyan"",""brown"",""magenta"",""gray-blue"",""teal""],""crossing_count"":83,""difficulty_score"":0.4971,""line_width_px"":2.95,""num_endpoints"":4,""num_routes"":8,""seed"":1}"
Comparative Reasoning,route_puzzle_0001.png,How many routes does letter A have in total (i.e. touching A)?,5,"{""colors_used"":[""orange"",""amber"",""olive"",""cyan"",""brown"",""magenta"",""gray-blue"",""teal""],""crossing_count"":83,""difficulty_score"":0.4971,""line_width_px"":2.95,""num_endpoints"":4,""num_routes"":8,""seed"":1}"
Compound Reasoning,route_puzzle_0001.png,"Is there any letter-pair with zero directly connecting routes? If yes, name one such pair; if no, answer 'none'.",CD,"{""colors_used"":[""orange"",""amber"",""olive"",""cyan"",""brown"",""magenta"",""gray-blue"",""teal""],""crossing_count"":83,""difficulty_score"":0.4971,""line_width_px"":2.95,""num_endpoints"":4,""num_routes"":8,""seed"":1}"
```
