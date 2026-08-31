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
- synthetic
- benchmark
- vqa
pretty_name: GRIP-Benchmark
size_categories:
- 100K<n<1M
---

# GRIP-Benchmark

GRIP-Benchmark is a fully synthetic, programmatically generated and independently validated visual geometry, spatial-reasoning, and physical-reasoning suite. The current release contains **34 categories**, **100,000 unique images**, and **500,000 image-question rows**. Every image is paired with five questions ordered from direct perception through extrapolative/counterfactual reasoning.

The repository provides data and ground truth only. It does not include model inference, scoring, or an evaluation harness.

## 2. Dataset summary

| Dataset | Geometry class | Images | Questions | Validation | Key skill tested |
|---|---|---:|---:|---|---|
| route | Topology / Graph Theory | 3,000 | 15,000 | PASS — 0 mismatches | Trace colored routes and reason over endpoint connectivity |
| nested_squares | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Measure center drift, size ratio, four-fold rotation, and geometric visibility |
| nested_triangles | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Generalize drift, size, and three-fold rotation reasoning to triangles |
| nested_hexagons | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Generalize drift, size, and six-fold rotation reasoning to hexagons |
| cube_structure | Solid Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Count and reason about visible/hidden cubes and support |
| line_intersection | Plane Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Count and compare line intersections |
| overlap_circles | Plane Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Reason about circle overlap and planar regions |
| cube_net | Solid Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Infer 3D cube relationships from unfolded nets |
| shadow_inference | Projective Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Infer light direction/elevation from projected shadows |
| impossible_object | Solid Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Detect globally inconsistent 3D line structures |
| polyhedron | Solid Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Classify polyhedra and reason about faces, edges, and vertices |
| depth_height | Projective Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Compare depicted depth and height from projected cues |
| embedded_figures | Plane Geometry — Composition | 3,000 | 15,000 | PASS — 0 mismatches | Find a target figure within a complex line composition |
| rotation_matching | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Match shapes under rotation while rejecting reflections |
| combination | Plane Geometry — Composition | 3,000 | 15,000 | PASS — 0 mismatches | Assemble 2D polyomino pieces into a target |
| combination3d | Solid Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Assemble voxel pieces under constrained 3D rotations |
| fold_punch | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Track sequential reflections and layered punch positions |
| symmetry_pattern | Transformational Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Identify and reason about reflection/rotation symmetry |
| occluded_pattern | Plane Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Perform amodal counting through regular-pattern occlusion |
| angle_estimation | Plane Geometry — Angles | 3,000 | 15,000 | PASS — 0 mismatches | Estimate, compare, and classify planar angles |
| coordinate_geometry | Analytic / Coordinate Geometry | 3,000 | 15,000 | PASS — 0 mismatches | Read coordinates and compute distance, midpoint, and collinearity |
| orthographic | Solid Geometry — Multi-View Projection | 3,000 | 15,000 | PASS — 0 mismatches | Reconstruct and compare voxel structures from top/front/side projections |
| rpm | Inductive / Analogical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Discover, combine, and extrapolate visual progression rules |
| surface_topology | Surface Topology | 3,000 | 15,000 | PASS — 0 mismatches | Reason about genus, orientability, boundaries, and Euler characteristic |
| gear_train | Physical / Mechanical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Propagate rotation direction and exact gear ratios through mechanical chains and branches |
| physical_stability | Physical / Mechanical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Compute cumulative centers of mass and identify tipping joints under block removal |
| free_body_diagram | Physical / Mechanical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Resolve force vectors, equilibrium, omissions, invalid arrows, and counterfactual acceleration |
| clock_reading | Physical / Mechanical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Read exact analog time, account for hour-hand creep, and recompute hand angles after time advancement |
| gauge_reading | Physical / Mechanical Reasoning | 3,000 | 15,000 | PASS — 0 mismatches | Interpolate single-needle readings across varied ranges and reason about thresholds and projected values |
| optical_illusion | Plane Geometry / Visual Perception | 3,000 | 15,000 | PASS — 0 mismatches | Separate true pixel geometry from misleading contextual size cues |
| compass_bearing | Analytic Geometry / Navigation | 3,000 | 15,000 | PASS — 0 mismatches | Compute compass bearings, turns, and counterfactual destinations |
| hex_pathfinding | Topology / Graph Theory | 3,000 | 15,000 | PASS — 0 mismatches | Find and count shortest paths through obstructed hex grids |
| laser_mirror | Plane Geometry / Physical Optics | 3,000 | 15,000 | PASS — 0 mismatches | Trace multi-bounce reflections and counterfactual mirror rotations |
| projectile_motion | Physical / Mechanical Reasoning | 1,000 | 5,000 | PASS — 0 mismatches | Apply ideal projectile kinematics and reason about obstacle clearance and angle optimization |
| **Total** | **34 sub-benchmarks** | **100,000** | **500,000** | **34/34 PASS** | **Broad visual, spatial, geometric, topological, analytic, inductive, optical, and mechanical reasoning** |

