"""Parse and score stored closed-loop responses without issuing model queries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grip_eval.config import MODELS
from grip_eval.manifest import load_manifest, select_models
from grip_eval.metrics import bootstrap_metric, metric_dict
from grip_eval.parsing import compare_answer, parse_answer


def stable_seed(*parts: object) -> int:
    """Return a stable bootstrap seed for one output cell."""

    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def load_results(path: Path, model_key: str) -> pd.DataFrame:
    """Load append-only JSONL, retaining the last occurrence of each row ID."""

    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {error}") from error
            row_id = str(record.get("row_id", ""))
            if not row_id:
                raise ValueError(f"Missing row_id in {path}:{line_number}")
            if record.get("model") not in (None, model_key):
                raise ValueError(f"Wrong model key in {path}:{line_number}")
            record["model"] = model_key
            records[row_id] = record
    return pd.DataFrame(records.values())


def serialized_value(value: Any) -> str:
    """Serialize parsed structured values without losing their shape."""

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "" if value is None else str(value)


def parse_and_compare(frame: pd.DataFrame) -> pd.DataFrame:
    """Parse every raw response and compute absolute correctness."""

    parsed_values: list[str] = []
    parse_ok: list[bool] = []
    parse_errors: list[str] = []
    absolute: list[bool] = []
    for row in frame.to_dict("records"):
        error_value = row.get("error")
        has_request_error = (
            error_value is not None
            and not pd.isna(error_value)
            and bool(str(error_value).strip())
        )
        if has_request_error:
            parsed = None
            ok = False
            error = f"request error: {error_value}"
            correct = False
        else:
            parsed = parse_answer(
                str(row.get("response_raw", "")),
                str(row["answer_format"]),
                str(row["ground_truth"]),
                str(row["tolerance"]),
                str(row["prompt"]),
            )
            ok = parsed.parse_ok
            error = parsed.error or ""
            correct = compare_answer(
                parsed,
                str(row["ground_truth"]),
                str(row["answer_format"]),
                str(row["tolerance"]),
            )
        parsed_values.append(serialized_value(parsed.value) if parsed else "")
        parse_ok.append(ok)
        parse_errors.append(error)
        absolute.append(correct)
    result = frame.copy()
    result["parsed_answer"] = parsed_values
    result["parse_ok"] = parse_ok
    result["parse_error"] = parse_errors
    result["absolute_correct"] = absolute
    return result


def add_chain_conditional(frame: pd.DataFrame) -> pd.DataFrame:
    """Add chain-gated conditional correctness on complete reusable core items.

    L1 is eligible on every core image. Each later level is evaluated only when
    the immediately preceding level remained correct and parseable. This keeps
    one lower-level error from being counted repeatedly down the same chain.
    Non-core rows are not assigned a conditional score because their levels were
    sampled independently.
    """

    result = frame.copy()
    result["conditional_eligible"] = False
    result["conditional_correct"] = pd.array([pd.NA] * len(result), dtype="boolean")
    grouped = result.loc[result["in_core_subset"]].groupby(
        ["model", "domain", "stem"], sort=False
    )
    for _, group in grouped:
        ordered = group.sort_values("level")
        previous_level = 0
        chain_alive = True
        for index, row in ordered.iterrows():
            level = int(row["level"])
            if level != previous_level + 1:
                chain_alive = False
            eligible = chain_alive
            result.at[index, "conditional_eligible"] = eligible
            if eligible:
                correct = bool(row["absolute_correct"])
                result.at[index, "conditional_correct"] = correct
                chain_alive = correct and bool(row["parse_ok"])
            previous_level = level
    return result


def summarize_group(
    frame: pd.DataFrame,
    *,
    resamples: int,
    seed_parts: tuple[object, ...],
) -> dict[str, object]:
    """Produce absolute and conditional bootstrap metrics for one slice."""

    absolute = bootstrap_metric(
        frame,
        "absolute_correct",
        resamples=resamples,
        seed=stable_seed(*seed_parts, "absolute"),
    )
    row = metric_dict("absolute", absolute)
    conditional_frame = frame.loc[frame["conditional_eligible"]].copy()
    if conditional_frame.empty:
        row.update(
            {
                "conditional_rows": 0,
                "conditional_items": 0,
                "conditional_accuracy": None,
                "conditional_baseline": None,
                "conditional_above_baseline": None,
                "conditional_accuracy_ci_low": None,
                "conditional_accuracy_ci_high": None,
                "conditional_above_baseline_ci_low": None,
                "conditional_above_baseline_ci_high": None,
                "conditional_no_signal": None,
                "conditional_minus_absolute_accuracy": None,
            }
        )
        return row
    conditional_frame["conditional_correct_bool"] = conditional_frame[
        "conditional_correct"
    ].astype(bool)
    conditional = bootstrap_metric(
        conditional_frame,
        "conditional_correct_bool",
        resamples=resamples,
        seed=stable_seed(*seed_parts, "conditional"),
    )
    row.update(metric_dict("conditional", conditional))
    row["conditional_minus_absolute_accuracy"] = conditional.accuracy - absolute.accuracy
    return row


def grouped_summary(
    frame: pd.DataFrame,
    group_columns: list[str],
    *,
    resamples: int,
) -> pd.DataFrame:
    """Summarize absolute and conditional scores for arbitrary grouping columns."""

    rows: list[dict[str, object]] = []
    grouper: str | list[str] = group_columns[0] if len(group_columns) == 1 else group_columns
    for keys, group in frame.groupby(grouper, sort=True):
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        prefix = dict(zip(group_columns, key_tuple))
        rows.append(
            {
                **prefix,
                **summarize_group(
                    group,
                    resamples=resamples,
                    seed_parts=tuple(prefix.values()),
                ),
            }
        )
    return pd.DataFrame(rows)


def build_summary(frame: pd.DataFrame, per_level: pd.DataFrame, resamples: int) -> pd.DataFrame:
    """Build one overall row per model and locate its first non-positive level."""

    overall = grouped_summary(frame, ["model"], resamples=resamples)
    first_levels: dict[str, int | None] = {}
    for model, group in per_level.groupby("model"):
        informative = group.loc[~group["absolute_no_signal"].astype(bool)].sort_values("level")
        failed = informative.loc[informative["absolute_above_baseline"] <= 0]
        first_levels[model] = int(failed.iloc[0]["level"]) if not failed.empty else None
    overall["first_level_above_baseline_at_or_below_zero"] = overall["model"].map(first_levels)
    return overall


def score(args: argparse.Namespace) -> None:
    """Join results to the manifest, score them, and write all analysis tables."""

    manifest = load_manifest(args.manifest)
    model_keys = select_models(args.models, list(MODELS))
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for model_key in model_keys:
        path = args.results_dir / f"closed_loop_{model_key}.jsonl"
        if not path.is_file():
            missing.append(model_key)
            continue
        results = load_results(path, model_key)
        joined = results.merge(
            manifest,
            on="row_id",
            how="left",
            validate="one_to_one",
            suffixes=("_response", ""),
        )
        if joined["question_id"].isna().any():
            unknown = joined.loc[joined["question_id"].isna(), "row_id"].head().tolist()
            raise ValueError(f"Result row IDs absent from manifest: {unknown}")
        frames.append(joined)
    if args.models and missing:
        raise FileNotFoundError(f"No result file for explicitly selected models: {missing}")
    if not frames:
        raise FileNotFoundError(f"No closed-loop result files found in {args.results_dir}")

    all_results = pd.concat(frames, ignore_index=True)
    scored = add_chain_conditional(parse_and_compare(all_results))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(args.output_dir / "per_question.csv", index=False)

    per_level = grouped_summary(scored, ["model", "level"], resamples=args.bootstrap)
    per_domain = grouped_summary(scored, ["model", "domain"], resamples=args.bootstrap)
    summary = build_summary(scored, per_level, args.bootstrap)
    answer_format_counts = (
        scored.assign(answer_format=scored["answer_format"].fillna("").astype(str))
        .groupby(["model", "answer_format"], dropna=False, sort=True)
        .size()
        .rename("rows")
        .reset_index()
    )
    failures = scored.loc[
        ~scored["parse_ok"],
        [
            "row_id",
            "model",
            "domain",
            "stem",
            "question_id",
            "level",
            "answer_format",
            "response_raw",
            "error",
            "parse_error",
        ],
    ]

    per_level.to_csv(args.output_dir / "per_level.csv", index=False)
    per_domain.to_csv(args.output_dir / "per_domain.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    answer_format_counts.to_csv(
        args.output_dir / "answer_format_counts.csv", index=False
    )
    failures.to_csv(args.output_dir / "parse_failures.csv", index=False)

    print("Rows by model and answer_format:")
    print(answer_format_counts.to_string(index=False))
    print()
    print("Parse failure rates:")
    rates = scored.groupby("model")["parse_ok"].agg(rows="size", parsed="sum")
    rates["parse_failure_rate"] = 1.0 - rates["parsed"] / rates["rows"]
    print(rates.to_string())
    print(f"\nWrote analysis tables to {args.output_dir}")
    no_signal = per_level.loc[per_level["absolute_no_signal"].astype(bool), ["model", "level"]]
    if not no_signal.empty:
        print("\nLevels with a 100% constant-answer baseline (no signal):")
        print(no_signal.to_string(index=False))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument("--output-dir", type=Path, default=TEST_ROOT / "analysis")
    parser.add_argument("--models", help="Comma-separated model keys; default is available files")
    parser.add_argument("--bootstrap", type=int, default=10_000)
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    args = parse_args()
    if args.bootstrap < 1:
        raise ValueError("--bootstrap must be positive")
    score(args)


if __name__ == "__main__":
    main()
