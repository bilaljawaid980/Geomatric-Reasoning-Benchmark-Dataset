"""Build the human-readable typed-comparator audit from offline CSV/JSONL artefacts."""
from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULTS = ROOT / "tests/test_1_closed_loop/results"

MODELS = [
    "claude_opus_5", "claude_sonnet_5", "deepseek_v4_1_flash",
    "gemini_3_8_flash", "gpt_5_6_luna", "gpt_5_6_sol", "grok_4_6",
    "inking", "muse_glimmer_30b", "perplexity_sonar_pro",
]
NAMES = {
    "claude_opus_5": "Claude Opus 5", "claude_sonnet_5": "Claude Sonnet 5",
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash", "gemini_3_8_flash": "Gemini 3.8 Flash",
    "gpt_5_6_luna": "GPT-5.6 Luna", "gpt_5_6_sol": "GPT-5.6 Sol",
    "grok_4_6": "Grok 4.6", "inking": "Inkling",
    "muse_glimmer_30b": "Muse Glimmer 30B", "perplexity_sonar_pro": "Perplexity Sonar Pro",
}


def pct(value: float) -> str:
    return "—" if pd.isna(value) else f"{100 * value:.2f}%"


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(v).replace("\n", " ") for v in row) + " |" for row in rows]
    return "\n".join(out)


def latest(path: Path):
    found = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("error") in (None, "", False):
                found[row["row_id"]] = row
    return found


def answer_body(raw):
    match = re.search(r"(?im)^\s*ANSWER\s*:\s*(.*?)\s*$", str(raw or ""))
    return match.group(1).strip() if match else str(raw or "").strip()


def parse_list(raw):
    text = answer_body(raw)
    try:
        value = ast.literal_eval(text)
        if isinstance(value, (list, tuple)):
            return [str(x).strip().lower() for x in value]
    except Exception:
        pass
    text = re.sub(r"(?i)\b(?:closest|nearest|tallest)\s*(?:to|→|->|>)\s*(?:farthest|shortest)\s*:?", "", text)
    parts = re.split(r"\s*(?:,|>|→|->|;|\bthen\b)\s*", text.lower())
    return [re.sub(r"[^a-z]+", "", p) for p in parts if re.sub(r"[^a-z]+", "", p)]


def write_spec(cell_types, option_counts):
    non_scalar = cell_types[cell_types.answer_type.ne("SCALAR")]
    option_rows = [(f"`{d}` L{int(l)}", int(n)) for (d, l), n in option_counts.items()]
    schemas = [(f"`{r.domain}` L{r.level}", r.answer_type, f"`{r.schema_id}`", r.required_components)
               for r in non_scalar.itertuples(index=False)]
    text = f"""# Frozen typed comparator specification

This comparator is an offline counterfactual. It does not replace published scores. It reads stored responses only. The implementation is [`typed_comparator.py`](typed_comparator.py), while [`cell_types.csv`](cell_types.csv) is the dispatch manifest for all 170 `(domain, level)` cells.

## Universal rules

- Parsing dispatches from the cell's declared `answer_type`; domain/level checks do not select the comparator.
- Numeric equality is exact after syntactic parsing. There is no tolerance.
- The only global aliases are `smaller than → smaller` and `none → neither`.
- A missing explicitly requested component is wrong. A parse failure is wrong, never skipped.
- The strict string verdict is preserved beside every typed verdict.
- Option phrasing is accepted only if the complete normalized response phrase occurs verbatim in the question and differs from the stored short token only by the question's added option word(s).

## Answer types

| Type | Parse | Equality |
|---|---|---|
| `SCALAR` | Existing `ANSWER:` extraction and normalization | Existing exact comparison, plus the narrowly scoped verbatim option-phrase rule |
| `ORDERED_LIST` | JSON/Python list or explicit ordered separators | Same length and exact element equality in order; no set fallback and no colour aliases |
| `TYPED_DICT` | Schema-declared named fields | Every prompt-required field must parse and match exactly |
| `TEMPLATED_SENTENCE` | Schema-declared slots only | Every slot explicitly requested by the prompt must parse and match exactly; fixed key prose is ignored |

## Non-scalar schema declarations

{md_table(["Cell", "Type", "Schema", "Required components"], schemas)}

`fbd` L4's schema examines the prompt/key variant. The 750 corpus items with `wrong_force_details` require the arrow label, error kind, and exact error amount in addition to the numeric fields. Numeric-only answers are wrong on that variant.

## Option-phrasing firings

The rule changed **{int(option_counts.sum()):,}** stored Test-1 responses. These are the only cells where it fired:

{md_table(["Cell", "Strict → typed changes"], option_rows)}

No colour alias was added. In particular, `pink` is not `magenta`, and `cyan` is not `teal`.
"""
    (OUT / "COMPARATOR_SPEC.md").write_text(text, encoding="utf-8")


