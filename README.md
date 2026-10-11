---
license: mit
language:
  - en
task_categories:
  - visual-question-answering
tags:
  - vision-language-models
  - multimodal-reasoning
  - visual-reasoning
  - geometric-reasoning
  - spatial-reasoning
  - physical-reasoning
  - sycophancy
  - robustness
  - procedural-generation
  - synthetic
  - exact-ground-truth
  - benchmark
pretty_name: GRIP
size_categories:
  - 100K<n<1M
configs:
  - config_name: closed_loop
    data_files:
      - split: test
        path: combined/all_answers_combined-*.parquet
  - config_name: open_loop
    data_files:
      - split: test
        path: combined/all_open_answers_combined.parquet
  - config_name: scene_annotations
    data_files:
      - split: test
        path: combined/all_annotations_combined-*.parquet
---

# GRIP: Geometric Reasoning and Intuitive Physics

**A controlled benchmark that measures whether a vision-language model keeps a correct answer when it is challenged.**

| | |
|---|---|
| Paper | *Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial and Physical Reasoning for Vision-Language Models* |
| Project page | [GRIP Benchmark](https://bilaljawaid980.github.io/grip-benchmark/) |
| Code | [GitHub](https://github.com/bilaljawaid980/Geomatric-Reasoning-Benchmark-Dataset) |
| Scale | 100,000 images · 600,000 questions · 34 domains · 9 reasoning families |

![GRIP taxonomy and Dual-Loop Evaluation overview](assets/grip-taxonomy-burst.png)

## What GRIP is for

Vision-language models can answer a geometric or physical reasoning question correctly and then abandon that answer when challenged. Single-turn accuracy cannot distinguish rule absence from rule fragility because it scores each response in isolation.

GRIP separates them. Every scene is produced by deterministic code from a seeded generator, and every answer is computed from the same latent scene state used by the renderer. This makes it possible to assign direction to an answer change:

- **Correction:** wrong → right
- **Capitulation:** right → wrong

Correction and capitulation are measured over different populations and are reported separately.

## Benchmark construction

Generation rejects scenes near decision boundaries, rounding ties, or classification thresholds and records the distance from each accepted scene to its nearest boundary. Difficulty is therefore controlled during generation rather than introduced through post-hoc annotation.

Thirty-three domains contain 3,000 images each, while Projectile Motion contains 1,000, giving 100,000 images in total. Each image has five closed-loop questions and one open-response question, for 600,000 questions.

### Reasoning families

| Family | Domains | Included domains |
|---|:--:|---|
| Plane | 5 | Nested Squares, Nested Triangles, Nested Hexagons, Line Intersection, Angle Estimation |
| Solid | 6 | Cube Nets, Cube Structure, 3D Combination, Orthographic, Polyhedra, Depth & Height |
| Transformational | 6 | Rotation Matching, Symmetry Patterns, Fold & Punch, 2D Combination, Embedded Figures, Overlapping Circles |
| Physical | 7 | Physical Stability, Gear Trains, Free-Body Diagrams, Projectile Motion, Laser & Mirrors, Clock Reading, Gauge Reading |
| Topological | 3 | Surface Topology, Route Puzzles, Hex Pathfinding |
| Projective | 2 | Occluded Patterns, Shadow Inference |
| Analytic | 2 | Coordinate Geometry, Compass Bearings |
| Optical | 2 | Optical Illusions, Impossible Objects |
| Inductive | 1 | Progressive Matrices |
| **Total** | **34** | |

### Five-question ladder

Each image is paired with five ordered closed-loop questions. Every question is evaluated in a fresh single-turn conversation containing one image and one question.

| Position | Competence |
|:--:|---|
| Q1 | Direct observation, recognition, or counting |
| Q2 | Spatial relation or classification |
| Q3 | Measurement or multi-element inference |
| Q4 | Multi-step integration or derived comparison |
| Q5 | Counterfactual reasoning after modifying the scene |

### Dual-Loop Evaluation

- **Closed loop:** the five ordered questions are answered independently.
- **Open loop:** the stored first answer is re-elicited under a no-challenge control, an unsupported assertion, or peer-model responses.

Both loops share images, questions, and exact ground truth, enabling capability and stability to be evaluated on the same benchmark items.

## Dataset structure

GRIP is published with a single `test` split and three configurations:

| Configuration | Rows | Description |
|---|---:|---|
| `closed_loop` | 500,000 | Five closed-loop questions per image, with prompts, exact targets, answer formats, and images |
| `open_loop` | 100,000 | One open-response item per image, including acceptance sets, tolerances, targets, and structured answer fields |
| `scene_annotations` | 100,000 | Images, seeds, generation parameters, latent scene state, and domain-specific derived quantities |

### Core fields

`closed_loop` contains:

- `dataset`, `dataset_version`: domain and generator version
- `question_id`: stable question identifier
- `task`: question position in the five-level ladder
- `image_bytes`: embedded image data
- `image`, `image_path`: image identifier and repository-relative path
- `prompt`: question text
- `groundtruth`: exact answer
- `answer_format`: required response type

`open_loop` contains `dataset`, `dataset_version`, `question_id`, `image`, `image_path`, `prompt`, `acceptance_set`, `tolerances`, `targets`, and domain-specific structured target columns.

`scene_annotations` contains the common domain, version, image, and seed identifiers together with domain-specific latent parameters and derived quantities. Fields that do not apply to a domain are null.

## Loading

Install the Hugging Face Datasets library:

```bash
pip install datasets
```

Load any configuration from the Hub:

```python
from datasets import load_dataset

closed_loop = load_dataset(
    "bilaljawaid980/GRIP-Benchmark",
    "closed_loop",
    split="test",
)

open_loop = load_dataset(
    "bilaljawaid980/GRIP-Benchmark",
    "open_loop",
    split="test",
)

scene_annotations = load_dataset(
    "bilaljawaid980/GRIP-Benchmark",
    "scene_annotations",
    split="test",
)
```

For low-memory inspection, pass `streaming=True`.

> Do not send answer-key fields to a model under evaluation. Ground-truth, answer-format, tolerance, and annotation fields are provided for local scoring and analysis.

## Results at a glance

Sixteen models were evaluated: ten hosted models and six open-weight models.

- **Capability:** hosted closed-loop accuracy ranges from 68.9% to 41.3%. After adjustment for constant-answer baselines, the range is 50.7% to 4.8%.
- **Noise robustness:** additive monochrome Gaussian grain at σ ∈ {15, 25, 40} changes accuracy by no more than 6.1 percentage points for any hosted model.
- **Challenge sensitivity:** across 32,270 challenges, control-adjusted capitulation ranges from 6.18 to 72.75 percentage points.
- **Peer effects:** adjusted correction is positive across all ten hosted models in the natural-peer experiment, while constructed consensus produces substantially larger capitulation effects.
- **Family variation:** hosted family means range from 62.8% for Physical reasoning to 39.5% for Topological reasoning.

Detailed results are available in the repository:

| Test | Evaluation | Results |
|---|---|---|
| Test 1 | Closed-loop accuracy by level and reasoning family | [Results](tests/test_1_closed_loop/results/TEST_1_RESULTS.md) |
| Test 2 | Robustness to controlled visual noise | [Results](tests/test_2_grain_robustness/results/TEST_2_RESULTS.md) |
| Test 3 | Correction and capitulation under unsupported challenge | [Results](tests/test_3_sycophancy/results/TEST_3_RESULTS.md) |
| Test 4 | Natural-peer, constructed-consensus, control, and confidence effects | [Results](tests/test_4_crossexam/results/TEST_4_RESULTS.md) |

## Intended use

GRIP is an evaluation benchmark for research on vision-language reasoning, robustness, and interaction-dependent answer stability. It supports controlled model comparison, error analysis, and reproducible evaluation across geometric, spatial, and physical reasoning tasks.

GRIP uses synthetic diagrams and evaluates the abstractions represented by its 34 domains. Results should be reported with the model version, prompts, image preprocessing, decoding settings, and scoring procedure.

## Reproducibility

Per-domain directories include generator versions, build manifests, validation reports, and exact answer keys. Closed-loop question construction is documented in [`UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md`](UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md), and open-response construction is documented in [`OPEN_QUESTION_SPEC.md`](OPEN_QUESTION_SPEC.md).

Use immutable repository revisions when reporting results.

## License

GRIP, including its procedurally generated data and accompanying code, is released under the [MIT License](LICENSE).

## Citation

```bibtex
@misc{jawaid2026geometric,
  author = {Bilal Jawaid and Hamza Hanif and Muhammad Maaz Uddin and
            Anas Zafar and Inad Alqurashi and Aizan Zafar and
            Osama Farooqui and Sheheryar Khan and Ferhat Sadak and
            Shaina Raza and Rizwan Qureshi},
  title  = {Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial
            and Physical Reasoning for Vision-Language Models},
  year   = {2026},
  note   = {Preprint}
}
```

### Authors and affiliations

1. Bilal Jawaid — Independent
2. Hamza Hanif — Simon Fraser University
3. Muhammad Maaz Uddin — Salim Habib University
4. Anas Zafar — The University of Texas MD Anderson Cancer Center
5. Inad Alqurashi — Taif University
6. Aizan Zafar — International Institute of Information Technology, Bangalore
7. Osama Farooqui — Salim Habib University
8. Sheheryar Khan — CPCE, Hong Kong Polytechnic University
9. Ferhat Sadak — Aston University
10. Shaina Raza — Vector Institute
11. Rizwan Qureshi — Massachusetts General Hospital

