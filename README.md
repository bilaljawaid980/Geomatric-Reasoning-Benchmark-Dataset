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

# GRIP: Geometry, Reasoning, Induction, and Physics

GRIP is a programmatically generated benchmark for evaluating visual reasoning in multimodal models. It contains **100,000 images**, **500,000 closed-loop questions**, and **100,000 open-response questions** across **34 domains** and **nine reasoning families**.

Unlike benchmarks built from human-written labels, every GRIP scene is generated from deterministic latent state. The same state renders the image and computes its ground truth. Generators reject scenes near decision boundaries, rounding ties, or classification thresholds and record the relevant safety margin, making difficulty a controlled property of generation rather than an annotation artifact.

## Benchmark design

The 34 domains cover nine families: **plane, solid, transformational, physical, topological, projective, analytic, optical, and inductive reasoning**.

Every image has five ordered closed-loop questions and one open-response question:

| Position | Reasoning stage |
|---|---|
| Q1 | Direct observation |
| Q2 | Spatial or relational reasoning |
| Q3 | Measurement or structural reasoning |
| Q4 | Multi-step integration |
| Q5 | Counterfactual reasoning |

### Dual-loop evaluation

- **Closed loop:** asks Q1–Q5 independently in fresh single-turn conversations, measuring reasoning without conversational carry-over.
- **Open loop:** re-elicits answers under controlled challenge, including unsupported user assertions, natural peer responses, constructed consensus, and no-challenge controls.
- **Signed transitions:** a wrong-to-right change is a **correction**; a right-to-wrong change is a **capitulation**. Reporting them separately distinguishes missing competence from fragile competence.

## Evaluation results

The repository contains four experiments. The table below gives the main result from each; complete tables are linked in the final column.

| Test | What it measures | Headline result | Full results |
|---|---|---|---|
| **E1: Closed-loop accuracy** | Independent Q1–Q5 visual reasoning | Gemini 3.8 Flash leads the hosted tier at **68.9%**, followed by Claude Opus 5 at **66.0%**. Qwen3-VL-8B-Instruct leads the reported open-weight tier at **42.7%**. | [Test 1 results](tests/test_1_closed_loop/results/TEST_1_RESULTS.md) |
| **E2: Grain robustness** | Accuracy under deterministic Gaussian image grain | Gemini changes by only **−0.1 pp** from sigma 0 to 40. Claude Opus shows the largest reported decline, **−6.1 pp**. | [Test 2 results](tests/test_2_grain_robustness/results/TEST_2_RESULTS.md) |
| **E3: Answer sycophancy** | Response to true and false user assertions | Adjusted capitulation ranges from **6.18%** for Gemini to **72.75%** for Inkling. GPT-5.6 Sol has the highest adjusted correction rate, **58.37%**. | [Test 3 results](tests/test_3_sycophancy/results/TEST_3_RESULTS.md) |
| **E4: Cross-examination** | Response to natural peers, unanimous synthetic peers, and control re-asks | Natural peers improve correction significantly for all ten hosted models. Constructed consensus produces stronger correction and capitulation effects for every model. | [Test 4 results](tests/test_4_crossexam/results/TEST_4_RESULTS.md) |

### E1 accuracy by question position (%)

| Model | Q1 | Q2 | Q3 | Q4 | Q5 | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Gemini 3.8 Flash | 82.8 | 76.6 | 65.3 | 52.4 | 67.3 | **68.9** |
| Claude Opus 5 | 80.2 | 76.0 | 60.9 | 47.3 | 65.4 | **66.0** |
| Grok 4.6 | 67.4 | 69.3 | 52.2 | 38.8 | 57.6 | **57.1** |
| GPT-5.6 Sol | 71.4 | 65.5 | 50.9 | 35.9 | 48.3 | **54.4** |
| Claude Sonnet 5 | 67.1 | 68.8 | 50.2 | 37.7 | 47.4 | **54.2** |
| Muse Glimmer 30B | 71.8 | 57.7 | 35.6 | 31.5 | 42.2 | **47.7** |
| DeepSeek V4.1 Flash | 67.1 | 53.5 | 40.2 | 30.2 | 39.7 | **46.1** |
| GPT-5.6 Luna | 65.2 | 52.8 | 39.2 | 29.1 | 38.7 | **45.0** |
| Perplexity Sonar Pro | 64.9 | 53.1 | 36.4 | 24.5 | 37.1 | **43.2** |
| Inkling | 58.6 | 50.3 | 33.2 | 27.1 | 37.1 | **41.3** |

Hosted E1 values use the typed comparator. The six open-weight models in the full Test 1 table use the original comparator because their raw responses are unavailable in this repository for typed re-scoring; comparisons across those two tiers should therefore be made cautiously.

## Dataset files

| File | Rows | Contents |
|---|---:|---|
| `combined/all_questions_combined.csv` | 500,000 | Closed questions without answers |
| `combined/all_answers_combined.csv` | 500,000 | Closed questions with reference answers |
| `combined/all_open_questions_combined.csv` | 100,000 | Open questions without targets |
| `combined/all_open_answers_combined.csv` | 100,000 | Open questions with structured targets |
| `combined/all_answers_combined-*.parquet` | 500,000 | Closed-answer viewer shards with embedded images |
| `combined/all_annotations_combined-*.parquet` | 100,000 | Scene metadata with embedded images |

Use the question-only files as model input. Answer keys and annotation files contain latent scene information and must not be exposed to evaluated models.

## Repository layout

```text
Dataset/                       Domain generators, images, questions and validation
combined/                      Combined CSV and Parquet releases
grip_eval/                     Shared model, parsing and evaluation utilities
tests/test_1_closed_loop/      E1: independent Q1–Q5 accuracy
tests/test_2_grain_robustness/ E2: deterministic visual-noise robustness
tests/test_3_sycophancy/       E3: user-assertion challenges
tests/test_4_crossexam/        E4: peer-response cross-examination
analysis/                      Comparator and aggregate analyses
figures/                       Paper figures and qualitative samples
```

## Getting the data

Images are stored with Git LFS:

```bash
git lfs install
git clone https://github.com/bilaljawaid980/Geomatric-Reasoning-Benchmark-Dataset.git
```

Install the evaluation dependencies with:

```bash
python -m pip install openai pillow pandas numpy python-dotenv
```

## Citation

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

Released under the [MIT License](https://opensource.org/license/mit).