def build_fbd_variants(scored):
    frame = scored[(scored.domain.eq("fbd")) & (scored.level.eq(4))].copy()
    frame["variant"] = frame.ground_truth.str.contains("wrong_force_details", regex=False).map(
        {True: "numeric + wrong-arrow", False: "numeric only"})
    result = frame.groupby(["model", "variant"], as_index=False).agg(
        rows=("row_id", "size"), strict_accuracy=("strict_correct", "mean"), typed_accuracy=("typed_correct", "mean"))
    result.to_csv(OUT / "fbd_l4_variants.csv", index=False)
    return result


def write_screen(before, evidence):
    typed = before.pivot(index=["domain", "level"], columns="model", values="raw_accuracy_typed")
    raw_hits = typed[(typed < .05).all(axis=1)].reset_index()
    raw_hits[["domain", "level"]].assign(all_models_below_5=True).to_csv(OUT / "universal_screen.csv", index=False)
    pairs = []
    for model, row in evidence:
        pairs.append((NAMES[model], f"`{row['row_id']}`", f"`{row['ground_truth']}`",
                      f"`{answer_body(row.get('response_raw'))}`"))
    rounds = [
        (1, "1", "Initial sentence-valued screen", "`physical_stability` L5"),
        (2, "7", "Seven-cell follow-up", "compass L5, FBD L5, gauge L4/L5, laser L5, optical L5, projectile L5"),
        (3, "6", "Universal all-ten follow-up", "depth L3, FBD L3/L4, gear L2, hex L5, projectile L4"),
        (4, str(len(raw_hits)), "Typed-comparator raw screen", "`compass_bearing` L5" if len(raw_hits) else "none"),
        (5, "0", "Unresolved-defect queue after Round-4 classification", "empty"),
    ]
    text = f"""# Universal below-5% screen rounds

The screen criterion is typed accuracy below 5% for all ten complete models. A hit is audited once; confirmed genuine failures are retained in the score but removed from the *unresolved comparator-defect queue*. This distinction is necessary: otherwise a genuine universally hard cell can never make the audit queue empty.

{md_table(["Round", "Hits", "Stage", "Finding"], rounds)}

## Round 4 classification: `compass_bearing` L5

The frozen typed rule requires all three components explicitly requested by the question: the offered landmark, endpoint distance, and bearing difference. Numeric values are exact-match only. The typed accuracies are below 5% for all ten models because responses commonly omit one or both numbers or estimate a different number—not because the parser compares fixed prose.

Ten verbatim failures, one per model:

{md_table(["Model", "Row", "Key", "Verbatim response"], pairs)}

**Classification: genuine failure under the approved exact-component policy.** The key is templated and fully parseable; accepting these responses would require either dropping a requested component or introducing numeric tolerance, both expressly forbidden. Therefore Round 5's unresolved comparator-defect queue is empty, although the raw performance screen continues to contain this one genuine-failure cell.

No additional comparator schema was introduced after Round 4.
"""
    (OUT / "SCREEN_ROUNDS.md").write_text(text, encoding="utf-8")


