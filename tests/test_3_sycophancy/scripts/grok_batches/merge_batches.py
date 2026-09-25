"""Validate and atomically merge completed Grok 4.6 sycophancy shards."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


MODEL_KEY = "grok_4_6"
TEST_ROOT = Path(__file__).resolve().parents[2]


def expected_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("model") == MODEL_KEY]
    ids = [row.get("row_id", "") for row in rows]
    if not ids or any(not row_id for row_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Filtered Grok manifest has blank, missing, or duplicate row IDs")
    return ids


def ingest(path: Path, successful: dict[str, dict[str, Any]]) -> tuple[int, int]:
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
            if not record.get("error"):
                successful[row_id] = record
                accepted += 1
    return physical, accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "sycophancy_manifest.csv"
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=TEST_ROOT / "results" / f"sycophancy_{MODEL_KEY}.jsonl",
    )
    parser.add_argument(
        "--batch-root", type=Path, default=TEST_ROOT / "results" / "grok_4_6_batches"
    )
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    if args.shards < 2:
        raise ValueError("--shards must be at least 2")

    ordered_ids = expected_ids(args.manifest)
    expected = set(ordered_ids)
    successful: dict[str, dict[str, Any]] = {}
    sources = [args.canonical]
    sources.extend(
        args.batch_root / f"batch_{index}" / f"sycophancy_{MODEL_KEY}.jsonl"
        for index in range(1, args.shards + 1)
    )
    for path in sources:
        physical, accepted = ingest(path, successful)
        print(f"{path}: {physical:,} physical rows, {accepted:,} successful rows")

    unknown = sorted(set(successful) - expected)
    missing = sorted(expected - set(successful))
    if unknown:
        raise ValueError(f"Results contain {len(unknown)} IDs outside the Grok manifest: {unknown[:5]}")
    if missing:
        raise ValueError(
            f"Merge refused: {len(missing):,} Grok rows are still missing successful responses. "
            f"First IDs: {missing[:5]}"
        )

    args.canonical.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.canonical.with_suffix(args.canonical.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row_id in ordered_ids:
            handle.write(json.dumps(successful[row_id], ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, args.canonical)
    print(f"Merged {len(ordered_ids):,} validated Grok rows into {args.canonical}")


if __name__ == "__main__":
    main()
