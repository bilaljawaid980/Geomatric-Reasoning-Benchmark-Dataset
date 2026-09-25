"""Prepare four non-overlapping closed-loop shards for Muse Glimmer 30B.

This script performs local file preparation only. It never calls an API.
Successful rows already present in the canonical Muse result file are excluded
from the shards so the smoke-test calls are not repeated.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


MODEL_KEY = "muse_glimmer_30b"
TEST_ROOT = Path(__file__).resolve().parents[2]


def successful_row_ids(path: Path) -> set[str]:
    """Return row IDs having at least one successful stored response."""

    completed: set[str] = set()
    if not path.is_file():
        return completed
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
            if not record.get("error"):
                completed.add(row_id)
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument(
        "--existing-results",
        type=Path,
        default=TEST_ROOT / "results" / f"closed_loop_{MODEL_KEY}.jsonl",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=TEST_ROOT / "plan" / "muse_glimmer_batches"
    )
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    if args.shards < 2:
        raise ValueError("--shards must be at least 2")

    with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    required = {"row_id", "domain", "level"}
    if not required.issubset(fieldnames):
        raise ValueError(f"Manifest is missing columns: {sorted(required - set(fieldnames))}")
    if len({row["row_id"] for row in rows}) != len(rows):
        raise ValueError("The source manifest contains duplicate row_id values")

    completed = successful_row_ids(args.existing_results)
    manifest_ids = {row["row_id"] for row in rows}
    unknown = completed - manifest_ids
    if unknown:
        raise ValueError(f"Existing results contain IDs absent from the manifest: {sorted(unknown)[:5]}")
    pending = [row for row in rows if row["row_id"] not in completed]

    # Round-robin independently inside each domain/level cell. This keeps the
    # workload composition balanced while guaranteeing disjoint row IDs.
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pending:
        groups[(row["domain"], row["level"])].append(row)
    shards: list[list[dict[str, str]]] = [[] for _ in range(args.shards)]
    for key in sorted(groups):
        for index, row in enumerate(sorted(groups[key], key=lambda item: item["row_id"])):
            shards[index % args.shards].append(row)

    assigned = [row["row_id"] for shard in shards for row in shard]
    if len(assigned) != len(set(assigned)) or set(assigned) != {
        row["row_id"] for row in pending
    }:
        raise AssertionError("Shard assignment is not an exact partition")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for index, shard in enumerate(shards, start=1):
        path = args.output_dir / f"batch_{index}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(shard)
        print(f"batch_{index}: {len(shard):,} rows -> {path}")

    print(f"Already successful and excluded: {len(completed):,}")
    print(f"Pending rows partitioned: {len(pending):,}")
    print(f"Full manifest rows: {len(rows):,}")


if __name__ == "__main__":
    main()
