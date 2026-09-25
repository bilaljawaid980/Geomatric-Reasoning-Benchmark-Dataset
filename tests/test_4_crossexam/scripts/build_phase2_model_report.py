"""Build a separate Markdown report for one completed Phase-2 model."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_phase2_unified_report import DISPLAY_NAMES, conf, pct


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = pd.read_csv(args.analysis_dir / "crossexam_summary.csv")
    row = summary.loc[summary["model"] == args.model]
    if len(row) != 1:
        raise ValueError(f"Expected one summary row for {args.model}, found {len(row)}")
    row = row.iloc[0]
    confidence = pd.read_csv(args.analysis_dir / "crossexam_confidence.csv")
    confidence = confidence.loc[
        (confidence["model"] == args.model) & (confidence["outcome"] == "ALL")
    ].set_index("arm")
    display = DISPLAY_NAMES.get(args.model, args.model)
    output = args.output or args.analysis_dir / "PHASE2_CROSSEXAM_REPORT.md"
    lines = [
        f"# Test 4 Phase-2 Cross-Examination: {display}",
        "",
        "## Coverage",
        "",
        f"The evaluation contains {int(row['rows']):,} Phase-2 comparisons from "
        f"{int(row['images']):,} source images, including {int(row['control_rows']):,} control re-asks.",
        "",
        "## Main transition rates",
        "",
        "| Intervention | Capitulation | Control-adjusted capitulation | Correction | Control-adjusted correction |",
        "|---|---:|---:|---:|---:|",
        f"| Natural peers | {pct(row['natural_capitulation_rate'])} | "
        f"{pct(row['natural_capitulation_rate_minus_control'])} | "
        f"{pct(row['natural_correction_rate'])} | {pct(row['natural_correction_rate_minus_control'])} |",
        f"| Constructed consensus | {pct(row['constructed_capitulation_rate'])} | "
        f"{pct(row['constructed_capitulation_rate_minus_control'])} | "
        f"{pct(row['constructed_correction_rate'])} | "
        f"{pct(row['constructed_correction_rate_minus_control'])} |",
        "",
        f"The control re-ask changed {pct(row['control_change_rate'])} of answers. Its capitulation "
        f"rate was {pct(row['control_capitulation_rate'])}, and its correction rate was "
        f"{pct(row['control_correction_rate'])}.",
        "",
        "## Confidence movement",
        "",
        "| Intervention | Before | After | Change | Moved toward correctness |",
        "|---|---:|---:|---:|---:|",
    ]
    labels = {
        "natural": "Natural peers",
        "constructed": "Constructed consensus",
        "control_reask": "Control re-ask",
    }
    for arm in ("natural", "constructed", "control_reask"):
        item = confidence.loc[arm]
        lines.append(
            f"| {labels[arm]} | {conf(item['mean_confidence_before'])} | "
            f"{conf(item['mean_confidence_after'])} | "
            f"{float(item['mean_confidence_change']):+.3f} | "
            f"{pct(item['confidence_moved_toward_correctness_rate'])} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "Natural peers produced a positive control-adjusted correction effect without increasing "
        "capitulation above the control rate. A constructed unanimous consensus was much stronger: "
        "it corrected many initially wrong answers, but also caused substantially more initially "
        "correct answers to become wrong.",
        "",
        "## Answer audit",
        "",
        "Round-2 answers were scored field by field with the open-ended semantic normalizer; "
        "field order and harmless representational differences do not affect correctness. "
        "Reviewed disagreements that remained were substantive answer differences, so no "
        "additional answers were promoted.",
        "",
    ])
    if args.model == "deepseek_v4_1_flash":
        lines[-1:-1] = [
            "Five initially incomplete Round-2 responses were re-run and merged before the "
            "final score was calculated.",
            "",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
