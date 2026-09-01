---
license: mit
task_categories:
  - visual-question-answering
language:
  - en
tags:
  - geometry
  - spatial-reasoning
  - visual-reasoning
  - physical-reasoning
  - synthetic
  - benchmark
  - vqa
size_categories:
  - 100K<n<1M
pretty_name: GRIP-Benchmark-34
configs:
  - config_name: default
    data_files:
      - split: train
        path: combined/all_answers_combined-*.parquet
  - config_name: annotations
    data_files:
      - split: train
        path: combined/all_annotations_combined-*.parquet
---

# GRIP-Benchmark-34

**A programmatically generated and independently validated suite for visual geometry and physical reasoning**

## 1. Suite overview

GRIP-Benchmark-34 contains **34 synthetic sub-benchmarks**, **100,000 images**, and **500,000 image–question pairs** across **nine reasoning families**: plane geometry, transformational geometry, projective geometry, topology/graph theory, surface topology, analytic/coordinate geometry, inductive/analogical reasoning, physical/mechanical reasoning, and solid geometry. The 33 core categories contribute 3,000 images each, while the focused projectile-motion addition contributes 1,000; every image has exactly five difficulty-ordered questions.

All images, scene parameters, and answers are generated programmatically with deterministic, closed-form ground truth. Ground truth is independently re-derived from the underlying geometry by dataset-specific validator code, and every current validation report records **PASS with zero mismatches**.

Suggested suite names:

1. **GRIP-Benchmark-34** — Geometry, Reasoning, Induction, and Physics; used throughout this README.
2. **GeoReason-34** — emphasizes visual, analytic, and mechanical reasoning rather than recognition alone.
3. **Synthetic Geometry and Physical Reasoning Suite (SGPRS-34)** — emphasizes provenance and scope.

This repository generates datasets and ground truth. It does not run models, score predictions, or provide an evaluation harness.

## 2. Dataset summary