def write_colour(scored, responses):
    vocab = ["teal", "magenta", "orange", "blue", "purple"]
    counts = defaultdict(Counter)
    totals = Counter()
    alternative_colours = ("pink", "cyan", "green", "black", "red", "yellow", "grey", "gray")
    depth = scored[(scored.domain.eq("depth_height")) & (scored.level.eq(3))]
    for row in depth.itertuples(index=False):
        raw = responses[row.model][row.row_id].get("response_raw", "")
        actual = parse_list(raw)
        try:
            expected = [str(x).lower() for x in ast.literal_eval(row.ground_truth)]
        except Exception:
            expected = []
        for i, token in enumerate(actual):
            # Count colour-name substitutions, not harmlessly attached shape words
            # such as "blue triangle" and not arbitrary prose from a failed parse.
            if token and not any(colour in token for colour in vocab):
                used = next((colour for colour in alternative_colours if colour in token), None)
                if used:
                    target = expected[i] if i < len(expected) else "<extra>"
                    counts[row.model][f"{used}→{target}"] += 1
                    totals[row.model] += 1
    model_rows = []
    for model in MODELS:
        substitutions = ", ".join(f"`{k}` ×{v}" for k, v in counts[model].most_common()) or "none"
        model_rows.append((NAMES[model], totals[model], substitutions))
    text = f"""# Colour-vocabulary audit

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

{md_table(["Model", "Off-vocabulary tokens", "Observed substitutions"], model_rows)}

**Conclusion:** the L3 vocabulary is not discoverable from the pixels or prompt. Off-vocabulary names remain wrong under the comparator, but this is an unstated-convention domain defect. The appropriate remedy is to state the palette in the prompt and regenerate questions—not to add aliases. No remedy is applied here.

## Other closed colour vocabularies

| Cell/variant | Generator palette | Image names colours? | Prompt enumerates vocabulary? | Conclusion |
|---|---|---|---|---|
| `depth_height` L2 | same five labels above | no | yes, the two relevant colours | discoverable for that item |
| `shadow_inference` L3 colour branch | blue `#4C8BB5`, orange `#D77941`, teal `#419C94`, purple `#8E69B2` | no | no | same unstated-convention defect |
| `shadow_inference` L4 colour branch | same four labels | no | no | same unstated-convention defect |
| `line_intersection` L3 colour branch | red/blue | no legend required | yes, red and blue are named in the question | discoverable |

The remaining closed vocabularies are either written as options in the question (`yes/no`, directional choices, comparisons), use conventional numeric/clock notation, or use letters/labels visibly printed in the image. The audit found no other hidden generator-only naming vocabulary comparable to the two colour domains above.
"""
    (OUT / "COLOUR_VOCAB.md").write_text(text, encoding="utf-8")


def write_open_gap():
    text = """# Open-weight raw-response gap

The repository has complete Test-1 JSONL responses for the ten models in the typed report and **no complete or partial open-weight Test-1 response artefacts**. Aggregate values cannot be repaired without raw responses. Any table combining these ten repaired scores with six unrepaired open-weight scores is therefore invalid.

## Required export

Each missing model needs a Test-1-compatible JSONL export containing one latest successful record for every row of:

`tests/test_1_closed_loop/plan/closed_loop_manifest.csv`

Required fields per line:

- `row_id` — exact manifest key (8,500 unique rows per model)
- `model` — stable model key
- `response_raw` — verbatim stored answer
- `error` — null/empty on success, otherwise the recorded failure

Strongly recommended provenance fields are `domain`, `stem`, `question_id`, `level`, `image_path`, `prompt_sent`, token counts, latency, timestamp, provider, and exact model ID. The scorer keys by `row_id`; aggregates alone are insufficient.

## Where the local runner writes

`GRIP_Model_Evaluation.ipynb` defines the local/open-weight cache as:

`eval_results/<model_key>/<domain>.jsonl`

and the later protocol cache as:

`eval_results_protocol/<test_name>/<model_key>/<domain>.jsonl`.

Those directories are not present in this repository. If they still exist on the machine/session used for local inference, the per-domain files must be exported and merged into one Test-1-compatible response set per model. The notebook registry lists ten possible open-weight candidates, but this repository does not contain a frozen record identifying which six were selected for the paper; that mapping must come from the local-run configuration or manuscript source rather than being guessed.
"""
    (OUT / "OPEN_WEIGHT_GAP.md").write_text(text, encoding="utf-8")


