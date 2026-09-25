# Test 2 — Grain Robustness Results

Test 2 measures how closed-loop accuracy changes when deterministic monochrome Gaussian grain is added to the benchmark images. The evaluation uses the fixed 680-image core subset: 20 images from each of 34 domains, with five questions per image, giving 3,400 evaluated question rows per model at each noise level.

## Noise conditions

- **σ = 0:** original image, without added grain.
- **σ = 15, 25, 40:** one deterministic monochrome Gaussian-noise field is added equally to all three RGB channels.
- Every model receives the same altered pixels for a given image and noise level.
- **Δ** is the change from σ = 0 to σ = 40. Negative values indicate an accuracy loss under the strongest tested grain.

## Accuracy at each noise level (%)

| Rank at σ=0 | Model | σ=0 | σ=15 | σ=25 | σ=40 | Δ |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Gemini 3.8 Flash | **64.1** | **65.5** | **64.7** | **64.0** | **−0.1** |
| 2 | Claude Opus 5 | 62.4 | 59.9 | 58.6 | 56.2 | −6.1 |
| 3 | Grok 4.6 | 52.7 | 51.2 | 51.3 | 50.4 | −2.4 |
| 4 | GPT-5.6 Sol | 50.8 | 50.9 | 51.0 | 49.8 | −1.1 |
| 5 | Claude Sonnet 5 | 49.7 | 48.4 | 47.6 | 47.1 | −2.6 |
| 6 | Muse Glimmer 30B | 44.4 | 42.4 | 43.6 | 42.4 | −1.9 |
| 7 | DeepSeek V4.1 Flash | 43.2 | 39.3 | 40.1 | 39.1 | −4.1 |
| 8 | GPT-5.6 Luna | 42.4 | 41.8 | 42.0 | 40.3 | −2.1 |
| 9 | Perplexity Sonar Pro | 41.8 | 41.4 | 40.9 | 39.4 | −2.4 |
| 10 | Inkling | 38.7 | 36.8 | 35.7 | 34.4 | −4.3 |

## Main findings

- **Gemini 3.8 Flash** is both the most accurate model and the most robust to added grain. Its reported change at σ = 40 is only **−0.1 percentage points**.
- **GPT-5.6 Sol** has the second-smallest degradation at **−1.1 points**.
- **Claude Opus 5** experiences the largest reported degradation, falling from 62.4% to 56.2%, with a reported Δ of **−6.1 points**.
- **Inkling** and **DeepSeek V4.1 Flash** also show comparatively large losses of **−4.3** and **−4.1 points**, respectively.
- Small non-monotonic changes at intermediate noise levels are visible for several models. For example, Gemini improves at σ = 15, while GPT-5.6 Sol and Muse Glimmer 30B partially recover at σ = 25.
- The ranking is broadly stable under the strongest grain: Gemini remains first, Claude Opus remains second, and Inkling remains last.

## Rounding note

The values above are transcribed from the supplied result table. Accuracy columns and Δ were calculated from underlying unrounded values before display, so subtracting the displayed one-decimal endpoints may differ from the displayed Δ by 0.1 point for some models.
