"""Prepare four non-overlapping Grok 4.6 grain-test shards without API calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


MODEL_KEY = "grok_4_6"
SIGMAS = (15, 25, 40)
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
            response_text = str(record.get("response_raw", "")).strip()
            if not record.get("error") and response_text and response_text.casefold() not in {"none", "null"}:
                completed.add(row_id)
    return completed


def stable_image_key(domain: str, stem: str) -> bytes:
    return hashlib.sha256(f"{domain}\x1f{stem}".encode("utf-8")).digest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "grain_manifest.csv"
    )
    parser.add_argument(
        "--existing-results-dir", type=Path, default=TEST_ROOT / "results"
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
        rows = list(reader)
    if not rows:
        raise ValueError(f"Manifest is empty: {args.manifest}")
    if len({row["row_id"] for row in rows}) != len(rows):
        raise ValueError("Grain manifest contains duplicate row_id values")

    completed: set[str] = set()
    for sigma in SIGMAS:
        completed.update(
            successful_row_ids(
                args.existing_results_dir / f"grain_{MODEL_KEY}_sigma{sigma}.jsonl"
            )
        )
    pending = [row for row in rows if row["row_id"] not in completed]

    by_image: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pending:
        by_image[(row["domain"], row["stem"])].append(row)

    shards: list[list[dict[str, str]]] = [[] for _ in range(args.shards)]
    ordered_images = sorted(by_image, key=lambda key: stable_image_key(*key))
    for index, image_key in enumerate(ordered_images):
        image_rows = sorted(
            by_image[image_key], key=lambda row: (int(row["sigma"]), int(row["level"]))
        )
        shards[index % args.shards].extend(image_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written_ids: set[str] = set()
    for index, shard_rows in enumerate(shards, start=1):
        path = args.output_dir / f"batch_{index}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(shard_rows)
        ids = {row["row_id"] for row in shard_rows}
        if written_ids & ids:
            raise AssertionError("Shard overlap detected")
        written_ids.update(ids)
        sigma_counts = {
            sigma: sum(int(row["sigma"]) == sigma for row in shard_rows) for sigma in SIGMAS
        }
        image_count = len({(row["domain"], row["stem"]) for row in shard_rows})
        print(
            f"batch_{index}: {len(shard_rows):,} rows across {image_count:,} images; "
            + ", ".join(f"sigma{sigma}={sigma_counts[sigma]:,}" for sigma in SIGMAS)
        )

    expected = {row["row_id"] for row in pending}
    if written_ids != expected:
        raise AssertionError("Shard union does not equal the pending grain rows")
    print(f"Grain manifest rows: {len(rows):,}")
    print(f"Already complete in canonical Grok results: {len(completed & {r['row_id'] for r in rows}):,}")
    print(f"Pending rows written exactly once: {len(written_ids):,}")


if __name__ == "__main__":
    main()