| Dataset | Geometry class | Version | Images | Questions | Validation | Key skill tested |
|---|---|---|---:|---:|---|---|
| [route](Dataset/route_dataset_3000/) | Topology / Graph Theory | route-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Trace colored routes and reason over endpoint connectivity |
| [nested_squares](Dataset/nested_squares_dataset_3000/) | Transformational Geometry | nested-squares-8.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Measure center drift, size ratio, four-fold rotation, and geometric visibility |
| [nested_triangles](Dataset/nested_triangles_dataset_3000/) | Transformational Geometry | nested-triangles-8.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Generalize drift, size, and three-fold rotation reasoning to triangles |
| [nested_hexagons](Dataset/nested_hexagons_dataset_3000/) | Transformational Geometry | nested-hexagons-8.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Generalize drift, size, and six-fold rotation reasoning to hexagons |
| [cube_structure](Dataset/cube_structure_dataset_3000/) | Solid Geometry | cube-structure-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Count and reason about visible/hidden cubes and support |
| [line_intersection](Dataset/line_intersection_dataset_3000/) | Plane Geometry | line-intersection-3.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Count and compare line intersections |
| [overlap_circles](Dataset/overlap_circles_dataset_3000/) | Plane Geometry | overlap-circles-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Reason about circle overlap and planar regions |
| [cube_net](Dataset/cube_net_dataset_3000/) | Solid Geometry | cube-net-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Infer 3D cube relationships from unfolded nets |
| [shadow_inference](Dataset/shadow_inference_dataset_3000/) | Projective Geometry | shadow-inference-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Infer light direction/elevation from projected shadows |
| [impossible_object](Dataset/impossible_object_dataset_3000/) | Solid Geometry | impossible-object-4.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Detect globally inconsistent 3D line structures |
| [polyhedron](Dataset/polyhedron_dataset_3000/) | Solid Geometry | polyhedron-5.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Classify polyhedra and reason about faces, edges, and vertices |
| [depth_height](Dataset/depth_height_dataset_3000/) | Projective Geometry / Height Comparison | depth-height-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Compare perspective-based depth and count flat stack heights |
| [embedded_figures](Dataset/embedded_figures_dataset_3000/) | Plane Geometry — Composition | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Find a target figure within a complex line composition |
| [rotation_matching](Dataset/rotation_matching_dataset_3000/) | Transformational Geometry | rotation-matching-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Match shapes under rotation while rejecting reflections |
| [combination](Dataset/combination_dataset_3000/) | Plane Geometry — Composition | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Assemble 2D polyomino pieces into a target |
| [combination3d](Dataset/combination3d_dataset_3000/) | Solid Geometry | combination3d-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Assemble voxel pieces under constrained 3D rotations |
| [fold_punch](Dataset/fold_punch_dataset_3000/) | Transformational Geometry | fold-punch-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Track sequential reflections and layered punch positions |
| [symmetry_pattern](Dataset/symmetry_pattern_dataset_3000/) | Transformational Geometry | symmetry-pattern-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Identify and reason about reflection/rotation symmetry |
| [occluded_pattern](Dataset/occluded_pattern_dataset_3000/) | Plane Geometry | occluded-pattern-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Perform amodal counting through regular-pattern occlusion |
| [angle_estimation](Dataset/angle_estimation_dataset_3000/) | Plane Geometry — Angles | angle-estimation-3.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Estimate, compare, and classify planar angles |
| [coordinate_geometry](Dataset/coordinate_geometry_dataset_3000/) | Analytic / Coordinate Geometry | coordinate-geometry-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Read coordinates and compute distance, midpoint, and collinearity |
| [orthographic](Dataset/orthographic_dataset_3000/) | Solid Geometry — Multi-View Projection | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Reconstruct and compare voxel structures from top/front/side projections |
| [rpm](Dataset/rpm_dataset_3000/) | Inductive / Analogical Reasoning | rpm-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Discover, combine, and extrapolate visual progression rules |
| [surface_topology](Dataset/surface_topology_dataset_3000/) | Surface Topology | surface-topology-3.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Reason about genus, orientability, boundaries, and Euler characteristic |
| [gear_train](Dataset/gear_train_dataset_3000/) | Physical / Mechanical Reasoning | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Propagate rotation direction and exact gear ratios through mechanical chains and branches |
| [physical_stability](Dataset/physical_stability_dataset_3000/) | Physical / Mechanical Reasoning | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Compute cumulative centers of mass and identify tipping joints under block removal |
| [free_body_diagram](Dataset/fbd_dataset_3000/) | Physical / Mechanical Reasoning | free-body-diagram-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Resolve force vectors, equilibrium, omissions, invalid arrows, and counterfactual acceleration |
| [clock_reading](Dataset/clock_reading_dataset_3000/) | Physical / Mechanical Reasoning | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Read exact analog time, account for hour-hand creep, and recompute hand angles after time advancement |
| [gauge_reading](Dataset/gauge_reading_dataset_3000/) | Physical / Mechanical Reasoning | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Interpolate single-needle readings across varied ranges and reason about thresholds and projected values |
| [optical_illusion](Dataset/optical_illusion_dataset_3000/) | Plane Geometry / Visual Perception | optical-illusion-3.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Separate true pixel geometry from misleading contextual size cues |
| [compass_bearing](Dataset/compass_bearing_dataset_3000/) | Analytic Geometry / Navigation | compass-bearing-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Compute compass bearings, turns, and counterfactual destinations |
| [hex_pathfinding](Dataset/hex_pathfinding_dataset_3000/) | Topology / Graph Theory | hex-pathfinding-2.0.0 | 3,000 | 15,000 | PASS — 0 mismatches | Find and count shortest paths through obstructed hex grids |
| [laser_mirror](Dataset/laser_mirror_dataset_3000/) | Plane Geometry / Physical Optics | legacy-current | 3,000 | 15,000 | PASS — 0 mismatches | Trace multi-bounce reflections and counterfactual mirror rotations |
| [projectile_motion](Dataset/projectile_motion_dataset_1000/) | Physical / Mechanical Reasoning | projectile-motion-1.0.0 | 1,000 | 5,000 | PASS — 0 mismatches | Apply ideal projectile kinematics and reason about obstacle clearance and angle optimization |
| **Total** | **34 sub-benchmarks** | — | **100,000** | **500,000** | **34/34 PASS** | **Broad visual, spatial, geometric, topological, analytic, inductive, optical, and mechanical reasoning** |

### Geometry-class breakdown

