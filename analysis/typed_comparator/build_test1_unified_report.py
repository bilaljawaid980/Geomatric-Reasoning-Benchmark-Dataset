"""Reformat existing typed-comparator outputs into the Test-1 unified report.

This script does not score responses. It reads only the frozen before/after and
aggregate tables plus the existing recomputation narrative.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "analysis/typed_comparator"
TEST = ROOT / "tests/test_1_closed_loop"
REPORT = TEST / "UNIFIED_REPORT.md"
STRICT_REPORT = TEST / "UNIFIED_REPORT_strict.md"
LEGACY_REPORT = TEST / "analysis/TEST_1_UNIFIED_REPORT.md"

NAMES = {
    "claude_opus_5": "Claude Opus 5",
    "claude_sonnet_5": "Claude Sonnet 5",
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
    "gpt_5_6_luna": "GPT-5.6 Luna",
    "gpt_5_6_sol": "GPT-5.6 Sol",
    "grok_4_6": "Grok 4.6",
    "inking": "Inkling",
    "muse_glimmer_30b": "Muse Glimmer 30B",
    "perplexity_sonar_pro": "Perplexity Sonar Pro",
}


def pct(value: float) -> str:
    return "—" if pd.isna(value) else f"{100 * value:.2f}%"


def table(headers, rows, aligns=None):
    if aligns is None:
        aligns = ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(aligns) + "|"]
    lines.extend("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def markdown_table_in_section(text: str, heading: str) -> pd.DataFrame:
    start = text.index(heading)
    block = text[start:].split("\n## ", 1)[0]
    lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    header = [x.strip() for x in lines[0].strip("|").split("|")]
    rows = [[x.strip() for x in line.strip("|").split("|")] for line in lines[2:]]
    return pd.DataFrame(rows, columns=header)


def preserve_strict_report():
    if STRICT_REPORT.exists():
        return
    source = REPORT if REPORT.exists() else LEGACY_REPORT
    if not source.exists():
        raise FileNotFoundError("No previous unified Test-1 report found to preserve")
    shutil.copy2(source, STRICT_REPORT)


def main():
    preserve_strict_report()
    before = pd.read_csv(SOURCE / "before_after.csv")
    aggregates = pd.read_csv(SOURCE / "aggregates.csv")
    recomputed_text = (SOURCE / "RECOMPUTED.md").read_text(encoding="utf-8")

    # The duplicate include_small_n=False views are identical here because every
    # evaluated cell has n=50. Use the explicit inclusive view once.
    ag = aggregates[aggregates.include_small_n.astype(str).str.lower().eq("true")].copy()
    overall_macro = ag[(ag.scope.eq("overall")) & ag.method.eq("MACRO")].set_index("model")
    overall_pooled = ag[(ag.scope.eq("overall")) & ag.method.eq("POOLED")].set_index("model")
    order = overall_macro.raw_accuracy_all_cells_typed.sort_values(ascending=False).index.tolist()

    overall_rows = []
    for model in order:
        ma, po = overall_macro.loc[model], overall_pooled.loc[model]
        overall_rows.append((
            NAMES[model],
            f"{int(ma.n_all_cells_typed):,} ({int(ma.n_typed):,} adjusted)",
            pct(ma.raw_accuracy_all_cells_strict), pct(ma.raw_accuracy_all_cells_typed),
            pct(ma.adjusted_score_strict), pct(ma.adjusted_score_typed),
            pct(po.adjusted_score_strict), pct(po.adjusted_score_typed),
        ))

    level = ag[(ag.scope.eq("level")) & ag.method.eq("MACRO")].copy()
    level_bases = (level[["level", "baseline_strict", "baseline_typed"]]
                   .drop_duplicates().sort_values("level"))
    level_baseline_line = "; ".join(
        f"L{int(r.level)} **{pct(r.baseline_typed)}** (strict {pct(r.baseline_strict)})"
        for r in level_bases.itertuples(index=False)
    )
    level_rows = []
    for model in order:
        for r in level[level.model.eq(model)].sort_values("level").itertuples(index=False):
            level_rows.append((NAMES[model], f"L{int(r.level)}", pct(r.raw_accuracy_strict),
                               pct(r.raw_accuracy_typed), pct(r.adjusted_score_strict),
                               pct(r.adjusted_score_typed)))

    family = ag[(ag.scope.eq("family")) & ag.method.eq("MACRO")].copy()
    families = [
        "Plane Geometry", "Solid Geometry", "Transformational",
        "Physical & Mechanical", "Topological", "Projective", "Analytic",
        "Optical", "Inductive",
    ]
    family_bases = family[["family", "baseline_strict", "baseline_typed"]].drop_duplicates()
    family_baseline_line = "; ".join(
        f"{name} **{pct(family_bases[family_bases.family.eq(name)].iloc[0].baseline_typed)}** "
        f"(strict {pct(family_bases[family_bases.family.eq(name)].iloc[0].baseline_strict)})"
        for name in families
    )
    family_rows = []
    for model in order:
        lookup = family[family.model.eq(model)].set_index("family")
        for name in families:
            r = lookup.loc[name]
            family_rows.append((NAMES[model], name, pct(r.adjusted_score_strict),
                                pct(r.adjusted_score_typed)))

    domain = ag[(ag.scope.eq("domain")) & ag.method.eq("MACRO")].copy()
    domains = sorted(domain.domain.dropna().unique())
    domain_rows = []
    for model in order:
        lookup = domain[domain.model.eq(model)].set_index("domain")
        for name in domains:
            r = lookup.loc[name]
            domain_rows.append((NAMES[model], f"`{name}`", pct(r.raw_accuracy_strict),
                                pct(r.raw_accuracy_typed), pct(r.adjusted_score_strict),
                                pct(r.adjusted_score_typed)))

    constants = (before[before.excluded_constant_typed.astype(bool)]
                 [["domain", "level", "modal_ground_truth_strict", "modal_ground_truth_typed",
                   "baseline_strict", "baseline_typed"]]
                 .drop_duplicates().sort_values(["domain", "level"]))
    constant_rows = [
        (f"`{r.domain}`", f"L{int(r.level)}", f"`{r.modal_ground_truth_strict}`",
         f"`{r.modal_ground_truth_typed}`", pct(r.baseline_strict), pct(r.baseline_typed))
        for r in constants.itertuples(index=False)
    ]

    l45 = markdown_table_in_section(recomputed_text, "## L4-to-L5 adjusted difference")
    l45_rows = [tuple(row) for row in l45.itertuples(index=False, name=None)]
    fbd = markdown_table_in_section(recomputed_text, "## FBD L4 variants")
    fbd_rows = [tuple(row) for row in fbd.itertuples(index=False, name=None)]

    methodology = (
        "Ground truth was not changed: the comparator now parses structured keys—ordered lists, "
        "typed dictionaries, and templated sentences—rather than comparing them as raw strings. "
        "Fifteen cells across eight domains were affected; no numeric tolerance was introduced, "
        "and strict scores are retained beside typed scores throughout."
    )

    report = f"""# Test 1: Unified Closed-Loop Result Report — Typed Comparator

