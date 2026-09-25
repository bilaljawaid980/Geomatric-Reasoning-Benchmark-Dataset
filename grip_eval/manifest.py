"""Manifest loading and validation shared by evaluation phases."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MANIFEST_COLUMNS = [
    "row_id",
    "domain",
    "stem",
    "image_path",
    "question_id",
    "level",
    "prompt",
    "ground_truth",
    "answer_format",
    "tolerance",
    "in_core_subset",
]


def load_manifest(path: str | Path) -> pd.DataFrame:
    """Load a closed-loop manifest and enforce its public schema and unique IDs."""

    manifest_path = Path(path)
    frame = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    missing = [column for column in MANIFEST_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{manifest_path} is missing columns: {missing}")
    if frame["row_id"].duplicated().any():
        duplicates = frame.loc[frame["row_id"].duplicated(), "row_id"].head().tolist()
        raise ValueError(f"Duplicate manifest row_id values: {duplicates}")
    frame["level"] = pd.to_numeric(frame["level"], errors="raise").astype(int)
    if not frame["level"].between(1, 5).all():
        raise ValueError("Manifest levels must all be integers from 1 through 5")
    frame["in_core_subset"] = frame["in_core_subset"].str.lower().eq("true")
    return frame


def select_models(value: str | None, available: list[str]) -> list[str]:
    """Parse a comma-separated model selection while preserving config order."""

    if not value:
        return available
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(f"Unknown model keys: {unknown}; available: {available}")
    return requested
