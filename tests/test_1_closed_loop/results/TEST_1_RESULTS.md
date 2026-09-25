# Test 1 — Closed-Loop Results

Test 1 evaluates accuracy across five reasoning positions, from direct observation (Q1) through counterfactual reasoning (Q5). Results cover 16 models: 10 hosted models and 6 open-weight models.

## Comparator note

Hosted-model values use the typed comparator. Open-weight values use the original comparator because their raw responses are not available in this repository for typed re-scoring. Results are internally consistent within each tier but should not be treated as directly comparator-equivalent across tiers.

## Accuracy by question position (%)

The mean is each model's overall Test-1 accuracy.

| Tier | Model | Q1 | Q2 | Q3 | Q4 | Q5 | Mean |
|---|---|---:|---:|---:|---:|---:|---:|
| Hosted | Gemini 3.8 Flash | 82.8 | 76.6 | 65.3 | 52.4 | 67.3 | **68.9** |
| Hosted | Claude Opus 5 | 80.2 | 76.0 | 60.9 | 47.3 | 65.4 | **66.0** |
| Hosted | Grok 4.6 | 67.4 | 69.3 | 52.2 | 38.8 | 57.6 | **57.1** |
| Hosted | GPT-5.6 Sol | 71.4 | 65.5 | 50.9 | 35.9 | 48.3 | **54.4** |
| Hosted | Claude Sonnet 5 | 67.1 | 68.8 | 50.2 | 37.7 | 47.4 | **54.2** |
| Hosted | Muse Glimmer 30B | 71.8 | 57.7 | 35.6 | 31.5 | 42.2 | **47.7** |
| Hosted | DeepSeek V4.1 Flash | 67.1 | 53.5 | 40.2 | 30.2 | 39.7 | **46.1** |
| Hosted | GPT-5.6 Luna | 65.2 | 52.8 | 39.2 | 29.1 | 38.7 | **45.0** |
| Hosted | Perplexity Sonar Pro | 64.9 | 53.1 | 36.4 | 24.5 | 37.1 | **43.2** |
| Hosted | Inkling | 58.6 | 50.3 | 33.2 | 27.1 | 37.1 | **41.3** |
| Open-weight | Qwen3-VL-8B-Instruct | 56.4 | 51.5 | 39.2 | 30.7 | 35.8 | **42.7** |
| Open-weight | Qwen3-VL-8B-Thinking | 58.4 | 51.3 | 37.7 | 26.7 | 29.5 | **40.7** |
| Open-weight | Molmo2-8B | 57.8 | 51.2 | 33.7 | 25.0 | 32.5 | **40.0** |
| Open-weight | InternVL3.5-8B | 52.2 | 48.8 | 33.0 | 21.8 | 28.9 | **36.9** |
| Open-weight | Kimi-VL-A3B-Thinking | 38.7 | 44.4 | 28.8 | 19.5 | 27.4 | **31.8** |
| Open-weight | DeepSeek-VL2-Small | 37.1 | 44.3 | 27.3 | 18.0 | 21.3 | **29.6** |

## Constant-answer baselines by question position (%)

These baselines are the accuracy obtainable without reading the image, computed from the answer key. They are reported separately because the two tiers use different item samples.

| Question position | Description | Hosted | Open-weight |
|---|---|---:|---:|
| Q1 | Direct observation | 31.6 | 32.7 |
| Q2 | Spatial relation | 44.8 | 41.9 |
| Q3 | Measurement | 25.9 | 23.3 |
| Q4 | Multi-step integration | 27.5 | 23.5 |
| Q5 | Counterfactual | 41.4 | 41.9 |
| **Mean** |  | **34.2** | **32.7** |

## Raw accuracy by reasoning family (%)

Families are ordered by the hosted-tier fleet mean, strongest first. The mean is the domain-count-weighted mean over the nine families and reproduces each model's overall accuracy in the preceding table. Bold marks the strongest family within each model row; underlining marks the weakest.