- **Plane Geometry:** overlap circles, line intersections, occluded patterns, optical illusions, and multi-bounce laser reflection.
- **Plane Geometry — Composition:** 2D combination and embedded figures.
- **Plane Geometry — Angles:** angle estimation.
- **Transformational Geometry:** the nested-polygon family (squares, equilateral triangles, and regular hexagons), rotation matching, symmetry patterns, and fold-and-punch transformations.
- **Projective Geometry:** perspective-based depth ordering and shadow inference; `depth_height` also contains an explicitly documented 50% flat height-comparison branch.
- **Topology / Graph Theory:** colored-route connectivity and shortest-path reasoning on hex grids.
- **Surface Topology:** genus, orientability, boundary components, and Euler characteristic.
- **Analytic / Coordinate Geometry:** coordinate-based geometry plus compass-bearing and map-navigation reasoning.
- **Inductive / Analogical Reasoning:** progressive-matrix rule discovery and completion.
- **Physical / Mechanical Reasoning:** causal gear propagation, cumulative-center-of-mass stability, free-body force analysis, exact analog-clock hand angles, single-needle gauge interpolation, and ideal projectile kinematics.
- **Solid Geometry** contains six sub-branches:
  1. **Nets & Surfaces:** `cube_net_dataset_3000`
  2. **Volume & Spatial Visualization:** `cube_structure_dataset_3000`
  3. **3D Tiling/Dissection:** `combination3d_dataset_3000`
  4. **Polyhedra:** `polyhedron_dataset_3000`
  5. **Spatial Consistency:** `impossible_object_dataset_3000`
  6. **Multi-View Projection:** `orthographic_dataset_3000`

## 3. Shared methodology

### Unified five-level question progression

Every image has exactly five questions in increasing order of difficulty:

1. **Level 1 — Simple Description:** perceive one directly visible fact with no inference.
2. **Level 2 — Basic Relational:** perform one comparison or one-step rule application.
3. **Level 3 — Comparative/Structural:** reason across multiple elements, rank them, identify an extreme, or cross-reference image regions.
4. **Level 4 — Compound Reasoning:** combine at least two facts or apply a multi-step formula/rule chain without hypothetical framing.
5. **Level 5 — Extrapolative/Counterfactual:** apply an explicitly defined hypothetical geometric change, extrapolate beyond the shown pattern, or explain a deterministic consequence.

The exact question templates differ by category, but this progression and the `difficulty_level: 1..5` annotation contract are shared by all 34 datasets. Every Level 5 operation is independently recomputable from raw stored geometry or scene metadata. Flattened CSV/JSONL files contain one row per question, yielding 15,000 rows per core dataset and 5,000 for the focused projectile-motion category.

The suite-level files in `combined/` are rebuilt from dataset directories discovered by `build_manifest.json`, not from a hardcoded list. The current combined files include all 34 datasets: 33 datasets at 15,000 questions each plus `projectile_motion_dataset_1000` at 5,000 questions, for 500,000 questions and 500,000 answers. The Hub's `default` configuration loads the sharded answer Parquet view, including embedded image bytes, prompt, ground truth, and answer format. The separate `annotations` configuration contains one row per image with the combined scene metadata. The original question and answer CSVs remain available for non-viewer workflows.

Free-body-diagram Level 4 questions introduce the structured scoring declaration `{"type":"numeric_tolerance","tolerance_percent":2}` for real-valued mechanics answers. This field appears in annotations, answer keys, and the published answer view, but not in question-only CSVs; it records grading precision explicitly.

### Independent validation

Generation-time assertions are not treated as sufficient evidence. Each sub-benchmark has a separate validator that reconstructs answers from raw scene geometry or metadata. Depending on the task, validators use exact-cover search, graph recomputation, affine reflection, dot products, coordinate formulas, polyhedral/voxel enumeration, geometric containment, or projective shadow calculations.

Validation follows a common pattern:

- re-derive ground truth rather than trusting stored answer fields;
- check constraints and reject ambiguous cases such as ties, accidental collinearity, invalid transformations, clipping, or degenerate geometry;
- recompute all five question answers;
- audit expected dataset-level distributions;
- where image/label divergence is a material risk, read the final PNG from disk and check rendered components, locations, silhouettes, or line geometry.