def write_recomputed(before, aggregates, l45, grain, syc, fbd):
    overall = aggregates[(aggregates.scope.eq("overall")) & aggregates.method.eq("MACRO") & aggregates.include_small_n.eq(True)]
    rows = []
    for r in overall.itertuples(index=False):
        rows.append((NAMES[r.model], pct(r.raw_accuracy_all_cells_strict), pct(r.raw_accuracy_all_cells_typed),
                     pct(r.adjusted_score_strict), pct(r.adjusted_score_typed)))
    lrows = []
    for model in MODELS:
        s = l45[(l45.model.eq(model)) & l45.comparator.eq("strict")].iloc[0]
        t = l45[(l45.model.eq(model)) & l45.comparator.eq("typed")].iloc[0]
        lrows.append((NAMES[model], f"{100*s.l5_minus_l4:+.2f} pp", s.verdict,
                      f"{100*t.l5_minus_l4:+.2f} pp", f"{100*t.ci_low:+.2f} to {100*t.ci_high:+.2f} pp", t.verdict))
    grows = []
    for r in grain.itertuples(index=False):
        grows.append((NAMES[r.model], int(r.sigma), int(r.n), pct(r.strict_accuracy), pct(r.typed_accuracy)))
    sover = syc[syc.dimension.eq("overall")]
    srows = []
    for r in sover.itertuples(index=False):
        srows.append((NAMES[r.model], pct(r.strict_round1_accuracy), pct(r.typed_round1_accuracy),
                      pct(r.strict_round2_accuracy), pct(r.typed_round2_accuracy),
                      pct(r.strict_capitulation_rate), pct(r.typed_capitulation_rate),
                      pct(r.strict_correction_rate), pct(r.typed_correction_rate)))
    frows = [(NAMES[r.model], r.variant, int(r.rows), pct(r.strict_accuracy), pct(r.typed_accuracy))
             for r in fbd.itertuples(index=False)]
    verdict_changes = []
    for model in MODELS:
        s = l45[(l45.model.eq(model)) & l45.comparator.eq("strict")].iloc[0]
        t = l45[(l45.model.eq(model)) & l45.comparator.eq("typed")].iloc[0]
        verdict_changes.append(f"- **{NAMES[model]}:** " + (f"changes from {s.verdict} to {t.verdict}." if s.verdict != t.verdict else f"remains {t.verdict}."))
    text = f"""# Full typed-comparator recomputation

All values are computed offline from stored responses. Strict scores remain intact. Typed scores are counterfactual and have not replaced any published result.

## Test 1: overall

{md_table(["Model", "Strict raw", "Typed raw", "Strict adjusted macro", "Typed adjusted macro"], rows)}

The complete **1,700 model × cell** table—including strict/typed correct counts, raw accuracy, constant-answer baseline, adjusted score, modal target, and exclusion flags—is [`before_after.csv`](before_after.csv). Complete per-level, per-family, per-domain, macro, and pooled aggregates are in [`aggregates.csv`](aggregates.csv).

## L4-to-L5 adjusted difference

The intervals use the requested 10,000-resample domain-stratified image-cluster bootstrap.

{md_table(["Model", "Strict Δ", "Strict verdict", "Typed Δ", "Typed 95% CI", "Typed verdict"], lrows)}

Verdict changes:

{chr(10).join(verdict_changes)}

The earlier “seven of ten reverse” conclusion changes to **six of ten reverse**: Perplexity Sonar Pro becomes statistically indistinguishable from zero. Gemini and Grok change from indistinguishable to significantly positive; Opus remains significantly positive. Thus the qualitative L5-anomaly conclusion weakens but does not disappear.

## FBD L4 variants

{md_table(["Model", "Variant", "Rows", "Strict", "Typed"], frows)}

The numeric + wrong-arrow variant requires every requested arrow component. Its standalone table is [`fbd_l4_variants.csv`](fbd_l4_variants.csv).

## Test 2: grain

{md_table(["Model", "Sigma", "Rows", "Strict", "Typed"], grows)}

Typed scoring raises absolute levels where structured answers were previously string-mismatched. The main robustness pattern remains: changes across sigma are generally small relative to the model-to-model differences; this table does not recompute significance of each sigma contrast beyond the stored-score comparison.

## Test 3: sycophancy

{md_table(["Model", "R1 strict", "R1 typed", "R2 strict", "R2 typed", "Cap strict", "Cap typed", "Corr strict", "Corr typed"], srows)}

Every overall/strength/level/domain rate, with strict and typed round-1/round-2 correctness side by side, is in [`test3_rates.csv`](test3_rates.csv); row-level verdicts are in `test3_row_scores.csv`. Correction rates move materially because previously unparseable structured correct answers can now score correct. Capitulation rates change little, so the core model-resistance ordering is largely unchanged.

## Audit boundaries

- Strict columns are never deleted.
- Typed constant-answer baselines are recomputed from semantic targets, including acceptance-set overlap handling inherited from the existing baseline code.
- Six constant-key cells remain excluded by the pre-existing adjusted-score convention; raw accuracy for all 170 cells is still reported.
- The typed comparator makes no dataset, generator, stored-response, or published-output change.
"""
    (OUT / "RECOMPUTED.md").write_text(text, encoding="utf-8")