## Scope

Ten models were evaluated on the same 8,500-question closed-loop sample: 50 images per domain, 34 domains, and five levels. Typed values are the current counterfactual report values; original strict results remain adjacent for auditability. The previous report is preserved at [UNIFIED_REPORT_strict.md](UNIFIED_REPORT_strict.md).

## Methodology note

{methodology}

## Overall per model

{table(["Model", "n", "Raw strict", "Raw typed", "Adjusted macro strict", "Adjusted macro typed", "Pooled strict", "Pooled typed"], overall_rows)}

Adjusted scores exclude the six structurally constant cells listed below; raw scores use all 8,500 responses.

## By level

Typed level baselines, with strict baselines retained: {level_baseline_line}.

{table(["Model", "Level", "Raw strict", "Raw typed", "Adjusted strict", "Adjusted typed"], level_rows)}

## By reasoning family

Typed family baselines, with strict baselines retained: {family_baseline_line}.

{table(["Model", "Family", "Adjusted strict", "Adjusted typed"], family_rows)}

## By domain

{table(["Model", "Domain", "Raw strict", "Raw typed", "Adjusted strict", "Adjusted typed"], domain_rows)}

## Structurally constant cells

The count remains **{len(constants)}**. These cells have a 100% constant-answer baseline and are excluded from adjusted aggregates under both comparators, while their raw accuracy remains included.

{table(["Domain", "Level", "Strict modal target", "Typed modal target", "Strict baseline", "Typed baseline"], constant_rows)}

## L4-to-L5 separation

The stored intervals use 10,000-resample, domain-stratified image-cluster bootstrapping. **Three models improve significantly, six degrade significantly, and one is indistinguishable from zero.** This separates models by capability; it is not described as an anomaly.

{table(list(l45.columns), l45_rows)}

The significantly improving models are Claude Opus 5, Gemini 3.8 Flash, and Grok 4.6. The significantly degrading models are Claude Sonnet 5, DeepSeek V4.1 Flash, GPT-5.6 Luna, GPT-5.6 Sol, Inkling, and Muse Glimmer 30B. Perplexity Sonar Pro is indistinguishable from zero.

## FBD L4 variants

Where FBD L4 is reported explicitly, its two variants are shown separately rather than as a pooled FBD-specific row. The numeric+wrong-arrow variant requires the requested arrow label, error kind, and exact error amount in addition to its numeric fields. It scores **0.00% for all ten models under both comparators**. The higher-level level/family/domain/overall values above are reproduced unchanged from the supplied aggregate source.

{table(list(fbd.columns), fbd_rows)}

## Open items

- The Optical family is negative for nine of ten models after repair. This is a domain-convention issue in `optical_illusion` and `impossible_object`, not a scoring defect.
- `depth_height` L3 and `shadow_inference` L3/L4 use a colour vocabulary that the prompt never states and the image never labels. No colour aliases were introduced; `pink` and `magenta` remain different answers.
- The six open-weight models cannot be re-scored because their raw responses are unavailable, and their selection is not recorded in this repository. If shown elsewhere, they must be marked as scored under the original comparator and are not comparable to these typed results.

## Audit sources

- [`before_after.csv`](../../analysis/typed_comparator/before_after.csv): every model × cell strict/typed result
- [`aggregates.csv`](../../analysis/typed_comparator/aggregates.csv): level, family, domain, macro, and pooled aggregates
- [`RECOMPUTED.md`](../../analysis/typed_comparator/RECOMPUTED.md): frozen L4-to-L5 bootstrap and FBD-variant tables
"""
    REPORT.write_text(report, encoding="utf-8", newline="\n")
    print(f"Preserved strict report: {STRICT_REPORT}")
    print(f"Wrote typed report: {REPORT}")
    print(f"Rows: overall={len(overall_rows)}, level={len(level_rows)}, family={len(family_rows)}, domain={len(domain_rows)}, constants={len(constants)}, fbd={len(fbd_rows)}")


if __name__ == "__main__":
    main()