Every dataset folder contains its generator, raw annotations, flattened outputs, validation report, contact sheet, and dataset-specific README.

For suite-wide manual review of the original 29-category release, see [spot_check_review](<spot check/spot_check_review/>), which preserves five low-, five medium-, and five high-difficulty images per included dataset: 435 images total, a long-form 2,175-row five-question answer key, and a consolidated 29×15 contact sheet. The deterministic seed is `20260814`.

## 4. Transparency: bugs found and fixed

Manual visual review and independent recomputation were part of dataset development, not post-hoc presentation. Two notable issues illustrate why both are necessary.

### Route endpoint-degree and tie handling

An early `highest_degree_letter` implementation in `route_dataset_3000` counted only routes where a letter appeared as `route.start`. It failed to count appearances as `route.end`, so some labels were wrong. The computation was corrected to count both endpoints. Explicit tie handling was also added: an ambiguous highest-degree question is not emitted; the question generator falls back to a well-defined template. A metadata-only regeneration repaired affected questions without changing route images or geometry, and the full validator subsequently reported zero mismatches.

### Shadow geometry, color, and floor contrast

Early `shadow_inference_dataset_3000` renders used small, caster-colored blobs that did not reliably communicate the stored projected length and direction. This escaped internal metadata consistency because the stored light/shadow values could agree even when the actual pixels did not.

The issue was corrected in two review-driven passes:

1. **Shape and geometry:** round-footprint objects received elongated tapered/almond silhouettes, cubes received sheared quadrilaterals, and PNG-level checks were added for centerline, endpoint, transverse width, base contact, clipping, and ground-line placement. Shadow length remains derived from object geometry and `1 / tan(light_elevation)`.
2. **Color and contrast:** every shadow was moved to a neutral dark-gray layer independent of caster color, and a lighter neutral floor gradient was introduced beneath the dark sky to make direction and extent readable.

The annotation hash was preserved during the rendering-only pass, and both the pre-change and final full validations reported zero ground-truth mismatches.

These fixes are a methodological strength: self-consistent parameters alone cannot prove that a rendered image expresses those parameters. Independent recomputation catches label logic errors, while human inspection and PNG-aware checks catch perceptual/rendering failures.

### Cube-net, Combination3D, and rotation-frame audit

A later manual-review pass found that `cube_net_dataset_3000` mixed flat-net fold-edge neighbors with folded-cube adjacency in some Level 4 answers. The v2 rebuild now stores both frames explicitly, repaired 452 incorrect prior Level 4 labels, removed the impossible folded-cube `neither` option, and balances adjacent/opposite answers 1,500/1,500.

The same audit confirmed that `combination3d_dataset_3000` was already internally consistent: its isometric renderer, height calculation, gravity convention, and permitted vertical spins all use world z as the visual vertical axis. This convention is now explicit in every record and is enforced by exhaustive z-only/full-rotation exact-cover validation.

`rotation_matching_dataset_3000` replaces non-isometric distorted foils with two congruent wrong-angle rotations plus one congruent reflection. A 25-degree minimum-turn guard and all-item PNG corner recovery protect vertex-count legibility, while a label-free Level 5 avoids reusing the target/reflection candidate pair. The current validator and `validation_metrics.json` contain the retained release audit.

## 5. Related work

> **Third-party attribution:** The publications below are independent works by their
> respective authors. They were studied and cited as conceptual inspiration for this
> original synthetic benchmark. The GRIP-Benchmark creator does not claim authorship,
> contribution, endorsement, or affiliation with these papers or their authors.

