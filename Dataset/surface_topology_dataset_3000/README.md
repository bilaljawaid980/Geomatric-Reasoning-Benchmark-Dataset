# Surface Topology Dataset 3000

## 1. Overview and motivation

This category fills a topology gap in GRIP. `route_dataset_3000` studies graph connectivity, while `polyhedron_dataset_3000` applies Euler's formula primarily to conventional polyhedral solids. This dataset instead tests genus, orientability, boundary components, and Euler characteristic for general surfaces—including higher-genus, non-convex, and non-orientable examples.

The category is also motivated by sustained interest in AI-assisted mathematical discovery and geometry. Recent systems have been used to [generate useful conjectures in topology](https://www.nature.com/articles/s41586-021-04086-x) and to [attack difficult problems in geometry](https://openai.com/index/model-disproves-discrete-geometry-conjecture/), reinforcing the value of transparent, foundational visual-topology tasks whose answers can be checked exactly. This dataset makes no claim to test research-level theorem proving; it isolates basic invariants that such reasoning ultimately depends on.

## 2. Dataset contents

The final dataset contains 3,000 deterministic 500–550 px PNG images on an off-white background and 15,000 questions. Four surface families are balanced at 750 images each:

- closed sphere-like surfaces with 0–3 handles;
- cubical/polyhedral boundary meshes with 0–3 through-tunnels;
- cylindrical bands and Möbius strips;
- tori and Klein bottles.

For non-orientable examples, `genus` records non-orientable (crosscap) genus: one for the Möbius strip and two for the Klein bottle. `genus_kind` makes this convention explicit. For orientable examples, it records ordinary handle genus.

## 3. Questions and difficulty levels

Every image has exactly five ordered questions:

1. **Image Description:** identify the represented genus/handle count.
2. **Basic Relational Reasoning:** classify the surface as orientable or non-orientable.
3. **Comparative Reasoning:** determine Euler characteristic or, for meshes, vertex count.
4. **Compound Reasoning:** combine the depicted genus/handle structure and orientability to report both Euler characteristic and orientability. This replaces the former constant-answer hypothetical, which could contradict an orientable render.
5. **Extrapolative/Counterfactual Reasoning:** infer the new Euler characteristic after hypothetically removing an open disk and introducing one additional boundary component.

The closed-orientable formula is never presented as applicable to a surface with boundary or a non-orientable surface.

## 4. Generation and reproducibility

Run from this folder:

```powershell
python generate_surface_topology_dataset.py --n 3000 --output-dir .
python validate_surface_topology_dataset.py .
python flatten_annotations.py annotations.jsonl
python make_contact_sheet.py .
```

Use `--sample` to produce five images before a full run. Each image uses `random.seed(index)` semantics, so image parameters are reproducible from the stored integer seed.

Polyhedral examples are not assigned arbitrary Euler counts. They are boundaries of voxel blocks with actual through-tunnels. The generator derives explicit vertex, edge, and face lists from exposed cubical faces and asserts `V-E+F = 2-2g` before rendering.

## 5. Independent validation

`validate_surface_topology_dataset.py` independently:

- derives orientability, boundary count, and Euler characteristic from the surface variant;
- uses `χ = 2-2g` only for closed orientable surfaces;
- uses `χ = 2-k-b` for the Möbius strip (`k=1`, `b=1`) and `χ = 2-k` for the Klein bottle (`k=2`);
- rebuilds the polyhedral edge set from the stored face cycles, then recomputes `V-E+F`;
- re-derives every question answer;
- verifies PNG readability and canvas dimensions;
- checks full-set surface-type and genus distributions.

The reference constants are independently corroborated by [Cornell's introduction to topology](https://pi.math.cornell.edu/~matsumura/math4530/IntroToTopology.pdf) and Wolfram MathWorld's entries for the [Euler characteristic](https://mathworld.wolfram.com/EulerCharacteristic.html), [Möbius strip](https://mathworld.wolfram.com/MoebiusStrip.html), and [Klein bottle](https://mathworld.wolfram.com/KleinBottle.html).

## 6. Output schema

Primary files:

- `images/surface_topology_####.png`
- `annotations.jsonl` with raw surface parameters, explicit mesh arrays where applicable, and five ground-truth questions
- `dataset_final.csv` and `dataset_final.jsonl`
- `question_set.csv` without answers
- `answer_key.csv` with answers
- `validation_report.txt`
- `contact_sheet.png` and `human_calibration/review_sheet.png`

No model inference, scoring, or evaluation runner is included.

## 7. Scope, limitations, and skills tested

Known limitations: genus is limited to 0–3 for tractable rendering; non-orientable surfaces are limited to the two classical examples; the Klein bottle uses its conventional self-intersecting 3D schematic because a true embedding in three dimensions is impossible; and the images are clean technical schematics rather than physical materials.

Skills tested include genus/handle counting, orientability judgment, Euler-characteristic computation, formula application, and linking a mesh's combinatorial data `(V,E,F)` to its topological invariant.
