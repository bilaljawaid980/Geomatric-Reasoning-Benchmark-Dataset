"""Build the unified Test 4 Phase-1 accuracy and confidence report."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from score_crossexam_round1 import DISPLAY_NAMES, decimal, percent


TEST_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-root",
        type=Path,
        default=TEST_ROOT / "analysis/phase1",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=TEST_ROOT / "analysis/phase1/UNIFIED_ROUND1_REPORT.md",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=TEST_ROOT / "analysis/phase1/unified_round1_summary.csv",
    )
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    for model, display_name in DISPLAY_NAMES.items():
        path = args.analysis_root / model / "round1_summary.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing Phase-1 summary for {model}: {path}")
        frame = pd.read_csv(path)
        if len(frame) != 1:
            raise ValueError(f"Expected one summary row in {path}, found {len(frame)}")
        record = frame.iloc[0].to_dict()
        record["display_name"] = display_name
        records.append(record)

    summary = pd.DataFrame(records).sort_values(
        ["accuracy", "display_name"], ascending=[False, True]
    ).reset_index(drop=True)
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.csv_output, index=False)

    lines = [
        "# Test 4 Phase-1 Unified Open-Ended Results",
        "",
        "## Evaluation",
        "",
        "Each model answered the same 2,000-image stratified sample before seeing any peer response. "
        "Accuracy requires the complete open-ended answer to match the stored ground truth. Numeric "
        "values are exact; harmless semantic and representational variants are normalised. Confidence "
        "is the model's reported value on a 0-1 scale.",
        "",
        "The exact Phase-1 prompt format and all Phase-2 intervention prompts are documented in "
        "[Test 4 methodology](../../METHODOLOGY.md).",
        "",
        "## Accuracy and confidence",
        "",
        "| Rank | Model | Samples | Correct | Accuracy | Bootstrap 95% CI | Mean confidence | Confidence when correct | Confidence when incorrect | Brier score | ECE (10 bins) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(summary.itertuples(index=False), 1):
        lines.append(
            f"| {rank} | {row.display_name} | {int(row.rows):,} | {int(row.correct):,} | "
            f"{percent(row.accuracy)} | {percent(row.accuracy_ci_low)}-{percent(row.accuracy_ci_high)} | "
            f"{decimal(row.mean_confidence)} | {decimal(row.mean_confidence_correct)} | "
            f"{decimal(row.mean_confidence_incorrect)} | {decimal(row.brier_score)} | "
            f"{decimal(row.ece_10_bins)} |"
        )

    lines.extend([
        "",
        "## Reading the confidence columns",
        "",
        "Mean confidence describes how certain a model said it was overall. The two conditional "
        "columns separate confidence on correct and incorrect answers; a high incorrect-answer "
        "confidence indicates overconfidence. Lower Brier score and lower expected calibration error "
        "indicate better calibration.",
        "",
        "## Phase-2 role",
        "",
        "These Phase-1 results are the fixed pre-intervention baseline. Phase 2 replays each model's "
        "stored answer verbatim and then presents natural peer responses, a constructed consensus, or "
        "a control re-ask. The analysis measures answer correction, capitulation, ordinary instability, "
        "and confidence movement.",
        "",
    ])
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote unified report for {len(summary)} models to {args.output}")
    print(f"Wrote unified CSV to {args.csv_output}")


if __name__ == "__main__":
    main()