- **GIQ.** Michalkiewicz et al., [*GIQ: Benchmarking 3D Geometric Reasoning of Vision Foundation Models with Simulated and Real Polyhedra*](https://arxiv.org/abs/2506.08194), evaluates vision and vision-language models using synthetic and real imagery of diverse polyhedra, including reconstruction, symmetry, mental rotation, and shape classification. GRIP-Benchmark-34 is complementary: it includes solid-geometry tasks but broadens the scope to plane, transformational, projective, topological, compositional, angle, coordinate, navigational, optical, inductive, and mechanical reasoning.
- **Spatial-DISE.** Huang et al., [*Spatial-DISE: A Unified Benchmark for Evaluating Spatial Reasoning in Vision-Language Models*](https://arxiv.org/abs/2510.13394), proposes a cognitively grounded spatial-reasoning taxonomy and scalable synthetic generation. Its task framing informed several categories here, including 2D/3D combination and fold-and-punch reasoning.
- **CAPTURe.** Pothiraj et al., [*CAPTURe: Evaluating Spatial Reasoning in Vision Language Models via Occluded Object Counting*](https://arxiv.org/abs/2504.15485), studies amodal counting through unseen regions. The `occluded_pattern` sub-benchmark extends this controlled pattern-extrapolation setting with a five-level question structure.
- **GeoQA.** Chen et al., [*GeoQA: A Geometric Question Answering Benchmark Towards Multimodal Numerical Reasoning*](https://aclanthology.org/2021.findings-acl.46/), focuses on diagram-and-text geometry problems from school examinations. GRIP-Benchmark-34 instead uses fully synthetic scenes with directly inspectable generation parameters and task-specific independent validators.
- **PhysBench.** Chow et al., [*PhysBench: Benchmarking and Enhancing Vision-Language Models for Physical World Understanding*](https://arxiv.org/abs/2501.16411), evaluates physical properties, relationships, scenes, and dynamics. The six Physical/Mechanical categories here provide controlled, exactly re-derived causal mechanics, statics, free-body force analysis, clock-angle, instrument-reading, and projectile-kinematics tasks.
- **Interactive intuitive physics.** Schulze Buschoff et al., [*Can Vision Language Models Learn Intuitive Physics from Interaction?*](https://arxiv.org/abs/2602.06033), studies block-tower construction and stability learning. `physical_stability_dataset_3000` provides a complementary deterministic center-of-mass benchmark with explicit counterfactual removal cases.
- **Analog-clock reasoning.** Choi et al., [*It's Time to Get It Right: Improving Analog Clock Reading and Clock-Hand Spatial Reasoning in Vision-Language Models*](https://arxiv.org/abs/2603.08011), documents persistent clock-reading and clock-hand spatial-reasoning failures in VLMs. Yang, Xie, and Zisserman, [*It's About Time: Analog Clock Reading in the Wild*](https://arxiv.org/abs/2111.09162), develops synthetic-to-real analog-clock recognition and benchmark data. `clock_reading_dataset_3000` adds exact minute-level readings, continuous hour-hand motion, smaller-angle computation, and deterministic time-advance counterfactuals.
- **Visual instrument reading.** Lin et al., [*Do Vision-Language Models Measure Up? Benchmarking Visual Measurement Reading with MeasureBench*](https://arxiv.org/abs/2510.26865), evaluates real and synthetic measurement instruments and highlights indicator localization as a recurring source of VLM reading error. `gauge_reading_dataset_3000` provides a complementary controlled benchmark with exact varied-range interpolation, threshold bands, and counterfactual range increases.

The `orthographic_dataset_3000` category implements classical orthographic/third-angle projection reasoning and serves as the inverse-task complement to `cube_structure_dataset_3000`: the former reconstructs 3D structure from three flat views, while the latter reasons about occlusion from one isometric view.

## 6. Release use, validation, and limitations

### Benchmark and metadata files

GRIP is a published open benchmark, so the Hub's `default` configuration intentionally exposes ground truth and `answer_format` alongside each question. Its `image_bytes` column is a Hugging Face `Image` feature with the PNG bytes embedded in Parquet; `image` retains the original filename and `image_path` retains the repository-relative source path. The `annotations` configuration exposes scene metadata for inspection and analysis, with its `image` column stored as the same embedded `Image` feature. Complex list and object metadata is losslessly JSON-encoded in individual columns so the heterogeneous 34-domain schema remains representable in one table.

The per-dataset `question_set.csv` files and `combined/all_questions_combined.csv` remain the question-only model-facing artifacts. Per-dataset `answer_key.csv` files, `combined/all_answers_combined.csv`, and the answer Parquet view include published reference answers. Raw `annotations.jsonl` and the annotations Parquet view can reveal the exact scene geometry and quantities from which answers are derived. **Do not provide annotations to a model under evaluation: doing so leaks answer-generating metadata and invalidates the measurement.**

### Validation methodology

Validators independently re-derive answers from stored geometry, inspect final PNGs for recoverable question-dependent quantities, run bias-corrected Cramér's V feature/answer audits, exercise constraints with violating and boundary guard-injection cases, and report constant-answer baselines. Accuracy should be interpreted relative to the reported baseline rather than as an isolated percentage.

### Depth/height scope

`depth_height_dataset_3000` is deliberately split: 1,500 scenes contain perspective-based size and vertical-position cues for projective depth ordering, while 1,500 are flat stack-height counting scenes. The whole category should not be described as exclusively projective.

### Levels with constant-answer baseline at or above 60%

- `combination_dataset_3000` Level 5: **64.0%**
- `cube_net_dataset_3000` Level 1: **100.0%**
- `cube_net_dataset_3000` Level 5: **78.8%**
- `embedded_figures_dataset_3000` Level 5: **66.2%**
- `gauge_reading_dataset_3000` Level 1: **80.0%**
- `gauge_reading_dataset_3000` Level 4: **60.0%**
- `gear_train_dataset_3000` Level 2: **100.0%**
- `laser_mirror_dataset_3000` Level 2: **75.0%**
- `optical_illusion_dataset_3000` Level 1: **100.0%**
- `orthographic_dataset_3000` Level 5: **100.0%**
- `physical_stability_dataset_3000` Level 2: **62.5%**
- `polyhedron_dataset_3000` Level 2: **89.5%**
- `polyhedron_dataset_3000` Level 5: **100.0%**
- `projectile_motion_dataset_1000` Level 2: **65.4%**
- `projectile_motion_dataset_1000` Level 5: **68.8%**
- `surface_topology_dataset_3000` Level 2: **75.0%**
- `symmetry_pattern_dataset_3000` Level 5: **100.0%**

Six levels are structurally constant at 100% and therefore carry no discriminative signal: `cube_net` L1 (every cube net has six faces), `gear_train` L2 (meshed gears counter-rotate), `optical_illusion` L1 (two elements are always compared), `orthographic` L5, `polyhedron` L5 (removing a face opens the surface), and `symmetry_pattern` L5. Report results as accuracy above baseline, and do not treat performance on these levels as evidence of reasoning ability.

## 7. Folder structure

```text
geomstry/
├── README.md
├── Dataset/
│   ├── route_dataset_3000/
│   ├── nested_squares_dataset_3000/
│   ├── nested_triangles_dataset_3000/
│   ├── nested_hexagons_dataset_3000/
│   ├── ...
│   ├── orthographic_dataset_3000/
│   ├── rpm_dataset_3000/
│   ├── surface_topology_dataset_3000/
│   ├── gear_train_dataset_3000/
│   ├── physical_stability_dataset_3000/
│   ├── fbd_dataset_3000/
│   ├── clock_reading_dataset_3000/
│   ├── gauge_reading_dataset_3000/
│   ├── optical_illusion_dataset_3000/
│   ├── compass_bearing_dataset_3000/
│   ├── hex_pathfinding_dataset_3000/
│   ├── laser_mirror_dataset_3000/
│   └── projectile_motion_dataset_1000/
├── spot check/
│   ├── spot_check_sampler.py
│   └── spot_check_review/
└── combined/
    ├── all_questions_combined.csv
    ├── all_answers_combined.csv
    ├── all_answers_combined-*.parquet
    └── all_annotations_combined-*.parquet
```

Each dataset folder is self-contained. Consult its local README for task definitions, generation commands, annotation schema, validation logic, limitations, and review assets.

Dataset PNG files are stored with Git Large File Storage. Before cloning or pulling the complete image collection, install Git LFS and run `git lfs install`.

This suite currently contains 34 datasets under the unified five-level rubric: 28 geometric/spatial/navigational/perceptual categories and six physical/mechanical categories. Future categories must follow [UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md](UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md) from generation onward.

The repository-wide final audit is published in [Dataset/final_suite_audit.md](Dataset/final_suite_audit.md). It reports current versions, five per-level constant baselines, modification status, and PNG asset coverage for all 34 datasets. Dataset-specific final audit reports intentionally flag structural answer skews rather than hiding them behind generator/validator agreement.
