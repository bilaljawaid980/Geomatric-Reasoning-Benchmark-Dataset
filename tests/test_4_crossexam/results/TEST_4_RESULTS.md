# Test 4 — Cross-Examination Results

Test 4 evaluates how models revise open-ended answers after a second turn. Phase 2 contains three arms: natural peer responses, a constructed unanimous consensus, and a control re-ask with no peer response. Capitulation is a correct-to-wrong transition; correction is a wrong-to-correct transition.

## How to read the results

- **Raw rate:** observed Phase-2 transition rate in that arm.
- **Peer effect:** raw arm rate minus the model's corresponding control rate, expressed in percentage points (pp).
- **95% CI:** bootstrap interval over 10,000 image-level resamples.
- An asterisk marks a peer-effect interval containing zero.
- Capitulation and correction have different denominators and must not be compared directly with each other.

## Natural-peer effects — Arm 1 (%)

| Model | Capitulation raw | Capitulation peer effect (95% CI) | Correction raw | Correction peer effect (95% CI) |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | 8.36 | 5.74 (3.51–7.92) | 12.56 | 8.70 (5.50–11.84) |
| GPT-5.6 Sol | 12.59 | −0.20* (−4.37–3.82) | 28.12 | 23.48 (20.21–26.72) |
| Claude Opus 5 | 5.98 | 5.98 (4.53–7.56) | 11.19 | 10.86 (8.55–13.29) |
| Grok 4.6 | 2.92 | 2.58 (1.19–3.95) | 12.15 | 10.81 (8.67–13.03) |
| Muse Glimmer 30B | 6.38 | −1.62* (−5.65–2.22) | 13.60 | 12.94 (10.52–15.33) |
| DeepSeek V4.1 Flash | 3.90 | 1.20* (−2.17–4.20) | 25.14 | 20.47 (17.49–23.49) |
| Inkling | 5.80 | 3.80* (−0.26–7.49) | 32.39 | 26.46 (23.68–29.30) |
| Claude Sonnet 5 | 9.81 | 9.00 (6.47–11.69) | 30.10 | 27.46 (24.49–30.48) |
| Perplexity Sonar Pro | 13.91 | 3.91* (−1.57–9.12) | 38.56 | **34.87 (31.91–37.73)** |
| GPT-5.6 Luna | 19.73 | **14.76 (10.33–19.18)** | 36.89 | 32.69 (29.69–35.72) |

Adjusted correction is significantly positive for all ten models. Natural-peer capitulation is statistically indistinguishable from control for GPT-5.6 Sol, Muse Glimmer 30B, DeepSeek V4.1 Flash, Inkling, and Perplexity Sonar Pro.

## Constructed-consensus effects — Arm 2 (%)

Three synthetic peers unanimously assert one answer. The row denominators and stored first responses match the natural-peer arm, enabling direct within-model comparison between the two arms.

| Model | Capitulation raw | Capitulation peer effect (95% CI) | Correction raw | Correction peer effect (95% CI) |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | 12.48 | 9.86 (7.40–12.27) | 80.81 | 76.95 (73.32–80.51) |
| GPT-5.6 Sol | 24.77 | 11.98 (7.30–16.52) | 83.18 | 78.54 (75.64–81.28) |
| Claude Opus 5 | 16.16 | 16.16 (14.01–18.37) | 82.51 | 82.18 (79.57–84.66) |
| Grok 4.6 | 16.78 | 16.44 (14.01–18.91) | 78.85 | 77.51 (74.81–80.10) |
| Muse Glimmer 30B | 41.96 | 33.96 (28.94–38.78) | 85.50 | 84.83 (82.34–87.33) |
| DeepSeek V4.1 Flash | 41.29 | 38.59 (33.46–43.72) | 77.06 | 72.39 (69.38–75.25) |
| Inkling | 41.98 | 39.98 (34.08–45.68) | 78.06 | 72.14 (69.39–74.73) |
| Claude Sonnet 5 | 47.65 | 46.84 (43.06–50.65) | 97.45 | **94.81 (92.94–96.47)** |
| Perplexity Sonar Pro | 62.33 | 52.33 (45.75–58.65) | 93.32 | 89.64 (87.54–91.62) |
| GPT-5.6 Luna | 66.27 | **61.30 (56.05–66.20)** | 88.57 | 84.38 (82.04–86.64) |

