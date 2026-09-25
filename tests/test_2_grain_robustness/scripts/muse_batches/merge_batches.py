"""Validate and atomically merge completed Muse Glimmer 30B grain shards."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


MODEL_KEY = "muse_glimmer_30b"
SIGMAS = (15, 25, 40)
TEST_ROOT = Path(__file__).resolve().parents[2]


def expected_ids(path: Path) -> dict[int, list[str]]:
    by_sigma = {sigma: [] for sigma in SIGMAS}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sigma = int(row["sigma"])
            if sigma in by_sigma:
                by_sigma[sigma].append(row.get("row_id", ""))
    all_ids = [row_id for ids in by_sigma.values() for row_id in ids]
    if any(not row_id for row_id in all_ids) or len(all_ids) != len(set(all_ids)):
        raise ValueError("Grain manifest has blank, missing, or duplicate row IDs")
    return by_sigma


def ingest(path: Path, sigma: int, successful: dict[str, dict[str, Any]]) -> tuple[int, int]:
    physical = accepted = 0
    if not path.is_file():
        return physical, accepted
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            physical += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {error}") from error
            row_id = str(record.get("row_id", ""))
            if not row_id:
                raise ValueError(f"Missing row_id in {path}:{line_number}")
            if record.get("model") not in (None, MODEL_KEY):
                raise ValueError(f"Wrong model key in {path}:{line_number}")
            if int(record.get("sigma", sigma)) != sigma:
                raise ValueError(f"Wrong sigma in {path}:{line_number}")
            if not record.get("error"):
                successful[row_id] = record
                accepted += 1
    return physical, accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "grain_manifest.csv"
    )
    parser.add_argument("--canonical-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument(
        "--batch-root", type=Path, default=TEST_ROOT / "results" / "muse_glimmer_30b_batches"
    )
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()

    expected_by_sigma = expected_ids(args.manifest)
    for sigma in SIGMAS:
        ordered = expected_by_sigma[sigma]
        expected = set(ordered)
        canonical = args.canonical_dir / f"grain_{MODEL_KEY}_sigma{sigma}.jsonl"
        successful: dict[str, dict[str, Any]] = {}
        sources = [canonical]
        sources.extend(
            args.batch_root / f"batch_{index}" / f"grain_{MODEL_KEY}_sigma{sigma}.jsonl"
            for index in range(1, args.shards + 1)
        )
        for path in sources:
            physical, accepted = ingest(path, sigma, successful)
            print(f"{path}: {physical:,} physical rows, {accepted:,} successful rows")

        unknown = sorted(set(successful) - expected)
        missing = sorted(expected - set(successful))
        if unknown:
            raise ValueError(f"Sigma {sigma} contains {len(unknown)} unexpected IDs: {unknown[:5]}")
        if missing:
            raise ValueError(
                f"Merge refused: sigma {sigma} still has {len(missing):,} missing responses. "
                f"First IDs: {missing[:5]}"
            )

        canonical.parent.mkdir(parents=True, exist_ok=True)
        temporary = canonical.with_suffix(canonical.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for row_id in ordered:
                handle.write(json.dumps(successful[row_id], ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, canonical)
        print(f"Merged {len(ordered):,} sigma={sigma} rows into {canonical}")


if __name__ == "__main__":
    main()
