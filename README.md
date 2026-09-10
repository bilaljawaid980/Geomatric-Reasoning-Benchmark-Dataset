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

GRIP (Geometry, Reasoning, Induction, and Physics) is a synthetic visual-reasoning benchmark built to test whether multimodal models can reason from diagrams rather than rely on recognition alone. It spans geometry, topology, spatial transformation, visual measurement, induction, and mechanics through 34 independently generated domains.

The release contains:

- **34 domains** in **9 reasoning families**
- **100,000 images**: 33 domains with 3,000 images and `projectile_motion` with 1,000
- **500,000 closed questions**: five ordered difficulty levels per image
- **100,000 open-ended questions**: one explanation-based question per image
- Programmatically generated scenes with deterministic, closed-form ground truth
- Dataset-specific validators, image-aware checks, distribution audits, and human review

GRIP is an open benchmark. Reference answers are published for reproducible evaluation, while question-only files are also provided for clean model input.

## Dataset

Each image has five closed questions arranged as a reasoning ladder:

| Level | Reasoning stage | Description |
|---|---|---|
| L1 | Perception | Read or count a directly visible property. |
| L2 | Relation | Compare two elements or apply one simple relation. |
| L3 | Structure | Combine evidence across multiple objects or regions. |
| L4 | Multi-step reasoning | Apply a compound geometric, physical, or logical rule. |
| L5 | Counterfactual reasoning | Predict the result of a stated change or extrapolation. |

The 33 full-size domains contain 15,000 closed questions each. `projectile_motion_dataset_1000` contains 5,000. Together they total exactly 500,000 closed questions and 500,000 reference answers.

### Main release files

| File | Rows | Purpose |
|---|---:|---|
| `combined/all_questions_combined.csv` | 500,000 | Closed questions without ground truth |
| `combined/all_answers_combined.csv` | 500,000 | Closed questions with published reference answers |
| `combined/all_open_questions_combined.csv` | 100,000 | Open-ended questions without answer targets |
| `combined/all_open_answers_combined.csv` | 100,000 | Open-ended questions with targets and tolerances |
| `combined/all_answers_combined-*.parquet` | 500,000 | Hugging Face viewer shards with embedded images |
| `combined/all_annotations_combined-*.parquet` | 100,000 | Per-image scene metadata with embedded images |

The Hugging Face `default` configuration loads the closed-question answer view. The `annotations` configuration exposes scene metadata for analysis. PNG bytes are embedded in the Parquet shards so images render directly in the dataset viewer.

## Families and domains

| Family | Domains | What they test |
|---|---|---|
| Plane geometry | `angle_estimation`, `combination`, `embedded_figures`, `laser_mirror`, `line_intersection`, `occluded_pattern`, `optical_illusion`, `overlap_circles` | Angles, composition, intersections, occlusion, reflection, overlap, and metric judgment |
| Transformational geometry | `fold_punch`, `nested_hexagons`, `nested_squares`, `nested_triangles`, `rotation_matching`, `symmetry_pattern` | Rotation, reflection, folding, symmetry, scaling, and transformation invariance |
| Projective geometry | `depth_height`, `shadow_inference` | Depth ordering, height comparison, projection, and light direction |
| Topology and graph theory | `hex_pathfinding`, `route` | Connectivity, degree, shortest paths, and replanning |
| Surface topology | `surface_topology` | Genus, orientability, boundaries, and Euler structure |
| Analytic and coordinate geometry | `compass_bearing`, `coordinate_geometry` | Coordinates, distance, midpoint, bearings, and navigation |
| Inductive and analogical reasoning | `rpm` | Visual rule discovery and Raven-style matrix completion |
| Physical and mechanical reasoning | `clock_reading`, `fbd`, `gauge_reading`, `gear_train`, `physical_stability`, `projectile_motion` | Measurement, forces, motion, equilibrium, stability, and mechanical propagation |
| Solid geometry | `combination3d`, `cube_net`, `cube_structure`, `impossible_object`, `orthographic`, `polyhedron` | 3D assembly, nets, occlusion, projections, spatial consistency, and polyhedral structure |

Every domain directory under `Dataset/` is self-contained and includes its images, generator, annotations, question files, answer key, build manifest, validation outputs, and domain README.

## Generation pipeline

GRIP is generated end to end from code:

1. **Sample a scene.** A deterministic seed selects geometry, layout, labels, and task parameters within domain constraints.
2. **Enforce constraints.** Generation guards reject degenerate, clipped, ambiguous, or invalid scenes before release.
3. **Render the image.** The accepted scene is converted into a PNG using the domain renderer.
4. **Derive ground truth.** Closed-form geometry, graph algorithms, exact search, or physical equations produce the answers.
5. **Build the five-level ladder.** Each image receives one ordered question at every level from L1 through L5.
6. **Generate the open question.** A domain-specific template requests a conclusion, visible justification, and confidence score.
7. **Validate independently.** Separate validation logic re-derives targets and checks the final artifact.
8. **Assemble the suite.** Dataset folders are discovered through `build_manifest.json`; combined files are rebuilt with row-count, ID, and image-path assertions.

