# GRIP Hex Grid Pathfinding Dataset 3000

Current version: `hex-pathfinding-2.0.0`. The superseded initial build is preserved under `archive/v1/`; v2 is unsuffixed at the dataset root.

## 1. Overview

This dataset extends GRIP's Topology/Graph Theory family alongside `route_dataset_3000`. Route puzzles trace already drawn crossing lines; this category instead requires constructing an optimal route through a structured environment with hazards. It is closer to grid-maze, robotic-navigation, and agent replanning tasks.

The release contains synthetic images and exact graph-derived ground truth only. It includes no model inference, scoring, accuracy computation, or evaluation harness.

## 2. Contents

- 3,000 deterministic light-theme PNGs on 500–600 px canvases
- Exactly 1,000 radius-3, 1,000 radius-4, and 1,000 radius-5 grids
- Five ordered questions per image, totaling 15,000
- Exact axial coordinates, tile states, shortest path, one example path sequence, and total shortest-path count
- Exactly balanced Level 2 hole/walkable cases
- Exactly balanced Level 5 same/increase/no-path counterfactual outcomes
- Public questions, private answers, statistics, contact sheets, tests, and PNG-aware validation

## 3. Hex graph construction

Tiles use axial `(q,r)` coordinates. The six legal neighbor offsets are:

    (1,0), (1,-1), (0,-1), (-1,0), (-1,1), (0,1)

Grey tiles are removed from the traversable graph. White and black tiles remain walkable; black is decorative, and every image explicitly states `WHITE / BLACK = WALKABLE | GREY = HOLE`. START and HOME are unique walkable cells. Breadth-first search computes the shortest move count, one deterministic example path, and the number of different shortest paths.

### Legend documentation correction

The initial release legend mentioned black walkable tiles and grey holes but omitted the more common white walkable tiles. The renderer was corrected across all 3,000 images to state explicitly that both white and black tiles are walkable. This was a rendering/documentation-only correction: tile colors, grid geometry, questions, annotations, and ground truth were not changed.

Hole density is sampled in a controlled range. Every scene is rejected unless an original START-to-HOME path exists.

## 4. Unified five-level questions

1. **Simple Description:** count grey holes.
2. **Basic Relational:** classify the blue-outlined tile immediately adjacent to START as a hole or walkable. The tile is selected deterministically from neighbors that minimize axial distance to HOME, but the public prompt makes no claim that it lies on a usable path. Selection is balanced independently to 1,500 hole and 1,500 walkable answers; the retained direction-selection flag is constant and has Cramer's V 0 against Level 2.
3. **Comparative/Structural:** find the BFS-shortest move count.
4. **Compound Reasoning:** decide whether the optimum is unique and, if not, count all shortest paths.
5. **Extrapolative/Counterfactual:** turn the purple-X walkable tile into a hole, rerun BFS, and classify the result as unchanged, increased, or disconnected.

The Level 5 tile is always on or within one hex move of the stored example shortest path. No-path cases use a genuine articulation tile at START's only viable exit; the answer is still confirmed through counterfactual BFS.

## 5. Commands and files

    python generate_hex_pathfinding_dataset.py --sample
    python flatten_annotations.py sample_test/annotations.jsonl
    python validate_hex_pathfinding_dataset.py sample_test

    python generate_hex_pathfinding_dataset.py --count 3000
    python flatten_annotations.py
    python make_stats.py
    python make_contact_sheet.py
    python validate_hex_pathfinding_dataset.py
    pytest -q test_hex_pathfinding_dataset.py

Outputs include `annotations.jsonl`, `images/`, `dataset_final.csv`, `dataset_final.jsonl`, `question_set.csv`, `answer_key.csv`, `stats.md`, `contact_sheet.png`, `review_sheet.png`, and `validation_report.txt`.

## 6. Independent validation

The validator independently rebuilds the coordinate set and traversable graph from `all_tiles`, runs its own BFS, recounts shortest paths, verifies every edge in the stored path sequence is one of the six axial neighbors, and reruns BFS after removing the Level 5 tile. It proves the outcome-specific Level 5 invariant for every item: a no-path tile is a true START/HOME cut vertex, an increase tile belongs to every original shortest path, and a same-length case retains an avoiding shortest path. PNG probes recover white, black, grey, START, and HOME as distinct classes and recover the exact grey-hole count in all 3,000 images.

The v2 reference-frame declaration is `axial hex coordinates (q,r)`. All stored graph quantities and every consuming question use that same frame. Full association matrices, answer baselines, parameter distributions, guard injections, and PNG recovery totals are in `validation_metrics.json` and `validation_report.txt`.

Manual launch traces confirmed 5-, 7-, and 13-move sample paths using only legal six-neighbor transitions.

## 7. Reasoning scope and limitations

Skills tested include graph construction from a visual grid, six-neighbor adjacency, hazard avoidance, optimal path planning, shortest-path multiplicity, articulation reasoning, and counterfactual replanning.

Limitations: only hexagonal grids are included; holes are static; every scene has one START and one HOME; movement costs are uniform; there are no dynamic agents, terrain weights, diagonal-like jumps, multiple goals, or partial observability.