Constructed consensus produces much larger peer effects than natural peers. The two capitulation intervals are disjoint for nine models; Gemini 3.8 Flash overlaps between 7.40 and 7.92 pp.

## Control instability — Arm 3 (%)

The control condition shows second-turn changes when no peer response is displayed and the model is simply asked for its final answer. These rates are subtracted from Arms 1 and 2 to calculate peer effects.

| Model | Capitulation (95% CI) | Correction (95% CI) |
|---|---:|---:|
| GPT-5.6 Sol | 12.79 (8.84–16.94) | 4.65 (2.72–6.85) |
| Perplexity Sonar Pro | 10.00 (5.45–15.13) | 3.69 (2.15–5.40) |
| Muse Glimmer 30B | 8.00 (4.43–12.00) | 0.66 (0.00–1.69) |
| GPT-5.6 Luna | 4.97 (1.89–8.56) | 4.19 (2.54–6.05) |
| DeepSeek V4.1 Flash | 2.70 (0.62–5.59) | 4.67 (2.77–6.70) |
| Gemini 3.8 Flash | 2.62 (1.08–4.36) | 3.86 (1.64–6.37) |
| Inkling | 2.00 (0.00–5.15) | 5.92 (4.06–7.94) |
| Claude Sonnet 5 | 0.81 (0.00–2.09) | 2.64 (1.20–4.26) |
| Grok 4.6 | 0.34 (0.00–1.07) | 1.34 (0.27–2.62) |
| Claude Opus 5 | 0.00 (0.00–0.00) | 0.33 (0.00–1.05) |

GPT-5.6 Sol shows the greatest control capitulation, abandoning a correct answer on 12.79% of control re-asks. Perplexity Sonar Pro is also high at 10.00%, while Grok 4.6 and Claude Opus 5 are near zero.

## Peer-effect comparison (pp)

| Model | Natural capitulation | Natural correction | Constructed capitulation | Constructed correction |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | 5.74 | 8.70 | 9.86 | 76.95 |
| GPT-5.6 Sol | −0.20 | 23.48 | 11.98 | 78.54 |
| Claude Opus 5 | 5.98 | 10.86 | 16.16 | 82.18 |
| Grok 4.6 | 2.58 | 10.81 | 16.44 | 77.51 |
| Muse Glimmer 30B | −1.62 | 12.94 | 33.96 | 84.83 |
| DeepSeek V4.1 Flash | 1.20 | 20.47 | 38.59 | 72.39 |
| Inkling | 3.80 | 26.46 | 39.98 | 72.14 |
| Claude Sonnet 5 | 9.00 | 27.46 | 46.84 | 94.81 |
| Perplexity Sonar Pro | 3.91 | 34.87 | 52.33 | 89.64 |
| GPT-5.6 Luna | 14.76 | 32.69 | 61.30 | 84.38 |

## Confidence movement

Confidence is the model's self-reported `CONFIDENCE` field, not a calibrated probability. Means are calculated only over rows with valid confidence values in both rounds. The paired count is therefore reported against each arm's total.

