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
pretty_name: GRIP
size_categories:
  - 100K<n<1M
---

# Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial and Physical Reasoning for Vision-Language Models

## GRIP

GRIP is an anonymous benchmark with 34 procedurally generated reasoning domains, 100,000 images, and 600,000 questions. Deterministic scene programs provide exact ground truth for closed-loop accuracy and open-loop reasoning-stability evaluation.

This repository contains the dataset, generation and evaluation code, analysis, figures, and results for all four experiments.

```bash
git lfs install
python -m pip install -r requirements.txt
```

Use `.env.example` only as a template. Never commit credentials.

## Citation

```bibtex
@misc{anonymous2027grip,
  author = {Anonymous},
  title  = {Geometric Parrots: Rule Absence vs. Rule Fragility in Spatial and Physical Reasoning for Vision-Language Models},
  year   = {2027},
  note   = {Anonymous submission}
}
```

Released under the [MIT License](LICENSE).
