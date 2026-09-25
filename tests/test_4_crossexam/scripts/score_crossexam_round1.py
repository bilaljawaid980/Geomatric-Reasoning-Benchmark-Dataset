"""Score Test 4 Round-1 open-ended responses, one model per invocation."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

TEST_ROOT = Path(__file__).resolve().parents[1]

from crossexam_common import (
    FAMILIES,
    answer_is_accepted,
    load_jsonl_latest,
    read_csv,
    response_parts,
)

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


def stable_seed(*parts: object) -> int:
    payload = "\x1f".join(map(str, parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def bootstrap_accuracy(
    values: np.ndarray, resamples: int, random_seed: int
) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return np.nan, np.nan, np.nan
    estimate = float(values.mean())
    rng = np.random.default_rng(random_seed)
    samples: list[np.ndarray] = []
    for start in range(0, resamples, 512):
        batch = min(512, resamples - start)
        picks = rng.integers(0, values.size, size=(batch, values.size))
        samples.append(values[picks].mean(axis=1))
    low, high = np.quantile(np.concatenate(samples), [0.025, 0.975])
    return estimate, float(low), float(high)


def expected_calibration_error(frame: pd.DataFrame, bins: int = 10) -> float:
    paired = frame.dropna(subset=["confidence"])
    if paired.empty:
        return np.nan
    confidence = paired["confidence"].to_numpy(float)
    correct = paired["correct"].to_numpy(float)
    bucket = np.minimum((confidence * bins).astype(int), bins - 1)
    result = 0.0
    for index in range(bins):
        selected = bucket == index
        if selected.any():
            result += selected.mean() * abs(confidence[selected].mean() - correct[selected].mean())
    return float(result)


def summarize(
    frame: pd.DataFrame, model: str, label: str, resamples: int
) -> dict[str, Any]:
    accuracy, low, high = bootstrap_accuracy(
        frame["correct"].to_numpy(bool),
        resamples,
        stable_seed(model, label, "round1_accuracy"),
    )
    paired = frame.dropna(subset=["confidence"])
    correct_confidence = paired.loc[paired["correct"], "confidence"]
    incorrect_confidence = paired.loc[~paired["correct"], "confidence"]
    brier = (
        float(np.mean((paired["confidence"].to_numpy(float) - paired["correct"].to_numpy(float)) ** 2))
        if len(paired)
        else np.nan
    )
    return {
        "model": model,
        "rows": len(frame),
        "correct": int(frame["correct"].sum()),
        "accuracy": accuracy,
        "accuracy_ci_low": low,
        "accuracy_ci_high": high,
        "confidence_rows": len(paired),
        "mean_confidence": paired["confidence"].mean(),
        "mean_confidence_correct": correct_confidence.mean(),
        "mean_confidence_incorrect": incorrect_confidence.mean(),
        "brier_score": brier,
        "ece_10_bins": expected_calibration_error(frame),
    }


def percent(value: Any) -> str:
    return "n/a" if pd.isna(value) else f"{100 * float(value):.2f}%"


def decimal(value: Any) -> str:
    return "n/a" if pd.isna(value) else f"{float(value):.3f}"


def markdown_report(
    model: str,
    overall: pd.DataFrame,
    by_family: pd.DataFrame,
    by_domain: pd.DataFrame,
) -> str:
    display = DISPLAY_NAMES.get(model, model)
    row = overall.iloc[0]
    lines = [
        f"# Test 4 Phase-1 Open-Ended Accuracy: {display}",
        "",
        "## Evaluation",
        "",
        "Round 1 measures independent open-ended visual reasoning before any peer responses are shown. "
        "Every sampled image remains in the denominator, and an answer is correct only when its complete "
        "set of required claims matches an accepted answer. Harmless representational differences in "
        "times, landmark pairs, ordered or set-like lists, coordinates, JSON, and established wording "
        "variants are normalised; numerical values are still compared exactly with no tolerance. Order is "
        "ignored for fields, pairs, sets, JSON keys, connectivity labels, and tied labels, but preserved "
        "for genuine sequences such as depth order, shortest-to-tallest order, and ranking levels.",
        "",
        "## Overall result",
        "",
        "| Samples | Correct | Accuracy | Bootstrap 95% CI | Mean confidence | Brier score | ECE (10 bins) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {int(row['rows']):,} | {int(row['correct']):,} | {percent(row['accuracy'])} | "
        f"{percent(row['accuracy_ci_low'])}–{percent(row['accuracy_ci_high'])} | "
        f"{decimal(row['mean_confidence'])} | {decimal(row['brier_score'])} | {decimal(row['ece_10_bins'])} |",
        "",
        "## Confidence by correctness",
        "",
        "| Mean when correct | Mean when incorrect |",
        "|---:|---:|",
        f"| {decimal(row['mean_confidence_correct'])} | {decimal(row['mean_confidence_incorrect'])} |",
        "",
        "## Accuracy by reasoning family",
        "",
        "| Family | Samples | Correct | Accuracy | Bootstrap 95% CI |",
        "|---|---:|---:|---:|---:|",
    ]
    for family_row in by_family.sort_values("family").itertuples(index=False):
        lines.append(
            f"| {family_row.family} | {family_row.rows:,} | {family_row.correct:,} | "
            f"{percent(family_row.accuracy)} | {percent(family_row.accuracy_ci_low)}–"
            f"{percent(family_row.accuracy_ci_high)} |"
        )
    lines.extend([
        "",
        "## Accuracy by domain",
        "",
        "| Domain | Samples | Correct | Accuracy | Bootstrap 95% CI |",
        "|---|---:|---:|---:|---:|",
    ])
    for domain_row in by_domain.sort_values("domain").itertuples(index=False):
        lines.append(
            f"| `{domain_row.domain}` | {domain_row.rows:,} | {domain_row.correct:,} | "
            f"{percent(domain_row.accuracy)} | {percent(domain_row.accuracy_ci_low)}–"
            f"{percent(domain_row.accuracy_ci_high)} |"
        )
    lines.extend([
        "",
        "## Role in the cross-examination test",
        "",
        "This score is the pre-intervention baseline. Phase 2 will replay each stored Round-1 response "
        "verbatim, expose the model to natural peers, a controlled peer consensus, or a control re-ask, "
        "and measure corrections, capitulations, ordinary instability, and confidence movement.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=TEST_ROOT / "plan/crossexam_manifest.csv",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=TEST_ROOT / "results",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=TEST_ROOT / "analysis/phase1",
    )
    parser.add_argument("--bootstrap-resamples", type=int, default=10000)
    args = parser.parse_args()
    if args.bootstrap_resamples < 1:
        parser.error("--bootstrap-resamples must be positive")

    manifest = read_csv(args.manifest)
    expected = manifest.loc[manifest["model"] == args.model].copy()
    if expected.empty:
        raise ValueError(f"No Round-1 manifest rows for {args.model}")
    if expected["row_id"].duplicated().any():
        raise ValueError(f"Duplicate manifest row IDs for {args.model}")

    result_path = args.results_dir / f"crossexam_r1_{args.model}.jsonl"
    records = load_jsonl_latest(result_path, args.model)
    expected_ids = set(expected["row_id"])
    successful_ids = {
        row_id
        for row_id, record in records.items()
        if not record.get("error")
        and str(record.get("response_raw", "")).strip()
        and str(record.get("response_raw", "")).strip().casefold() not in {"none", "null"}
    }
    missing = expected_ids - successful_ids
    extra = set(records) - expected_ids
    if missing or extra:
        raise ValueError(
            f"Round 1 is not complete for {args.model}: "
            f"successful={len(successful_ids & expected_ids):,}/{len(expected_ids):,}, "
            f"missing={len(missing):,}, extra={len(extra):,}"
        )

    scored_rows: list[dict[str, Any]] = []
    for row in expected.to_dict("records"):
        result = records[row["row_id"]]
        parts = response_parts(str(result["response_raw"]))
        correct = answer_is_accepted(parts["answer"], row["acceptance_set"])
        scored_rows.append({
            "row_id": row["row_id"],
            "model": args.model,
            "domain": row["domain"],
            "family": FAMILIES[row["domain"]],
            "stem": row["stem"],
            "question_id": row["question_id"],
            "ground_truth": row["ground_truth"],
            "answer": parts["answer"] or "",
            "correct": bool(correct),
            "confidence": parts["confidence"],
        })
    scored = pd.DataFrame(scored_rows)

    overall = pd.DataFrame([
        summarize(scored, args.model, "overall", args.bootstrap_resamples)
    ])
    family_rows: list[dict[str, Any]] = []
    for family, group in scored.groupby("family", sort=True):
        family_rows.append({
            "family": family,
            **summarize(group, args.model, f"family:{family}", args.bootstrap_resamples),
        })
    domain_rows: list[dict[str, Any]] = []
    for domain, group in scored.groupby("domain", sort=True):
        domain_rows.append({
            "domain": domain,
            **summarize(group, args.model, f"domain:{domain}", args.bootstrap_resamples),
        })
    by_family = pd.DataFrame(family_rows)
    by_domain = pd.DataFrame(domain_rows)

    output_dir = args.output_root / args.model
    output_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_dir / "round1_scored.csv", index=False)
    overall.to_csv(output_dir / "round1_summary.csv", index=False)
    by_family.to_csv(output_dir / "round1_by_family.csv", index=False)
    by_domain.to_csv(output_dir / "round1_by_domain.csv", index=False)
    report_path = output_dir / "ROUND1_OPEN_ENDED_REPORT.md"
    report_path.write_text(
        markdown_report(args.model, overall, by_family, by_domain),
        encoding="utf-8",
    )

    summary = overall.iloc[0]
    print(f"Model: {DISPLAY_NAMES.get(args.model, args.model)}")
    print(f"Samples: {int(summary['rows']):,}")
    print(f"Correct: {int(summary['correct']):,}")
    print(
        f"Strict open-ended accuracy: {percent(summary['accuracy'])} "
        f"(95% CI {percent(summary['accuracy_ci_low'])}-{percent(summary['accuracy_ci_high'])})"
    )
    print(f"Mean confidence: {decimal(summary['mean_confidence'])}")
    print(f"Wrote separate analysis to {output_dir}")


if __name__ == "__main__":
    main()
