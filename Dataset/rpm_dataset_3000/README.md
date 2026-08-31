# Synthetic Raven-Style Progressive Matrices Dataset

## 1. Overview

This folder contains 3,000 synthetic Raven-style Progressive Matrices (RPM) images and 12,000 grounded questions. It follows the procedural visual-reasoning tradition of [RAVEN (Zhang et al., 2019)](https://openaccess.thecvf.com/content_CVPR_2019/html/Zhang_RAVEN_A_Dataset_for_Relational_and_Analogical_Visual_REasoNing_CVPR_2019_paper.html) and [Procedurally Generated Matrices / PGM (Barrett et al., 2018)](https://proceedings.mlr.press/v80/barrett18a.html), while using an original compact rule grammar and rendering pipeline.

Unlike the suite's 20 single-image spatial/geometric datasets, this category tests inductive and analogical rule discovery across a matrix of panels. It contains exactly one correct completion among eight choices per puzzle. No model inference, scoring, or evaluation code is included.

The published images use the generic on-image title **“PROGRESSIVE MATRIX PUZZLE”** on an off-white, paper-like background. Raven/RAVEN/PGM terminology is retained only here for scholarly lineage and related-work attribution, not as image branding.

## 2. Generation prompt

The complete source specification is preserved verbatim in `generation_prompt.txt`:

```text
Build a Python script that generates 3000 "Raven's Progressive Matrices" (RPM) puzzles, 
testing inductive/analogical rule reasoning — a completely different reasoning family from 
the rest of this suite, which so far tests only single-image spatial/geometric perception. 
This replicates the classical RPM paradigm (Raven, 1936; the RAVEN/PGM procedurally-
generated tradition) used as a standard human fluid-intelligence test.

=== VISUAL SPEC ===

Canvas: 550-650px, DARK background (#1A1A1A), consistent with your dark-theme datasets.

- Render a 3x3 grid of panels. The bottom-right (9th) panel is left BLANK (shown as an 
  empty bordered box with a "?" mark).
- Each of the 8 filled panels shows 1-3 simple geometric shapes (from: circle, square, 
  triangle, pentagon, hexagon, star) with attributes: shape_type, size (small/medium/large), 
  color (from a fixed palette of 6), rotation_angle, count (1-3 identical shapes arranged 
  in a row or single centered).
- Generate the grid by choosing 1-3 RULES that apply consistently across each row (or, for 
  ~30% of images, across each column instead, to prevent models from assuming "always 
  read left-to-right" as a shortcut) from this pool:
  a) SHAPE PROGRESSION: shape type stays constant within a row, but changes across rows 
     in a fixed cyclic order (e.g. row1=circle, row2=square, row3=triangle)
  b) SIZE PROGRESSION: size increases or decreases consistently left-to-right within each row
  c) COLOR PROGRESSION: color cycles through a fixed sequence across columns
  d) ROTATION PROGRESSION: shape rotates by a constant angle increment across the row
  e) COUNT PROGRESSION: number of shapes increases/decreases by a constant amount across 
     the row (1,2,3)
  f) XOR/ADDITION RULE: the third panel's attribute is derived by combining the first two 
     (e.g. if panel1 has a shape and panel2 doesn't share it, panel3 shows the shape that's 
     different; or panel3 = shapes present in panel1 XOR panel2, for 2-shape panels)
  g) CONSTANT RULE: one attribute (e.g. color) stays IDENTICAL across the entire row 
     (or column), while other attributes vary per the other active rules
  - Combine 1-2 of these rules per puzzle (single-rule puzzles for ~40% of images = easier 
    tier; 2 combined rules for ~60% = harder tier), ensuring the 9th panel's correct answer 
    is uniquely and unambiguously derivable by applying the same rule(s) consistently.
- Generate 8 answer CHOICES (labeled 1-8, shown below the grid): 1 correct (satisfies all 
  active rules exactly), and 7 distractors constructed via specific violation types:
  - 2-3 distractors that violate exactly ONE of the active rules (e.g. correct shape/size/
    count but wrong color) — "near miss" distractors
  - 2-3 distractors that violate a DIFFERENT, plausible-but-wrong rule (e.g. continue a 
    progression that doesn't actually apply to this puzzle)
  - 1-2 distractors that are clearly wrong (random combination) as easier eliminations

=== GROUND TRUTH DATA PER IMAGE ===

- active_rules: list of {rule_type, applies_to: "row"|"column", details}
- grid_panels: full attribute list for all 8 given panels + the correct 9th panel
- correct_answer_index: 1-8
- distractor_violations: list of {choice_index, violates_rule: which rule it breaks, 
  violation_type: "single_attribute"|"wrong_progression"|"random"}
- difficulty_tier: "single_rule"|"combined_rules"
- num_active_rules

=== 4 QUESTIONS PER IMAGE, ORDERED BY DIFFICULTY ===

LEVEL 1 - Simple Description (always include):
  "How many shapes appear in the panel at row 1, column 1 (top-left)?"
  ground_truth = count of shapes in that specific panel (direct reading, no rule-solving 
  needed — pure perception checkpoint before the harder inductive questions)

LEVEL 2 - Basic Relational (always include, THE CORE RPM question):
  "Which of the 8 numbered choices correctly completes the pattern in the missing panel? 
  Answer with the number."
  ground_truth = correct_answer_index

LEVEL 3 - Comparative/Structural (pick ONE at random per image from):
  a) "What attribute changes consistently across the top row — shape, size, color, 
     rotation, or count? Answer with one word." (only ask about an attribute that is 
     ACTUALLY part of an active rule for that row)
     ground_truth = the specific attribute name
  b) "Choice {X} (a random incorrect choice) is wrong. Does it have the correct shape 
     but wrong color, or the correct color but wrong shape, or is it wrong in some other 
     way? Answer accordingly." (tailor answer options to that specific distractor's 
     actual violation_type)
     ground_truth = derived from that distractor's stored violation info

LEVEL 4 - Complex/Compound (pick ONE at random per image from):
  a) "This puzzle uses more than one rule simultaneously (e.g. both size AND color change 
     together). Name both attributes that change according to a pattern. Answer with two 
     words separated by 'and'." (only for difficulty_tier=="combined_rules"; for 
     single_rule puzzles, fall back to (b))
     ground_truth = both active rule attribute names
  b) "If the pattern in this row/column continued for one MORE panel beyond the missing 
     one, what would that panel's [specific attribute] be?" (asks about extrapolating the 
     rule one step further than the puzzle requires)
     ground_truth = computed by extending the identified progression one additional step
  c) "How many of the 8 answer choices share the same shape type as the correct answer, 
     even though most of them are wrong for other reasons? Answer with a number."
     ground_truth = count of choices (including the correct one) matching the correct 
     shape_type

=== METADATA, OUTPUT, VALIDATION (same pipeline pattern as your 20 existing datasets) ===

1. annotations.jsonl, images/rpm_{index:04d}.png
2. flatten_annotations.py → dataset_final.csv (same schema/task mapping)
3. validate_rpm_dataset.py:
   - Independently re-verify the correct_answer_index by re-applying the stored 
     active_rules to the grid pattern from scratch and confirming it produces the 
     stored "correct" panel's exact attributes — not just trusting the generation-time flag
   - Independently re-verify EVERY distractor's violation_type by checking it against 
     what would be perfectly rule-consistent, confirming each genuinely violates what 
     it claims to violate
   - Confirm no distractor accidentally ALSO satisfies all active rules (which would 
     create a duplicate correct answer / ambiguous puzzle) — reject and regenerate any 
     such case
   - Confirm roughly 40/60 split between single_rule and combined_rules difficulty tiers
   - Confirm roughly even distribution across rule types used
   - Re-derive every question's ground truth, confirm exact match
4. --sample flag, 5 images — this is a HIGH manual-check priority category: literally 
   try to solve each puzzle yourself (identify the rule, pick the answer) before trusting 
   generation at scale. RPM puzzles are notoriously easy to accidentally make ambiguous 
   (multiple valid answers) or unsolvable (no consistent rule actually holds) — this is 
   exactly the failure mode your independent validator's "no duplicate correct answer" 
   check is designed to catch, but a human read is still the strongest final confirmation.

=== TECHNICAL NOTES ===

- Implement apply_rule(rule, row_or_col_index, position_in_sequence) -> panel_attributes, 
  reused for both generating the grid and independently validating it.
- Implement generate_distractor(correct_attributes, violation_type) for constructing each 
  of the 7 wrong choices with a controlled, labeled violation.
- Render each panel and each choice as a small bordered box containing the shape(s), 
  consistent simple flat-color rendering (no gradients/shading) matching your other 
  datasets' clean geometric style.
- Reuse random.seed(i) per image for reproducibility.

Output as: generate_rpm_dataset.py

=== README (7-section format, citing RAVEN/PGM lineage) ===

Section 1: state this implements a synthetic Raven's Progressive Matrices generator in 
the tradition of RAVEN (Zhang et al.) and Procedurally Generated Matrices/PGM (Barrett 
et al. 2018), representing a distinct reasoning family (inductive/analogical rule 
discovery across multiple images) compared to the single-image spatial/geometric 
perception tasks in the rest of this suite's 20 other datasets.

Known limitations: rule pool limited to 7 rule types (shape/size/color/rotation/count 
progressions, XOR, constant); maximum 2 combined rules per puzzle (real RPM tests can 
combine more); shape vocabulary limited to 6 basic polygon/circle types; distractor 
generation uses labeled violation types rather than fully adversarial optimization.

Reasoning skills tested: inductive rule discovery from visual sequences, analogical 
completion, distinguishing near-miss distractors from clearly-wrong ones, rule 
extrapolation beyond the given grid, multi-rule simultaneous tracking.

Output as: generate_rpm_dataset.py
```

## 3. Question design

Every image has exactly four questions in increasing difficulty:

1. Directly count the shapes in the top-left panel.
2. Select the choice that completes the matrix.
3. Identify a governed attribute or diagnose a distractor.
4. Track multiple rules, extrapolate one more step, or compare the choices with the correct shape.

The generated composition is 1,200 single-rule puzzles and 1,800 combined-rule puzzles. Rule uses are: {"color_progression": 721, "constant": 720, "count_progression": 657, "rotation_progression": 662, "shape_progression": 660, "size_progression": 720, "xor_addition": 660}. Non-active attributes are explicitly held constant, so the missing panel is fully constrained rather than relying on unspecified visual properties.

## 4. Ground truth and validation

Each JSONL record stores the active rule definitions, all nine panel attribute records (the ninth is hidden only in the PNG), eight answer choices, the correct index, controlled distractor violations, deterministic seed, and four question-answer objects. `validate_rpm_dataset.py` independently infers the missing panel from the eight visible panel records, rechecks every grid cell against its rule, requires exactly one matching answer choice, reconstructs each distractor's changed attributes, and re-derives all four answers.

Latest full report:

```text
Total images checked: 3000
Difficulty tiers: {"combined_rules": 1800, "single_rule": 1200}
Orientations: {"column": 900, "row": 2100}
Rule distribution: {"color_progression": 721, "constant": 720, "count_progression": 657, "rotation_progression": 662, "shape_progression": 660, "size_progression": 720, "xor_addition": 660}
Question types: {"choices_matching_correct_shape": 1184, "combined_rule_attributes": 593, "consistent_attribute": 797, "correct_choice": 3000, "distractor_classification": 2203, "rule_extrapolation": 1223, "top_left_shape_count": 3000}
Total mismatches found: 0
Summary: PASS
```

## 5. Reasoning skills tested

- Inductive rule discovery from visual sequences
- Analogical completion of a missing matrix cell
- Simultaneous tracking of two governed attributes
- Distinguishing near-miss distractors from clearly wrong choices
- Rule extrapolation beyond the displayed matrix
- Row-versus-column orientation switching

## 6. Known limitations

The rule vocabulary is limited to seven types: shape, size, color, rotation, and count progressions; modular count addition; and a constant attribute. Puzzles combine at most two rules, whereas human-authored RPM tests can use richer compositions. The shapes are six basic polygon/circle types. Distractors use controlled labeled violations rather than adversarial optimization. The implementation is inspired by the procedural lineage above but is not a reproduction of either RAVEN or PGM.

## 7. Files and schema

- `images/rpm_0001.png` ... `images/rpm_3000.png`: rendered puzzles
- `annotations.jsonl`: full private geometry, rules, choices, and ground truth
- `dataset_final.csv` / `dataset_final.jsonl`: flattened four-row-per-image table
- `question_set.csv`: public prompts with answers removed
- `answer_key.csv`: private matched answers
- `validation_report.txt`: independent full-pass results
- `contact_sheet.png`: 25-image overview
- `human_calibration/review_sheet.png`: five full-size review samples
- `generate_rpm_dataset.py`, `validate_rpm_dataset.py`, `flatten_annotations.py`, `make_contact_sheet.py`: reproducible pipeline
- `tests/`: unit tests for modular addition, progression, and independent inference

The flattened schema is `task,image,prompt,groundtruth,metadata`. Compact metadata includes only difficulty, rule count/tier, orientation, and seed; full panels and answer choices remain in `annotations.jsonl`.
# v2 anti-copy correction

Version 2 requires three distinct matrix rows, forbids the missing panel from duplicating any shown panel, and requires variation across rows as well as within them. Consequently all released matrices combine two rules; a single oriented rule cannot satisfy the anti-copy condition in a 3×3 grid.
