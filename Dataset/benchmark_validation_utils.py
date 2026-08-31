"""Shared, dependency-free reporting helpers for GRIP dataset validators."""
from __future__ import annotations

import math
from collections import Counter, defaultdict


def quantiles(values):
    data = sorted(float(value) for value in values)
    if not data:
        return {"count": 0}

    def percentile(fraction):
        position = fraction * (len(data) - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return data[lower]
        return data[lower] + (data[upper] - data[lower]) * (position - lower)

    return {
        "count": len(data), "min": data[0], "p25": percentile(.25),
        "p50": percentile(.50), "p75": percentile(.75),
        "p95": percentile(.95), "max": data[-1],
    }


def cramers_v_raw(xs, ys):
    pairs = [(str(x), str(y)) for x, y in zip(xs, ys)]
    if not pairs:
        return 0.0
    rows = sorted({x for x, _ in pairs})
    cols = sorted({y for _, y in pairs})
    if len(rows) < 2 or len(cols) < 2:
        return 0.0
    table = Counter(pairs)
    row_counts = Counter(x for x, _ in pairs)
    col_counts = Counter(y for _, y in pairs)
    total = len(pairs)
    chi2 = 0.0
    for row in rows:
        for col in cols:
            expected = row_counts[row] * col_counts[col] / total
            chi2 += (table[row, col] - expected) ** 2 / expected
    return math.sqrt((chi2 / total) / min(len(rows) - 1, len(cols) - 1))


def cramers_v(xs, ys):
    """Bias-corrected Cramer's V (Bergsma/Wicher correction).

    The correction is essential for sparse, high-cardinality features such as
    canvas-size pairs: uncorrected V approaches one when most contingency-table
    cells are empty even when the variables were sampled independently.
    """
    pairs = [(str(x), str(y)) for x, y in zip(xs, ys)]
    if not pairs:
        return 0.0
    rows = sorted({x for x, _ in pairs})
    cols = sorted({y for _, y in pairs})
    if len(rows) < 2 or len(cols) < 2:
        return 0.0
    table = Counter(pairs)
    row_counts = Counter(x for x, _ in pairs)
    col_counts = Counter(y for _, y in pairs)
    total = len(pairs)
    chi2 = 0.0
    for row in rows:
        for col in cols:
            expected = row_counts[row] * col_counts[col] / total
            chi2 += (table[row, col] - expected) ** 2 / expected
    phi2 = chi2 / total
    row_count, col_count = len(rows), len(cols)
    corrected_phi2 = max(0.0, phi2 - ((col_count - 1) * (row_count - 1)) / (total - 1))
    corrected_rows = row_count - ((row_count - 1) ** 2) / (total - 1)
    corrected_cols = col_count - ((col_count - 1) ** 2) / (total - 1)
    denominator = min(corrected_rows - 1, corrected_cols - 1)
    return math.sqrt(corrected_phi2 / denominator) if denominator > 0 else 0.0


def decile_labels(values):
    numeric = [float(value) for value in values]
    ordered = sorted(numeric)
    if len(set(ordered)) < 2:
        return ["0"] * len(numeric)
    cuts = [ordered[min(len(ordered) - 1, int(len(ordered) * step / 10))]
            for step in range(1, 10)]
    return [str(sum(value > cut for cut in cuts)) for value in numeric]


def feature_association(values, answers):
    if values and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                      for value in values):
        return cramers_v(decile_labels(values), answers), "numeric_deciles"
    normalized = [repr(value) if isinstance(value, (dict, list)) else str(value)
                  for value in values]
    return cramers_v(normalized, answers), "categorical"


def distributions(records, continuous, categorical):
    return {
        "continuous": {name: quantiles([row[name] for row in records])
                       for name in continuous},
        "categorical": {name: dict(sorted(Counter(str(row[name]) for row in records).items()))
                        for name in categorical},
    }


def answer_distributions(records):
    result = {}
    for level in range(1, 6):
        counts = Counter(str(row["questions"][level - 1]["ground_truth"]) for row in records)
        total = sum(counts.values())
        result[str(level)] = {
            "counts": dict(counts),
            "constant_answer_baseline": max(counts.values(), default=0) / total if total else 0.0,
        }
    return result


def leak_audit(records, feature_names, whitelist):
    result = {}
    for feature in feature_names:
        values = [row[feature] for row in records]
        levels = {}
        for level in range(1, 6):
            answers = [row["questions"][level - 1]["ground_truth"] for row in records]
            value, kind = feature_association(values, answers)
            levels[str(level)] = {"cramers_v": value, "kind": kind}
        result[feature] = {
            "levels": levels,
            "classification": "definitional" if feature in whitelist else "scene_feature",
            "whitelist_justification": whitelist.get(feature),
        }
    return result


def split_summary(records, value_field, split_field):
    groups = defaultdict(list)
    for row in records:
        groups[str(row[split_field])].append(row[value_field])
    return {key: quantiles(values) for key, values in sorted(groups.items())}
