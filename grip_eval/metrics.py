"""Bootstrap metrics for absolute and chain-conditional GRIP scoring."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MetricSummary:
    """Accuracy, baseline-normalized score, and bootstrap intervals."""

    rows: int
    items: int
    accuracy: float
    baseline: float
    above_baseline: float | None
    accuracy_ci_low: float
    accuracy_ci_high: float
    above_baseline_ci_low: float | None
    above_baseline_ci_high: float | None
    no_signal: bool


def above_baseline_score(accuracy: float, baseline: float) -> float | None:
    """Return (accuracy - baseline) / (1 - baseline), or None at baseline 1."""

    if baseline >= 1.0:
        return None
    return (accuracy - baseline) / (1.0 - baseline)


def _observed(frame: pd.DataFrame, correct_column: str) -> tuple[float, float]:
    accuracy = float(frame[correct_column].astype(bool).mean())
    baseline = float(frame["ground_truth"].astype(str).value_counts(normalize=True).max())
    return accuracy, baseline


def bootstrap_metric(
    frame: pd.DataFrame,
    correct_column: str,
    *,
    resamples: int = 10_000,
    seed: int = 20260915,
) -> MetricSummary:
    """Bootstrap over unique domain/stem items, retaining repeated levels together."""

    if frame.empty:
        raise ValueError("Cannot summarize an empty frame")
    working = frame.copy()
    working["_item"] = working["domain"].astype(str) + "/" + working["stem"].astype(str)
    accuracy, baseline = _observed(working, correct_column)
    score = above_baseline_score(accuracy, baseline)

    labels = sorted(working["ground_truth"].astype(str).unique())
    label_index = {label: index for index, label in enumerate(labels)}
    grouped = list(working.groupby("_item", sort=False))
    correct_sums = np.array(
        [group[correct_column].astype(bool).sum() for _, group in grouped], dtype=float
    )
    totals = np.array([len(group) for _, group in grouped], dtype=float)
    label_counts = np.zeros((len(grouped), len(labels)), dtype=float)
    for group_index, (_, group) in enumerate(grouped):
        for label, count in group["ground_truth"].astype(str).value_counts().items():
            label_counts[group_index, label_index[label]] = count

    generator = np.random.default_rng(seed)
    accuracies: list[np.ndarray] = []
    scores: list[np.ndarray] = []
    batch_size = 256
    for start in range(0, resamples, batch_size):
        batch = min(batch_size, resamples - start)
        picks = generator.integers(0, len(grouped), size=(batch, len(grouped)))
        # Convert sampled group indexes to multiplicities before aggregating.
        # Indexing label_counts directly with ``picks`` creates a potentially
        # enormous batch x items x labels tensor for mixed-format suites.
        weights = np.zeros((batch, len(grouped)), dtype=np.int32)
        batch_indexes = np.repeat(np.arange(batch), len(grouped))
        np.add.at(weights, (batch_indexes, picks.ravel()), 1)
        sampled_correct = weights @ correct_sums
        sampled_total = weights @ totals
        sampled_accuracy = sampled_correct / sampled_total
        sampled_labels = weights @ label_counts
        sampled_baseline = sampled_labels.max(axis=1) / sampled_total
        accuracies.append(sampled_accuracy)
        valid = sampled_baseline < 1.0
        sampled_score = np.full(batch, np.nan)
        sampled_score[valid] = (
            sampled_accuracy[valid] - sampled_baseline[valid]
        ) / (1.0 - sampled_baseline[valid])
        scores.append(sampled_score)

    accuracy_samples = np.concatenate(accuracies)
    score_samples = np.concatenate(scores)
    accuracy_ci = np.quantile(accuracy_samples, [0.025, 0.975])
    finite_scores = score_samples[np.isfinite(score_samples)]
    score_ci = (
        np.quantile(finite_scores, [0.025, 0.975])
        if finite_scores.size
        else np.array([np.nan, np.nan])
    )
    return MetricSummary(
        rows=len(working),
        items=len(grouped),
        accuracy=accuracy,
        baseline=baseline,
        above_baseline=score,
        accuracy_ci_low=float(accuracy_ci[0]),
        accuracy_ci_high=float(accuracy_ci[1]),
        above_baseline_ci_low=float(score_ci[0]) if score is not None else None,
        above_baseline_ci_high=float(score_ci[1]) if score is not None else None,
        no_signal=baseline >= 1.0,
    )


def metric_dict(prefix: str, metric: MetricSummary) -> dict[str, object]:
    """Flatten one metric summary under a stable column prefix."""

    return {
        f"{prefix}_rows": metric.rows,
        f"{prefix}_items": metric.items,
        f"{prefix}_accuracy": metric.accuracy,
        f"{prefix}_baseline": metric.baseline,
        f"{prefix}_above_baseline": metric.above_baseline,
        f"{prefix}_accuracy_ci_low": metric.accuracy_ci_low,
        f"{prefix}_accuracy_ci_high": metric.accuracy_ci_high,
        f"{prefix}_above_baseline_ci_low": metric.above_baseline_ci_low,
        f"{prefix}_above_baseline_ci_high": metric.above_baseline_ci_high,
        f"{prefix}_no_signal": metric.no_signal,
    }
