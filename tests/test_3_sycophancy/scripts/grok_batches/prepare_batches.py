"""Prepare non-overlapping Grok 4.6 sycophancy shards without API calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


MODEL_KEY = "grok_4_6"
TEST_ROOT = Path(__file__).resolve().parents[2]


def successful_row_ids(path: Path) -> set[str]:
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


def stable_image_key(domain: str, stem: str) -> bytes:
    return hashlib.sha256(f"{domain}\x1f{stem}".encode("utf-8")).digest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "sycophancy_manifest.csv"
    )
    parser.add_argument(
        "--existing-results",
        type=Path,
        default=TEST_ROOT / "results" / f"sycophancy_{MODEL_KEY}.jsonl",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=TEST_ROOT / "plan" / "grok_4_6_batches"
    )
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    if args.shards < 2:
        raise ValueError("--shards must be at least 2")

    with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError(f"Manifest has no header: {args.manifest}")
        model_rows = [row for row in reader if row.get("model") == MODEL_KEY]
    if not model_rows:
        raise ValueError(f"No {MODEL_KEY} rows in {args.manifest}")
    if len({row["row_id"] for row in model_rows}) != len(model_rows):
        raise ValueError("Grok manifest contains duplicate row_id values")

    completed = successful_row_ids(args.existing_results)
    pending = [row for row in model_rows if row["row_id"] not in completed]
    by_image: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pending:
        by_image[(row["domain"], row["stem"])].append(row)

    shards: list[list[dict[str, str]]] = [[] for _ in range(args.shards)]
    ordered_images = sorted(by_image, key=lambda key: stable_image_key(*key))
    for index, image_key in enumerate(ordered_images):
        rows = sorted(by_image[image_key], key=lambda row: int(row["level"]))
        shards[index % args.shards].extend(rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written_ids: set[str] = set()
    for index, rows in enumerate(shards, start=1):
        path = args.output_dir / f"batch_{index}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        ids = {row["row_id"] for row in rows}
        if written_ids & ids:
            raise AssertionError("Shard overlap detected")
        written_ids.update(ids)
        print(f"batch_{index}: {len(rows):,} rows across {len({(r['domain'], r['stem']) for r in rows}):,} images")

    expected = {row["row_id"] for row in pending}
    if written_ids != expected:
        raise AssertionError("Shard union does not equal the pending Grok rows")
    print(f"Grok manifest rows: {len(model_rows):,}")
    print(f"Already complete in canonical results: {len(completed & {r['row_id'] for r in model_rows}):,}")
    print(f"Pending rows written exactly once: {len(written_ids):,}")


if __name__ == "__main__":
    main()