| Tier | Model | Physical | Inductive | Analytic | Transformational | Solid | Projective | Plane | Optical | Topological | Mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hosted | Gemini 3.8 Flash | 79.4 | **83.2** | 79.2 | 69.7 | 61.5 | 68.0 | 65.0 | 62.0 | <u>57.7</u> | **68.9** |
| Hosted | Claude Opus 5 | 77.8 | **83.2** | 78.6 | 64.3 | 62.1 | 67.4 | 65.3 | 51.4 | <u>48.4</u> | **66.0** |
| Hosted | Grok 4.6 | **72.8** | 65.2 | 64.4 | 55.2 | 56.9 | 51.4 | 52.1 | <u>39.4</u> | 40.8 | **57.1** |
| Hosted | GPT-5.6 Sol | 63.1 | **63.2** | 59.8 | 53.3 | 56.6 | 47.8 | 51.8 | <u>39.4</u> | 44.3 | **54.4** |
| Hosted | Claude Sonnet 5 | **68.3** | 66.4 | 58.6 | 50.6 | 55.6 | 47.8 | 45.0 | 51.4 | <u>40.5</u> | **54.2** |
| Hosted | Muse Glimmer 30B | **58.3** | 53.2 | 48.6 | 42.7 | 44.5 | 50.2 | 50.2 | <u>32.4</u> | 41.6 | **47.7** |
| Hosted | DeepSeek V4.1 Flash | **58.6** | 58.4 | 44.8 | 48.7 | 40.7 | 50.2 | 42.4 | 35.0 | <u>30.7</u> | **46.2** |
| Hosted | GPT-5.6 Luna | **52.8** | 51.6 | 47.6 | 45.7 | 47.7 | 38.0 | 42.6 | 36.8 | <u>30.0</u> | **45.0** |
| Hosted | Perplexity Sonar Pro | **51.0** | 42.0 | 38.8 | 44.6 | 44.3 | 40.2 | 41.8 | 39.4 | <u>30.4</u> | **43.2** |
| Hosted | Inkling | 45.4 | 36.8 | 36.4 | 43.4 | **46.7** | 43.8 | 37.4 | 35.2 | <u>30.5</u> | **41.3** |
| Open-weight | Qwen3-VL-8B-Instruct | 46.0 | **56.0** | 43.3 | 39.5 | 49.3 | 49.5 | 36.0 | <u>32.7</u> | 37.4 | **42.8** |
| Open-weight | Qwen3-VL-8B-Thinking | 52.7 | **61.5** | 31.9 | 39.1 | 41.8 | 53.6 | 29.3 | <u>27.8</u> | 32.9 | **40.8** |
| Open-weight | Molmo2-8B | **48.4** | 36.4 | 32.8 | 43.0 | 43.1 | 42.1 | 32.1 | 32.3 | <u>31.0</u> | **40.1** |
| Open-weight | InternVL3.5-8B | **46.4** | 34.9 | <u>26.1</u> | 33.2 | 45.2 | 36.8 | 31.4 | 30.0 | 28.7 | **37.0** |
| Open-weight | Kimi-VL-A3B-Thinking | 35.9 | 29.2 | <u>16.4</u> | 32.1 | 37.1 | **39.8** | 27.3 | 26.0 | 28.4 | **31.8** |
| Open-weight | DeepSeek-VL2-Small | 29.1 | 24.6 | <u>20.3</u> | 28.4 | **36.6** | 28.2 | 29.4 | 30.6 | 27.1 | **29.6** |

## Summary

- Gemini 3.8 Flash leads the hosted tier at **68.9%**, followed by Claude Opus 5 at **66.0%**.
- Qwen3-VL-8B-Instruct leads the open-weight tier at **42.7%** in the position table and **42.8%** in the rounded family table.
- Accuracy generally declines from direct observation toward multi-step integration, with partial recovery at Q5 for most models.
- Physical and Inductive reasoning are the strongest hosted-tier families overall; Topological reasoning is generally the weakest.
- The one-decimal means shown here are transcribed from the supplied result tables. Small 0.1-point differences between tables reflect their reported rounding.
