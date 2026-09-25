"""Score within-image grain robustness with exact closed-loop comparison."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
TEST1_ROOT = REPO_ROOT / "tests" / "test_1_closed_loop"
TEST1_SCRIPTS = TEST1_ROOT / "scripts"
for import_root in (REPO_ROOT, TEST1_SCRIPTS):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from grip_eval.config import MODELS
from grip_eval.manifest import load_manifest, select_models
from grip_eval.metrics import bootstrap_metric, metric_dict
from score_closed_loop import load_results, parse_and_compare


def stable_seed(*parts: object) -> int:
    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def load_grain_manifest(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {
        "row_id",
        "domain",
        "stem",
        "sigma",
        "image_path",
        "question_id",
        "level",
        "prompt",
        "ground_truth",
        "answer_format",
    }
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing grain manifest columns: {sorted(required - set(frame.columns))}")
    if frame["row_id"].duplicated().any():
        raise ValueError("Duplicate grain manifest row_id values")
    frame["sigma"] = pd.to_numeric(frame["sigma"], errors="raise").astype(int)
    frame["level"] = pd.to_numeric(frame["level"], errors="raise").astype(int)
    frame["tolerance"] = ""
    return frame


def grouped_metrics(frame: pd.DataFrame, columns: list[str], resamples: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouper: str | list[str] = columns[0] if len(columns) == 1 else columns
    for keys, group in frame.groupby(grouper, sort=True):
        values = keys if isinstance(keys, tuple) else (keys,)
        prefix = dict(zip(columns, values))
        metric = bootstrap_metric(
            group,
            "absolute_correct",
            resamples=resamples,
            seed=stable_seed(*values, "grain_accuracy"),
        )
        rows.append({**prefix, **metric_dict("absolute", metric)})
    return pd.DataFrame(rows)


def paired_drop(
    clean: pd.DataFrame,
    noisy: pd.DataFrame,
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    """Return paired noisy-minus-clean accuracy with image-cluster bootstrap CI."""

    paired = clean[["comparison_id", "domain", "stem", "absolute_correct"]].merge(
        noisy[["comparison_id", "absolute_correct"]],
        on="comparison_id",
        how="inner",
        validate="one_to_one",
        suffixes=("_clean", "_noisy"),
    )
    if paired.empty:
        return {
            "paired_rows": 0,
            "paired_images": 0,
            "sigma0_accuracy": None,
            "noisy_accuracy": None,
            "accuracy_change": None,
            "change_ci_low": None,
            "change_ci_high": None,
            "significant_drop": False,
        }
    paired["_item"] = paired["domain"] + "/" + paired["stem"]
    grouped = list(paired.groupby("_item", sort=False))
    clean_sums = np.array(
        [group["absolute_correct_clean"].astype(bool).sum() for _, group in grouped],
        dtype=float,
    )
    noisy_sums = np.array(
        [group["absolute_correct_noisy"].astype(bool).sum() for _, group in grouped],
        dtype=float,
    )
    totals = np.array([len(group) for _, group in grouped], dtype=float)
    generator = np.random.default_rng(seed)
    samples: list[np.ndarray] = []
    for start in range(0, resamples, 256):
        batch = min(256, resamples - start)
        picks = generator.integers(0, len(grouped), size=(batch, len(grouped)))
        denominator = totals[picks].sum(axis=1)
        samples.append(
            noisy_sums[picks].sum(axis=1) / denominator
            - clean_sums[picks].sum(axis=1) / denominator
        )
    changes = np.concatenate(samples)
    low, high = np.quantile(changes, [0.025, 0.975])
    clean_accuracy = float(paired["absolute_correct_clean"].astype(bool).mean())
    noisy_accuracy = float(paired["absolute_correct_noisy"].astype(bool).mean())
    return {
        "paired_rows": len(paired),
        "paired_images": len(grouped),
        "sigma0_accuracy": clean_accuracy,
        "noisy_accuracy": noisy_accuracy,
        "accuracy_change": noisy_accuracy - clean_accuracy,
        "change_ci_low": float(low),
        "change_ci_high": float(high),
        "significant_drop": bool(high < 0.0),
    }


def discover_models(results_dir: Path) -> list[str]:
    pattern = re.compile(r"^grain_(.+)_sigma\d+\.jsonl$")
    found = {
        match.group(1)
        for path in results_dir.glob("grain_*_sigma*.jsonl")
        if (match := pattern.fullmatch(path.name))
    }
    return [key for key in MODELS if key in found]


def score(args: argparse.Namespace) -> None:
    grain_manifest = load_grain_manifest(args.grain_manifest)
    closed_manifest = load_manifest(args.closed_manifest)
    model_keys = select_models(args.models, list(MODELS)) if args.models else discover_models(args.results_dir)
    if not model_keys:
        raise FileNotFoundError(f"No grain result files found in {args.results_dir}")

    scored_frames: list[pd.DataFrame] = []
    for model_key in model_keys:
        clean_path = args.closed_results_dir / f"closed_loop_{model_key}.jsonl"
        if not clean_path.is_file():
            raise FileNotFoundError(f"Missing sigma=0 closed-loop results: {clean_path}")
        clean = load_results(clean_path, model_key).merge(
            closed_manifest,
            on="row_id",
            how="inner",
            validate="one_to_one",
            suffixes=("_response", ""),
        )
        clean = clean.loc[clean["in_core_subset"]].copy()
        clean["sigma"] = 0
        clean["comparison_id"] = clean["domain"] + ":" + clean["question_id"]
        scored_frames.append(parse_and_compare(clean))

        for sigma in sorted(grain_manifest["sigma"].unique()):
            path = args.results_dir / f"grain_{model_key}_sigma{sigma}.jsonl"
            if not path.is_file():
                if args.models:
                    raise FileNotFoundError(f"Missing requested result file: {path}")
                continue
            manifest_sigma = grain_manifest.loc[grain_manifest["sigma"] == sigma]
            noisy = load_results(path, model_key).merge(
                manifest_sigma,
                on="row_id",
                how="left",
                validate="one_to_one",
                suffixes=("_response", ""),
            )
            if noisy["question_id"].isna().any():
                unknown = noisy.loc[noisy["question_id"].isna(), "row_id"].head().tolist()
                raise ValueError(f"Grain result IDs absent from manifest: {unknown}")
            noisy["comparison_id"] = noisy["domain"] + ":" + noisy["question_id"]
            scored_frames.append(parse_and_compare(noisy))

    scored = pd.concat(scored_frames, ignore_index=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(args.output_dir / "per_question.csv", index=False)

    per_sigma = grouped_metrics(scored, ["model", "sigma"], args.bootstrap)
    per_domain_sigma = grouped_metrics(
        scored, ["model", "domain", "sigma"], args.bootstrap
    )
    per_sigma.to_csv(args.output_dir / "per_sigma.csv", index=False)
    per_domain_sigma.to_csv(args.output_dir / "per_domain_sigma.csv", index=False)

    overall_drop_rows: list[dict[str, Any]] = []
    domain_drop_rows: list[dict[str, Any]] = []
    for model_key, model_frame in scored.groupby("model", sort=True):
        clean = model_frame.loc[model_frame["sigma"] == 0]
        for sigma in sorted(value for value in model_frame["sigma"].unique() if value > 0):
            noisy = model_frame.loc[model_frame["sigma"] == sigma]
            overall_drop_rows.append(
                {
                    "model": model_key,
                    "sigma": sigma,
                    **paired_drop(
                        clean,
                        noisy,
                        resamples=args.bootstrap,
                        seed=stable_seed(model_key, sigma, "overall_drop"),
                    ),
                }
            )
            for domain, domain_noisy in noisy.groupby("domain", sort=True):
                domain_clean = clean.loc[clean["domain"] == domain]
                domain_drop_rows.append(
                    {
                        "model": model_key,
                        "domain": domain,
                        "sigma": sigma,
                        **paired_drop(
                            domain_clean,
                            domain_noisy,
                            resamples=args.bootstrap,
                            seed=stable_seed(model_key, domain, sigma, "domain_drop"),
                        ),
                    }
                )

    overall_drops = pd.DataFrame(overall_drop_rows)
    domain_drops = pd.DataFrame(domain_drop_rows)
    overall_drops.to_csv(args.output_dir / "degradation_curve.csv", index=False)
    domain_drops.to_csv(args.output_dir / "per_domain_degradation.csv", index=False)

    first_model_rows: list[dict[str, Any]] = []
    for model, group in overall_drops.groupby("model", sort=True):
        significant = group.loc[group["significant_drop"]].sort_values("sigma")
        first_model_rows.append(
            {
                "model": model,
                "first_significant_drop_sigma": (
                    int(significant.iloc[0]["sigma"]) if not significant.empty else None
                ),
            }
        )
    first_domain_rows: list[dict[str, Any]] = []
    for (model, domain), group in domain_drops.groupby(["model", "domain"], sort=True):
        significant = group.loc[group["significant_drop"]].sort_values("sigma")
        first_domain_rows.append(
            {
                "model": model,
                "domain": domain,
                "first_significant_drop_sigma": (
                    int(significant.iloc[0]["sigma"]) if not significant.empty else None
                ),
            }
        )
    first_models = pd.DataFrame(first_model_rows)
    first_domains = pd.DataFrame(first_domain_rows)
    first_models.to_csv(args.output_dir / "first_significant_drop.csv", index=False)
    first_domains.to_csv(args.output_dir / "domain_break_sigma.csv", index=False)
    break_summary = (
        first_domains.assign(
            break_bucket=first_domains["first_significant_drop_sigma"]
            .fillna("no significant drop")
            .astype(str)
        )
        .groupby(["model", "break_bucket"], sort=True)
        .size()
        .rename("domains")
        .reset_index()
    )
    break_summary.to_csv(args.output_dir / "domain_break_summary.csv", index=False)

    print("Accuracy and above-baseline score by model and sigma:")
    print(per_sigma.to_string(index=False))
    print("\nFirst significant drop by model:")
    print(first_models.to_string(index=False))
    print("\nDomain break-sigma distribution:")
    print(break_summary.to_string(index=False))
    print(f"\nWrote grain analysis to {args.output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grain-manifest", type=Path, default=TEST_ROOT / "plan" / "grain_manifest.csv"
    )
    parser.add_argument(
        "--closed-manifest", type=Path, default=TEST1_ROOT / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument("--closed-results-dir", type=Path, default=TEST1_ROOT / "results")
    parser.add_argument("--output-dir", type=Path, default=TEST_ROOT / "analysis")
    parser.add_argument("--models", help="Comma-separated model keys")
    parser.add_argument("--bootstrap", type=int, default=10_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bootstrap < 1:
        raise ValueError("--bootstrap must be positive")
    score(args)


if __name__ == "__main__":
    main()