| Model | Arm | Paired n/total | Before | After | Δ |
|---|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | Natural peers | 918/1,658 | 0.982 | 0.978 | −0.003 |
| Gemini 3.8 Flash | Constructed | 977/1,925 | 0.982 | 0.986 | 0.005 |
| Gemini 3.8 Flash | Control | 361/641 | 0.980 | 0.983 | 0.003 |
| Claude Opus 5 | Natural peers | 1,661/1,678 | 0.756 | 0.775 | 0.018 |
| Claude Opus 5 | Constructed | 1,952/1,975 | 0.751 | 0.737 | −0.014 |
| Claude Opus 5 | Control | 656/661 | 0.750 | 0.741 | −0.009 |
| Claude Sonnet 5 | Natural peers | 1,669/1,672 | 0.684 | 0.763 | 0.079 |
| Claude Sonnet 5 | Constructed | 1,974/1,975 | 0.677 | 0.671 | −0.006 |
| Claude Sonnet 5 | Control | 663/664 | 0.677 | 0.677 | 0.001 |
| Grok 4.6 | Natural peers | 1,678/1,684 | 0.827 | 0.853 | 0.026 |
| Grok 4.6 | Constructed | 1,989/1,997 | 0.823 | 0.869 | 0.046 |
| Grok 4.6 | Control | 666/667 | 0.823 | 0.835 | 0.012 |
| GPT-5.6 Sol | Natural peers | 1,724/1,724 | 0.950 | 0.946 | −0.004 |
| GPT-5.6 Sol | Constructed | 2,000/2,000 | 0.950 | 0.957 | 0.007 |
| GPT-5.6 Sol | Control | 667/667 | 0.952 | 0.955 | 0.003 |
| GPT-5.6 Luna | Natural peers | 1,670/1,671 | 0.917 | 0.908 | −0.009 |
| GPT-5.6 Luna | Constructed | 1,984/1,985 | 0.917 | 0.951 | 0.033 |
| GPT-5.6 Luna | Control | 661/662 | 0.918 | 0.920 | 0.002 |
| DeepSeek V4.1 Flash | Natural peers | 1,465/1,514 | 0.925 | 0.900 | −0.025 |
| DeepSeek V4.1 Flash | Constructed | 1,662/1,725 | 0.926 | 0.889 | −0.038 |
| DeepSeek V4.1 Flash | Control | 553/576 | 0.923 | 0.926 | 0.003 |
| Inkling | Natural peers | 1,636/1,670 | 0.924 | 0.915 | −0.009 |
| Inkling | Constructed | 1,933/1,974 | 0.927 | 0.877 | −0.050 |
| Inkling | Control | 646/657 | 0.922 | 0.925 | 0.003 |
| Muse Glimmer 30B | Natural peers | 1,118/1,443 | 0.679 | 0.737 | 0.058 |
| Muse Glimmer 30B | Constructed | 1,032/1,496 | 0.646 | 0.651 | 0.005 |
| Muse Glimmer 30B | Control | 411/501 | 0.672 | 0.672 | 0.000 |
| Perplexity Sonar Pro | Natural peers | 1,705/1,719 | 0.869 | 0.886 | 0.017 |
| Perplexity Sonar Pro | Constructed | 1,974/1,989 | 0.871 | 0.891 | 0.020 |
| Perplexity Sonar Pro | Control | 662/665 | 0.871 | 0.871 | 0.000 |

Overall paired-confidence coverage exceeds 97% for eight models. It is lower for Gemini 3.8 Flash and Muse Glimmer 30B, whose responses frequently omit a valid confidence field. Confidence movement is conditional on paired coverage and does not affect answer correctness or the peer-effect estimates.

## Main findings

- Constructed unanimous consensus increases both correction and capitulation much more strongly than natural peer responses for every model.
- Natural peers produce significantly positive adjusted correction for all ten models.
- Five models have natural-peer capitulation intervals containing zero: GPT-5.6 Sol, Muse Glimmer 30B, DeepSeek V4.1 Flash, Inkling, and Perplexity Sonar Pro.
- Gemini 3.8 Flash is the most resistant to constructed-consensus capitulation at 9.86 pp; GPT-5.6 Luna is the most susceptible at 61.30 pp.
- Claude Sonnet 5 has the largest constructed-consensus correction effect at 94.81 pp.
- Control instability varies substantially and must be removed before attributing second-turn changes to peers.
