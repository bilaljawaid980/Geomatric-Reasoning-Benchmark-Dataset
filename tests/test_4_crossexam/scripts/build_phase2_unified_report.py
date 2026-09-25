"""Build a unified Markdown report from completed Test 4 Phase-2 analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


TEST_ROOT = Path(__file__).resolve().parents[1]
DISPLAY_NAMES = {
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash",
    "gpt_5_6_sol": "GPT-5.6 Sol",
    "gpt_5_6_luna": "GPT-5.6 Luna",
    "claude_opus_5": "Claude Opus 5",
    "claude_sonnet_5": "Claude Sonnet 5",
    "gemini_3_8_flash": "Gemini 3.8 Flash",
    "grok_4_6": "Grok 4.6",
    "inking": "Inkling",
    "muse_glimmer_30b": "Muse Glimmer 30B",
    "perplexity_sonar_pro": "Perplexity Sonar Pro",
}


def pct(value: object) -> str:
    return "n/a" if pd.isna(value) else f"{100 * float(value):.2f}%"


def conf(value: object) -> str:
    return "n/a" if pd.isna(value) else f"{float(value):.3f}"


def interval(row: pd.Series, prefix: str) -> str:
    return f"{pct(row[prefix + '_ci_low'])}-{pct(row[prefix + '_ci_high'])}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=TEST_ROOT / "analysis")
    parser.add_argument(
        "--output",
        type=Path,
        default=TEST_ROOT / "analysis/UNIFIED_PHASE2_CROSSEXAM_REPORT.md",
    )
    args = parser.parse_args()

    summary_frames = [pd.read_csv(args.analysis_dir / "crossexam_summary.csv")]
    confidence_frames = [pd.read_csv(args.analysis_dir / "crossexam_confidence.csv")]
    for child in args.analysis_dir.iterdir():
        if not child.is_dir():
            continue
        summary_path = child / "crossexam_summary.csv"
        confidence_path = child / "crossexam_confidence.csv"
        if summary_path.is_file() and confidence_path.is_file():
            summary_frames.append(pd.read_csv(summary_path))
            confidence_frames.append(pd.read_csv(confidence_path))
    summary = pd.concat(summary_frames, ignore_index=True).drop_duplicates("model", keep="last")
    confidence = pd.concat(confidence_frames, ignore_index=True).drop_duplicates(
        ["model", "arm", "outcome"], keep="last"
    )
    missing = set(DISPLAY_NAMES) - set(summary["model"])
    if missing:
        raise ValueError(f"Missing models from Phase-2 summary: {sorted(missing)}")
    summary = summary.assign(display_name=summary["model"].map(DISPLAY_NAMES)).sort_values("display_name")
    all_confidence = confidence.loc[confidence["outcome"] == "ALL"].copy()

    lines = [
        "# Test 4: Open-Ended Cross-Examination — Unified Phase-2 Report",
        "",
        "## Design",
        "",
        "Phase 2 replays each model's exact Round-1 response before showing one of three interventions: "
        "natural responses from three other models, a constructed unanimous consensus, or a control "
        "re-ask with no peer answer. Correction is a wrong-to-right transition; capitulation is a "
        "right-to-wrong transition. The primary effects below subtract the matching control transition "
        "rate, separating peer influence from ordinary second-turn instability.",
        "",
        "The exact Phase-1 response format, peer displays, constructed-consensus rule, control "
        "prompt, and Phase-2 response instruction are documented in "
        "[Test 4 methodology](../METHODOLOGY.md).",
        "",
        "## Sample coverage",
        "",
        "| Model | Phase-2 rows | Source images | Control rows |",
        "|---|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['display_name']} | {int(row['rows']):,} | {int(row['images']):,} | "
            f"{int(row['control_rows']):,} |"
        )

    lines.extend([
        "",
        "## Natural-peer effects",
        "",
        "| Model | Capitulation | Control-adjusted capitulation (95% CI) | Correction | Control-adjusted correction (95% CI) |",
        "|---|---:|---:|---:|---:|",
    ])
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['display_name']} | {pct(row['natural_capitulation_rate'])} | "
            f"{pct(row['natural_capitulation_rate_minus_control'])} "
            f"({interval(row, 'natural_capitulation_rate_minus_control')}) | "
            f"{pct(row['natural_correction_rate'])} | "
            f"{pct(row['natural_correction_rate_minus_control'])} "
            f"({interval(row, 'natural_correction_rate_minus_control')}) |"
        )

    lines.extend([
        "",
        "## Constructed-consensus effects",
        "",
        "| Model | Capitulation | Control-adjusted capitulation (95% CI) | Correction | Control-adjusted correction (95% CI) |",
        "|---|---:|---:|---:|---:|",
    ])
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['display_name']} | {pct(row['constructed_capitulation_rate'])} | "
            f"{pct(row['constructed_capitulation_rate_minus_control'])} "
            f"({interval(row, 'constructed_capitulation_rate_minus_control')}) | "
            f"{pct(row['constructed_correction_rate'])} | "
            f"{pct(row['constructed_correction_rate_minus_control'])} "
            f"({interval(row, 'constructed_correction_rate_minus_control')}) |"
        )

    lines.extend([
        "",
        "## Control instability",
        "",
        "| Model | Any answer change | Capitulation | Correction |",
        "|---|---:|---:|---:|",
    ])
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['display_name']} | {pct(row['control_change_rate'])} | "
            f"{pct(row['control_capitulation_rate'])} | {pct(row['control_correction_rate'])} |"
        )

    lines.extend([
        "",
        "## Confidence movement",
        "",
        "Values are mean reported confidence before and after the second turn. Coverage counts are "
        "intentionally omitted.",
        "",
        "| Model | Arm | Before | After | Change | Moved toward correctness |",
        "|---|---|---:|---:|---:|---:|",
    ])
    arm_order = {"natural": 0, "constructed": 1, "control_reask": 2}
    all_confidence = all_confidence.assign(
        display_name=all_confidence["model"].map(DISPLAY_NAMES),
        arm_order=all_confidence["arm"].map(arm_order),
    ).sort_values(["display_name", "arm_order"])
    arm_names = {
        "natural": "Natural peers",
        "constructed": "Constructed consensus",
        "control_reask": "Control re-ask",
    }
    for _, row in all_confidence.iterrows():
        lines.append(
            f"| {row['display_name']} | {arm_names[row['arm']]} | "
            f"{conf(row['mean_confidence_before'])} | {conf(row['mean_confidence_after'])} | "
            f"{float(row['mean_confidence_change']):+.3f} | "
            f"{pct(row['confidence_moved_toward_correctness_rate'])} |"
        )

    lines.extend([
        "",
        "## Main findings",
        "",
        "- Constructed unanimous consensus produced much larger answer movement than natural peers for every model.",
        "- Natural peers improved wrong answers more often than they damaged correct answers for every model after control adjustment.",
        "- GPT-5.6 Luna had the largest natural-peer correction effect, but also the largest natural-peer capitulation effect.",
        "- Gemini 3.8 Flash and Grok 4.6 were the most resistant to a constructed false consensus, while Claude Sonnet 5 and GPT-5.6 Luna were the most susceptible.",
        "- Control re-asks caused non-trivial instability for several models, demonstrating why the control-adjusted effects are the primary comparison.",
        "",
        "## Answer audit",
        "",
        "Open-ended answers were compared field by field after semantic normalization; field order "
        "and harmless representational differences do not change correctness. Reviewed remaining "
        "disagreements were substantive. Five incomplete DeepSeek V4.1 Flash responses were re-run "
        "and merged before final scoring.",
        "",
        "Detailed outcome, family, confidence, and silent-capitulation tables remain available in the companion CSV files in this directory.",
        "",
    ])
    # Replace the legacy mojibake title retained in older generated reports.
    lines[0] = "# Test 4: Open-Ended Cross-Examination - Unified Phase-2 Report"
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote unified Phase-2 report to {args.output}")


if __name__ == "__main__":
    main()
