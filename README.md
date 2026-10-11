---
license: mit
language:
  - en
task_categories:
  - visual-question-answering
tags:
  - vision-language
  - multimodal-reasoning
  - geometric-reasoning
  - spatial-reasoning
  - visual-reasoning
  - physical-reasoning
  - procedural-generation
  - synthetic
  - exact-ground-truth
  - robustness
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

# GRIP

**Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial and Physical Reasoning for Vision-Language Models**

GRIP is a procedurally generated benchmark for evaluating geometric, spatial, visual, and physical reasoning in vision-language models. It pairs deterministic scene generation with exact answers computed from the same latent scene state, avoiding human-label ambiguity and enabling controlled analysis of both reasoning ability and reasoning stability.

## Dataset summary

| Property | Value |
|---|---:|
| Images | 100,000 |
| Reasoning domains | 34 |
| Reasoning families | 9 |
| Closed-loop questions | 500,000 |
| Open-response questions | 100,000 |
| Total questions | 600,000 |
| Language | English |
| License | MIT |

The nine reasoning families are **plane, solid, transformational, physical, topological, projective, analytic, optical, and inductive reasoning**.

## Benchmark design

### Procedural scenes and exact ground truth

Each image is rendered from a deterministic seeded program. The generator uses the same scene parameters to derive the answer, rejects samples near decision boundaries or rounding ties, and stores detailed scene annotations. This makes difficulty and correctness properties of generation rather than post-hoc human annotation.

### Dual-Loop Evaluation

- **Closed loop:** five questions are asked in fresh single-turn conversations. They progress from direct observation through relational reasoning, measurement, multi-step integration, and counterfactual reasoning.
- **Open loop:** a free-response question supports controlled re-elicitation under no-challenge controls, unsupported user assertions, and peer-model responses.

Because every target is known exactly, answer changes can be signed. A **correction** moves from an incorrect answer to the ground truth; a **capitulation** abandons a correct answer. GRIP therefore separates **rule absence** from **rule fragility**.

## Dataset configurations

| Config | Rows | Contents |
|---|---:|---|
| `closed_loop` | 500,000 | Five question levels per image, prompts, answer formats, exact targets, and images |
| `open_loop` | 100,000 | One open-response prompt per image with acceptance sets, tolerances, targets, and structured answers |
| `scene_annotations` | 100,000 | Images, generation parameters, latent scene state, and domain-specific derived quantities |

All configurations use a single `test` split because GRIP is an evaluation benchmark. The repository also retains combined question-only CSV files and the original per-domain files for transparent inspection and reproducibility.

## Loading the data

Install the core dependencies:

```bash
python -m pip install -r requirements.txt
```

Load a configuration from the Hugging Face Hub:

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
```

For low-memory inspection, add `streaming=True`. A full repository clone requires Git LFS:

```bash
git lfs install
git clone <repository-url>
```

## Key fields

### `closed_loop`

- `dataset`, `dataset_version`: domain and generator version
- `question_id`: stable question identifier
- `task`: position in the five-level reasoning ladder
- `image_bytes`: embedded image data
- `image`, `image_path`: image identifiers and repository-relative paths
- `prompt`: question text
- `groundtruth`: exact answer
- `answer_format`: required response type

### `open_loop`

- `question_id`, `image`, `image_path`, `prompt`
- `acceptance_set`: accepted structured answer representation
- `tolerances`: explicit numeric tolerances where applicable
- `targets`: visual entities or quantities that must be recovered
- domain-specific structured target columns

### `scene_annotations`

The common fields identify the domain, version, scene, image, and seed. Remaining fields store domain-specific latent parameters and derived quantities. Unused domain-specific columns are null.

## Evaluation protocols and results

| Test | Purpose | Results |
|---|---|---|
| Test 1 | Closed-loop accuracy by question level and reasoning family | [TEST_1_RESULTS.md](tests/test_1_closed_loop/results/TEST_1_RESULTS.md) |
| Test 2 | Robustness to controlled visual noise | [TEST_2_RESULTS.md](tests/test_2_grain_robustness/results/TEST_2_RESULTS.md) |
| Test 3 | Corrections and capitulations under unsupported challenge | [TEST_3_RESULTS.md](tests/test_3_sycophancy/results/TEST_3_RESULTS.md) |
| Test 4 | Natural-peer, constructed-consensus, control, and confidence effects | [TEST_4_RESULTS.md](tests/test_4_crossexam/results/TEST_4_RESULTS.md) |

The evaluation implementation is in [`grip_eval/`](grip_eval/), with experiment-specific scripts and archived outputs under [`tests/`](tests/).

## Repository structure

```text
Dataset/       Per-domain images, annotations, questions, validators, and generators
combined/      Hub-ready closed-loop, open-loop, and scene-annotation tables
grip_eval/     Shared parsing and evaluation utilities
tests/         Protocols, scripts, results, and archived model responses
analysis/      Aggregate analyses and audit outputs
figures/       Paper figures and selected qualitative samples
scripts/       Repository-level validation and maintenance utilities
```

## Intended use and limitations

GRIP is intended for research on vision-language reasoning, robustness, calibration, and interaction-dependent answer stability. It is suitable for evaluation, error analysis, and controlled comparison of multimodal systems.

The benchmark is synthetic and should not be treated as evidence of real-world physical competence. Performance may depend on prompting, image preprocessing, decoding settings, and answer parsing. The domains test selected geometric and physical abstractions; they do not cover every form of perception, commonsense reasoning, or embodied interaction. Researchers should report model versions, prompts, image transforms, decoding parameters, and scoring rules.

All scenes are procedurally generated and contain no people, personal information, or scraped user content.

## Reproducibility

Per-domain directories include generator versions, build manifests, validation reports, and exact answer keys. Closed-loop question construction is documented in [`UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md`](UNIFIED_5_LEVEL_GENERATION_TEMPLATE.md); open-response construction is documented in [`OPEN_QUESTION_SPEC.md`](OPEN_QUESTION_SPEC.md).

Use immutable commit revisions when reporting results. Do not expose answer keys to a model during evaluation.

## License

GRIP, including its procedurally generated data and accompanying code, is released under the [MIT License](LICENSE).

## Citation

If you use GRIP, cite the accompanying preprint:

```bibtex
@misc{jawaid2026geometric,
  author = {Bilal Jawaid and Hamza Hanif and Muhammad Maaz Uddin and Anas Zafar and Inad Alqurashi and Aizan Zafar and Osama Farooqui and Sheheryar Khan and Ferhat Sadak and Shaina Raza and Rizwan Qureshi},
  title = {Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial and Physical Reasoning for Vision-Language Models},
  year = {2026},
  note = {arXiv preprint}
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

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and validation requirements, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards, and [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.
