"""Build separate and unified Markdown reports for grain robustness."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


TEST_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = TEST_ROOT / "analysis"
DISPLAY = {
    "gemini_3_8_flash": "Gemini 3.8 Flash", "claude_opus_5": "Claude Opus 5",
    "grok_4_6": "Grok 4.6", "gpt_5_6_sol": "GPT-5.6 Sol",
    "claude_sonnet_5": "Claude Sonnet 5", "muse_glimmer_30b": "Muse Glimmer 30B",
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash", "gpt_5_6_luna": "GPT-5.6 Luna",
    "perplexity_sonar_pro": "Perplexity Sonar Pro", "inking": "Inkling",
}


def source(model: str, name: str) -> pd.DataFrame:
    individual = ANALYSIS / model / f"{name}.csv"
    path = individual if individual.is_file() else ANALYSIS / f"{name}.csv"
    frame = pd.read_csv(path)
    return frame.loc[frame["model"] == model].copy()


def pct(value: object) -> str:
    return f"{100 * float(value):.2f}%"


def points(value: object) -> str:
    return f"{100 * float(value):+.2f}"


def model_report(model: str) -> str:
    sigma = source(model, "per_sigma").sort_values("sigma")
    curve = source(model, "degradation_curve").sort_values("sigma")
    breaks = source(model, "domain_break_summary")
    first = source(model, "first_significant_drop").iloc[0]["first_significant_drop_sigma"]
    first_text = "None" if pd.isna(first) or str(first) == "None" else str(int(float(first)))
    lines = [
        f"# Test 2 Grain Robustness: {DISPLAY[model]}", "", "## Design", "",
        "The same 680 core images and 3,400 image-question pairs were evaluated at sigma 0, 15, 25, and 40. Sigma 0 reuses the clean response; every positive sigma uses a fixed monochrome-noise rendering of the same image.", "",
        "## Accuracy by grain level", "", "| Sigma | Rows | Accuracy | Bootstrap 95% CI | Change from clean |", "|---:|---:|---:|---:|---:|",
    ]
    changes = {int(row.sigma): row for row in curve.itertuples(index=False)}
    for row in sigma.itertuples(index=False):
        change = "baseline" if int(row.sigma) == 0 else f"{points(changes[int(row.sigma)].accuracy_change)} points"
        lines.append(
            f"| {int(row.sigma)} | {int(row.absolute_rows):,} | **{pct(row.absolute_accuracy)}** | "
            f"{pct(row.absolute_accuracy_ci_low)}-{pct(row.absolute_accuracy_ci_high)} | {change} |"
        )
    lines.extend(["", f"First significant suite-level drop: **{first_text}**.", "", "## Domain breakpoint distribution", "", "| Breakpoint | Domains |", "|---|---:|"])
    for row in breaks.itertuples(index=False):
        lines.append(f"| {row.break_bucket} | {int(row.domains)} |")
    lines.extend([
        "", "## Scoring audit", "",
        "The noisy-image answers use the same strict parser and exact comparison as Test 1. Review of the wrong-answer forms found no additional meaning-preserving equivalences beyond the approved Test 1 normalization rules.", "",
    ])
    return "\n".join(lines)


def main() -> None:
    records = []
    for model in DISPLAY:
        sigma = source(model, "per_sigma").sort_values("sigma")
        curve = source(model, "degradation_curve").sort_values("sigma")
        first = source(model, "first_significant_drop").iloc[0]["first_significant_drop_sigma"]
        accuracy = {int(row.sigma): row.absolute_accuracy for row in sigma.itertuples(index=False)}
        change40 = float(curve.loc[curve["sigma"] == 40, "accuracy_change"].iloc[0])
        records.append((model, accuracy, change40, first))
        output = ANALYSIS / "models" / model / "GRAIN_ROBUSTNESS_REPORT.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(model_report(model), encoding="utf-8")
    records.sort(key=lambda item: item[1][0], reverse=True)
    lines = [
        "# Test 2: Unified Grain-Robustness Report", "",
        "The matched-image construction, exact grain-generation procedure, readability",
        "gate, scoring policy, and statistical analysis are documented in",
        "[Test 2 methodology](../METHODOLOGY.md).", "", "## Test design", "",
        "Ten models were evaluated on 680 matched images and 3,400 questions per condition at sigma 0, 15, 25, and 40. Positive-sigma images use fixed reproducible monochrome grain, making every comparison within-image.", "",
        "## Main result", "", "| Rank | Model | Sigma 0 | Sigma 15 | Sigma 25 | Sigma 40 | Sigma 40 change | First significant drop |", "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, (model, accuracy, change40, first) in enumerate(records, 1):
        first_text = "None" if pd.isna(first) or str(first) == "None" else str(int(float(first)))
        lines.append(
            f"| {rank} | {DISPLAY[model]} | {pct(accuracy[0])} | {pct(accuracy[15])} | "
            f"{pct(accuracy[25])} | {pct(accuracy[40])} | {points(change40)} points | {first_text} |"
        )
    lines.extend(["", "Separate per-model reports are stored under `analysis/models/<model>/GRAIN_ROBUSTNESS_REPORT.md`.", ""])
    (ANALYSIS / "TEST_2_UNIFIED_GRAIN_ROBUSTNESS_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(DISPLAY)} separate reports and {ANALYSIS / 'TEST_2_UNIFIED_GRAIN_ROBUSTNESS_REPORT.md'}")


if __name__ == "__main__":
    main()