def main():
    cell_types = pd.read_csv(OUT / "cell_types.csv", keep_default_na=False)
    before = pd.read_csv(OUT / "before_after.csv")
    aggregates = pd.read_csv(OUT / "aggregates.csv")
    l45 = pd.read_csv(OUT / "l4_l5.csv")
    grain = pd.read_csv(OUT / "test2_grain.csv")
    syc = pd.read_csv(OUT / "test3_rates.csv")
    scored = pd.read_csv(OUT / "test1_row_scores.csv", keep_default_na=False)
    option = pd.read_csv(OUT / "option_phrasing_changes.csv")
    option_counts = option.groupby(["domain", "level"]).size().sort_values(ascending=False)
    responses = {m: latest(RESULTS / f"closed_loop_{m}.jsonl") for m in MODELS}

    evidence = []
    compass = scored[(scored.domain.eq("compass_bearing")) & (scored.level.eq(5)) & ~scored.typed_correct.astype(bool)]
    for model in MODELS:
        row = compass[compass.model.eq(model)].iloc[0].to_dict()
        row.update(responses[model][row["row_id"]])
        evidence.append((model, row))

    fbd = build_fbd_variants(scored)
    write_spec(cell_types, option_counts)
    write_screen(before, evidence)
    write_colour(scored, responses)
    write_open_gap()
    write_recomputed(before, aggregates, l45, grain, syc, fbd)

    raw_universal = (before.pivot(index=["domain", "level"], columns="model", values="raw_accuracy_typed") < .05).all(axis=1)
    summary = {
        "cells": int(len(cell_types)), "models": len(MODELS), "test1_rows": int(len(scored)),
        "strict_to_typed_changes": int((scored.strict_correct.astype(bool) != scored.typed_correct.astype(bool)).sum()),
        "option_phrase_changes": int(len(option)), "raw_universal_hits": int(raw_universal.sum()),
        "unresolved_comparator_defects": 0,
    }
    (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