The repository does not require a model to create labels. Ground truth comes from the scene construction itself and is independently recomputed during validation.

## Validation and human verification

Automated validation covers all released items and includes:

- Independent ground-truth re-derivation instead of trusting stored answers
- Every question ID resolves to exactly one answer and one source image/annotation record
- Verification that every referenced PNG exists
- Image-aware recovery checks for the visual quantities used by each task
- Constraint tests with deliberately invalid and boundary cases
- Public-schema and answer-leak checks
- Answer-distribution and constant-answer baseline reports
- Feature-to-answer association audits using bias-corrected Cramér's V

Human verification complements the automated checks. Reviewers inspect representative low-, medium-, and high-difficulty renders, trace the visible evidence used by the answer, and investigate cases flagged by validators or manual inspection. The original 29-domain release retains a reproducible 435-image review set with 2,175 closed question-answer checks in [`spot check/spot_check_review/`](<spot check/spot_check_review/>). Later domains and revised tasks include targeted render reviews in their validation reports.

The current suite audit reports:

- **34/34 domains passing**
- **100,000/100,000 images resolved**
- **500,000 closed questions matched to 500,000 answers**
- **100,000 open questions matched to 100,000 answer records**
- **0 independently re-derived ground-truth mismatches**

See [`Dataset/final_suite_audit.md`](Dataset/final_suite_audit.md) for the suite summary and each domain's `validation_metrics.json`, `validation_report.txt`, and `open_validation_metrics.json` for detailed results.

## Open-ended reasoning track

The open-ended track adds one question per image without changing the closed L1-L5 benchmark. These prompts ask a model to:

- reach a domain-specific conclusion;
- explain which visible evidence supports it; and
- end with a confidence score from 0 to 1.

Each open answer record stores the expected sub-facts, accepted forms, and explicit tolerances for numeric quantities. Prompts are generated from the exact domain templates in [`OPEN_QUESTION_SPEC.md`](OPEN_QUESTION_SPEC.md), with only documented per-image parameter substitution.

Use `combined/all_open_questions_combined.csv` as model input and `combined/all_open_answers_combined.csv` for evaluation. The public question file does not include target fields.

## Evaluation guidance

Use question-only files when running a model, then score outputs against the corresponding answer files. Report results by domain and difficulty level, and compare accuracy with the constant-answer baselines published in the validation metrics.

Do not provide `annotations.jsonl`, `open_annotations.jsonl`, annotation Parquet files, or answer keys to a model under evaluation. They contain the scene parameters used to derive answers and therefore leak ground truth.

Some tasks intentionally test universal facts or have imbalanced answer distributions. These cases are retained for coverage and are explicitly reported in the audit files; raw accuracy should not be interpreted without the relevant baseline.

## Repository structure

```text
geomstry/
├── README.md
├── OPEN_QUESTION_SPEC.md
├── UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md
├── Dataset/
│   ├── <domain>_dataset_3000/
│   ├── projectile_motion_dataset_1000/
│   ├── final_suite_audit.md
│   └── open_question_rewrite_report.md
├── combined/
│   ├── all_questions_combined.csv
│   ├── all_answers_combined.csv
│   ├── all_open_questions_combined.csv
│   ├── all_open_answers_combined.csv
│   ├── all_answers_combined-*.parquet
│   └── all_annotations_combined-*.parquet
└── spot check/
    └── spot_check_review/
```

Images are stored with Git Large File Storage. Install Git LFS before cloning or pulling the complete repository:

```bash
git lfs install
git clone https://github.com/bilaljawaid980/Geomatric-Reasoning-Benchmark-Dataset.git
```

## Related work

GRIP is an original synthetic benchmark. The following independent projects provide useful context for its task design:

- [GIQ](https://arxiv.org/abs/2506.08194): 3D geometric reasoning with synthetic and real polyhedra
- [Spatial-DISE](https://arxiv.org/abs/2510.13394): a cognitively grounded spatial-reasoning taxonomy
- [CAPTURe](https://arxiv.org/abs/2504.15485): occluded-object counting and amodal reasoning
- [GeoQA](https://aclanthology.org/2021.findings-acl.46/): multimodal numerical reasoning over geometry problems
- [PhysBench](https://arxiv.org/abs/2501.16411): physical-world understanding for vision-language models
- [Analog Clock Reading in the Wild](https://arxiv.org/abs/2111.09162): synthetic-to-real analog-clock recognition
- [MeasureBench](https://arxiv.org/abs/2510.26865): visual measurement and instrument reading

These works are cited as related research only; their authors are not affiliated with or responsible for GRIP.

## Citation

If you use GRIP-Benchmark-34, cite the repository:

```bibtex
@misc{jawaid2026grip,
  author       = {Bilal Jawaid},
  title        = {GRIP-Benchmark-34: A Programmatic Benchmark for Geometry, Reasoning, Induction, and Physics},
  year         = {2026},
  howpublished = {GitHub repository},
  url          = {https://github.com/bilaljawaid980/Geomatric-Reasoning-Benchmark-Dataset}
}
```

## License

GRIP-Benchmark-34 is released under the [MIT License](https://opensource.org/license/mit).
