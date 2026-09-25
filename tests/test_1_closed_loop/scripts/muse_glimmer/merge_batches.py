"""Validate and merge completed Muse Glimmer closed-loop batch results.

The canonical result is replaced atomically only after every manifest row has
one successful response. Raw batch files remain untouched.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


MODEL_KEY = "muse_glimmer_30b"
TEST_ROOT = Path(__file__).resolve().parents[2]


def read_manifest_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [str(row.get("row_id", "")) for row in rows]
    if any(not row_id for row_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Manifest has blank or duplicate row_id values")
    return ids


def ingest(path: Path, successful: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """Keep the last successful record for each row ID from one JSONL file."""

    physical = 0
    accepted = 0
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
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=TEST_ROOT / "results" / f"closed_loop_{MODEL_KEY}.jsonl",
    )
    parser.add_argument(
        "--batch-root", type=Path, default=TEST_ROOT / "results" / "muse_glimmer_30b_batches"
    )
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    if args.shards < 2:
        raise ValueError("--shards must be at least 2")

    ordered_ids = read_manifest_ids(args.manifest)
    expected = set(ordered_ids)
    successful: dict[str, dict[str, Any]] = {}
    sources = [args.canonical]
    sources.extend(
        args.batch_root / f"batch_{index}" / f"closed_loop_{MODEL_KEY}.jsonl"
        for index in range(1, args.shards + 1)
    )
    for path in sources:
        physical, accepted = ingest(path, successful)
        print(f"{path}: {physical:,} records, {accepted:,} successful records read")

    unexpected = set(successful) - expected
    missing = expected - set(successful)
    if unexpected:
        raise ValueError(f"Successful result IDs absent from manifest: {sorted(unexpected)[:10]}")
    if missing:
        print(f"Merge not performed: {len(missing):,} successful rows are still missing.")
        print("First missing IDs:")
        for row_id in sorted(missing)[:20]:
            print(f"  {row_id}")
        raise SystemExit(2)

    args.canonical.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.canonical.with_suffix(args.canonical.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        for row_id in ordered_ids:
            handle.write(
                json.dumps(successful[row_id], ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, args.canonical)
    print(f"Merged {len(ordered_ids):,} successful rows into {args.canonical}")
    print("Raw batch result files were retained.")


if __name__ == "__main__":
    main()