### Geometry-class breakdown

- **Plane Geometry:** overlap circles, line intersections, occluded patterns, optical illusions, and multi-bounce laser reflection.
- **Plane Geometry — Composition:** 2D combination and embedded figures.
- **Plane Geometry — Angles:** angle estimation.
- **Transformational Geometry:** the nested-polygon family (squares, equilateral triangles, and regular hexagons), rotation matching, symmetry patterns, and fold-and-punch transformations.
- **Projective Geometry:** depth/height perception and shadow inference.
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

Free-body-diagram Level 4 questions introduce the structured private scoring declaration `{"type":"numeric_tolerance","tolerance_percent":2}` for real-valued mechanics answers. This field appears in annotations and private answer keys, not public question sets; it changes grading precision without exposing an acceptance band to a tested model.

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

## Dataset Structure

The Hub release uses one unified `train` split with 500,000 rows and the following schema:

| Field | Type | Description |
|---|---|---|
| `id` | string | Globally unique identifier such as `route_0001_q1` |
| `image` | Image | Embedded image bytes; the dataset is self-contained |
| `category` | string | One of the 34 benchmark categories |
| `question` | string | Question prompt |
| `ground_truth` | string | Validated answer |
| `metadata` | string | Compact JSON metadata retained from the source dataset |

Example (image omitted from the textual representation):

```json
{
  "id": "route_0001_q1",
  "category": "route",
  "question": "How many distinct colored routes are visible in this image?",
  "ground_truth": "7",
  "metadata": "{\"difficulty_score\":0.42,\"num_routes\":7}"
}
```

Each unique image appears in five rows with different IDs, questions, and answers but identical embedded image content.

## Loading

```python
from datasets import load_dataset
dataset = load_dataset("bilaljawaid980/GRIP-Benchmark", split="train")
```

## Validation and limitations

Ground truth is independently re-derived from stored scene geometry or structured metadata by category-specific validators. Known limitations include synthetic rather than photographic imagery, bounded shape/rule vocabularies, and category-specific procedural distributions. These data should be treated as a diagnostic benchmark, not as a substitute for real-world spatial reasoning evaluation.

## Related Work

- [GIQ: Benchmarking 3D Geometric Reasoning of Vision Foundation Models](https://arxiv.org/abs/2506.08194)
- [Pathfinder / Long Range Arena](https://arxiv.org/abs/2011.04006)
- [GeoMeter: Probing Depth and Height Perception of Large Visual-Language Models](https://arxiv.org/abs/2408.11748)
- [Spatial-DISE: A Unified Benchmark for Evaluating Spatial Reasoning in Vision-Language Models](https://arxiv.org/abs/2510.13394)
- [CAPTURe: Evaluating Spatial Reasoning in Vision Language Models via Occluded Object Counting](https://arxiv.org/abs/2504.15485)

## License

MIT. See the repository license and individual related-work citations for details.
