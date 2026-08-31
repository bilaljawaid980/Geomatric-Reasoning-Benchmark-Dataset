# GRIP Impossible Object Dataset 3000 — v4

Version `impossible-object-4.0.0` contains 3,000 depth-order line diagrams and 15,000 questions. The current v4 build occupies the unsuffixed release paths; superseded local builds were removed to keep the repository clean.

## File visibility rule

`question_set.csv` is the **only model-facing file**. It contains exactly four columns: `question_id`, `task`, `image`, and `prompt`. The validator rejects any additional column.

`annotations.jsonl` and `answer_key.csv` are **answer-key-side files**. They intentionally contain ground truth. Raw annotations retain full geometry and derived fields including `mode`, `num_beams`, `num_crossings`, `reference_front_beam`, `removable_beam_label`, `crossings`, and `depth_constraints`.

**Do not expose `annotations.jsonl` or `answer_key.csv` to a tested model. Evaluating against either file leaks the answers.**

Build diagnostics are separate from all three released tables. Per-image `generation_attempt`, `png_recovery_retry`, and the obsolete `visibility_variant` field are absent. Their aggregate distributions are embedded only in `validation_metrics.json`.

## Rendering and geometry

Every scene contains five or six labeled beams. At each crossing, the foreground beam is visibly continuous while the background beam is interrupted. The validator independently recovers beam count, crossing count, and foreground/background order from the final PNG.

V4 retains the v3 leak controls and adds an independently targeted reference-distance gap:

- Label spacing is held near-constant by design on a narrow shared 40–44 px schedule. It is not intended as a varying scene property. Five- and six-beam classes use the same schedule.
- Minimum crossing separation is independently targeted while retaining the hard 8 px floor.
- The distance margin between the closest and second-closest crossings to image center is independently targeted on a shared 13.5–14.5 px schedule, with ±1 px tolerance and the original 12 px hard floor. The schedule is independent of beam count, crossing count, and constructibility mode.
- Stroke color uses an independent deterministic RNG namespace.

Background, canvas dimensions, palette, beam outline style, five question forms, directed beam-label depth schema, and uniform Level 4 crossing-count inversion are unchanged.

## Questions

1. Count labeled beams.
2. Decide whether the displayed depth ordering is physically constructible.
3. At the crossing closest to image center, identify the foreground beam.
4. Count all visible over/under crossings.
5. Name the unique beam whose removal repairs an impossible scene, or answer `already constructible`.

## Label-class caveat

Beam `F` exists only in six-beam scenes. It is therefore structurally underrepresented: 247 Level 3 answers versus 503–622 for A–E, and 125 answers in the Level 5 impossible branch versus approximately 275 for A–E. This is structural, not a sampling defect, and is reflected in the reported constant baselines.

## Validation

The independent validator recomputes geometry and directed-graph consistency, recovers all visual quantities from every PNG, audits every stored scene parameter against every level with Cramér's V, lists every field in each output, runs violating/boundary guard injections, and reports full continuous and categorical distributions.

Full v4 results: 3,000 images checked, 15,000 questions checked, 0 mismatches, and 3,000/3,000 PNG recovery for beam count, crossing count, and per-crossing depth order. Twenty reviewed images were all legible.

```powershell
python .\generate_impossible_object_dataset.py --sample
python .\generate_impossible_object_dataset.py
python .\validate_impossible_object_dataset.py
```
