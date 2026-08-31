# GRIP Cube Net Dataset 3000 — v2

This release contains 3,000 dark-theme diagrams covering all 11 valid cube nets and 15,000 questions under GRIP's unified five-level rubric. Version `cube-net-2.0.0` repairs a reference-frame defect in the previous Level 4 labels.

## Reference frames and the v2 correction

Two relations are stored explicitly and must not be mixed:

- `net_edge_pairs` / `net_edge_neighbors` use the **flat-net frame** and contain only squares sharing a drawn fold edge.
- `opposite_pairs`, `cube_adjacent_pairs`, and `cube_adjacent_faces` use the **folded-cube frame**. A folded face is adjacent to every face except itself and its unique opposite.

The previous build stored folded opposition correctly but used flat-net edge neighbors when answering some folded-cube Level 4 questions. Independent recomputation found 452 wrong old Level 4 answers. v2 derives folded adjacency as the complement of opposition and removes the impossible `neither` option. Level 4 is exactly balanced: 1,500 `adjacent` and 1,500 `opposite`.

Level 2 remains intentionally flat-net based. Its `valid_answers` array contains every face sharing a drawn fold edge with the queried face; the private `answer_key.csv` preserves both this accepted list and `answer_format=letter_any_of_list`.

## Five questions

1. Count the six visible face squares.
2. Name any valid flat-net fold-edge neighbor.
3. Recover a flat-net degree or a folded opposite face.
4. Classify a folded face pair as adjacent or opposite.
5. Determine whether swapping two face labels preserves a face's original opposite.

## Validation

`validate_cube_net_dataset.py` independently propagates 3D face frames through every net, reconstructs flat and folded relations, re-derives all five answers, verifies every Level 2 accepted list, and checks all six labeled face regions and layouts in every PNG. It reports full distributions, per-level constant baselines, a complete stored-feature leak audit, reference-frame mappings, and violating/boundary guard injections. The final v2 build passes 3,000/3,000 images and 15,000/15,000 questions with zero mismatches.

The previous metadata and reports are preserved under `archive/v1/`. Cube-net pixels did not require a style change; backgrounds, dimensions, palette, and line-art renderer remain unchanged.

## Commands

```text
python generate_cube_net_dataset.py --n 3000 --output-dir .
python flatten_annotations.py annotations.jsonl
python validate_cube_net_dataset.py .
```

Model-facing evaluation must use `question_set.csv`, which contains only `question_id`, `task`, `image`, and `prompt`. `annotations.jsonl`, `answer_key.csv`, and `dataset_final.*` contain ground truth.
