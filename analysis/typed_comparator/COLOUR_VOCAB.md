# Colour-vocabulary audit

No colour normalization is applied by the typed comparator.

## `depth_height`

| Key label | RGB | Hex |
|---|---:|---:|
| `teal` | `(56, 171, 159)` | `#38AB9F` |
| `magenta` | `(205, 75, 139)` | `#CD4B8B` |
| `orange` | `(232, 133, 55)` | `#E88537` |
| `blue` | `(64, 139, 207)` | `#408BCF` |
| `purple` | `(143, 104, 190)` | `#8F68BE` |

The generator drawing code renders shapes/stack outlines only. It draws no text, legend, key, or colour-name label. L3 asks for a ranking “by color” but never enumerates the five permitted labels. L2 and L5 do name the colours used in their particular comparison, so those variants are locally discoverable; L3 is not.

Off-vocabulary L3 tokens are aligned by response position to show the keyed label they replaced. Counts are token occurrences, not necessarily whole-response counts:

| Model | Off-vocabulary tokens | Observed substitutions |
|---|---|---|
| Claude Opus 5 | 33 | `pink→magenta` ×33 |
| Claude Sonnet 5 | 34 | `pink→magenta` ×26, `pink→blue` ×4, `pink→purple` ×2, `pink→teal` ×1, `pink→orange` ×1 |
| DeepSeek V4.1 Flash | 37 | `pink→magenta` ×32, `green→teal` ×2, `green→purple` ×1, `pink→teal` ×1, `cyan→teal` ×1 |
| Gemini 3.8 Flash | 39 | `pink→magenta` ×33, `cyan→teal` ×3, `green→teal` ×3 |
| GPT-5.6 Luna | 33 | `pink→magenta` ×28, `pink→blue` ×2, `pink→teal` ×1, `pink→purple` ×1, `pink→orange` ×1 |
| GPT-5.6 Sol | 33 | `pink→magenta` ×30, `pink→orange` ×1, `pink→purple` ×1, `pink→blue` ×1 |
| Grok 4.6 | 34 | `pink→magenta` ×29, `pink→teal` ×2, `green→teal` ×2, `black→magenta` ×1 |
| Inkling | 46 | `pink→magenta` ×23, `cyan→teal` ×8, `cyan→blue` ×4, `pink→purple` ×2, `pink→blue` ×2, `cyan→magenta` ×2, `cyan→purple` ×1, `pink→teal` ×1, `pink→orange` ×1, `green→teal` ×1, `cyan→orange` ×1 |
| Muse Glimmer 30B | 37 | `pink→magenta` ×27, `pink→purple` ×4, `green→teal` ×3, `pink→teal` ×1, `pink→blue` ×1, `pink→orange` ×1 |
| Perplexity Sonar Pro | 36 | `pink→magenta` ×31, `green→teal` ×2, `pink→purple` ×1, `pink→blue` ×1, `pink→orange` ×1 |

**Conclusion:** the L3 vocabulary is not discoverable from the pixels or prompt. Off-vocabulary names remain wrong under the comparator, but this is an unstated-convention domain defect. The appropriate remedy is to state the palette in the prompt and regenerate questions—not to add aliases. No remedy is applied here.

## Other closed colour vocabularies

| Cell/variant | Generator palette | Image names colours? | Prompt enumerates vocabulary? | Conclusion |
|---|---|---|---|---|
| `depth_height` L2 | same five labels above | no | yes, the two relevant colours | discoverable for that item |
| `shadow_inference` L3 colour branch | blue `#4C8BB5`, orange `#D77941`, teal `#419C94`, purple `#8E69B2` | no | no | same unstated-convention defect |
| `shadow_inference` L4 colour branch | same four labels | no | no | same unstated-convention defect |
| `line_intersection` L3 colour branch | red/blue | no legend required | yes, red and blue are named in the question | discoverable |

The remaining closed vocabularies are either written as options in the question (`yes/no`, directional choices, comparisons), use conventional numeric/clock notation, or use letters/labels visibly printed in the image. The audit found no other hidden generator-only naming vocabulary comparable to the two colour domains above.
