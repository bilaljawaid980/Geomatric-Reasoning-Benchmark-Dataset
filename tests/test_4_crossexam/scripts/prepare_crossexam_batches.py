"""Create deterministic non-overlapping manifest shards for Test 4."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import pandas as pd

TEST_ROOT = Path(__file__).resolve().parents[1]


def stable_bucket(row_id: str, batches: int) -> int:
    digest = hashlib.sha256(row_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % batches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=(1, 2), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--batches", type=int, default=4)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-root", type=Path, default=TEST_ROOT / "plan/batches")
    args = parser.parse_args()
    if args.batches < 1:
        parser.error("--batches must be positive")
    manifest = args.manifest or TEST_ROOT / "plan" / (
        "crossexam_manifest.csv" if args.phase == 1 else "crossexam_round2_manifest.csv"
    )
    frame = pd.read_csv(manifest, dtype=str, keep_default_na=False)
    if "row_id" not in frame or "model" not in frame:
        raise ValueError(f"Manifest lacks row_id/model columns: {manifest}")
    frame = frame.loc[frame["model"] == args.model].copy()
    if frame.empty:
        raise ValueError(f"No rows for {args.model} in {manifest}")
    if frame["row_id"].duplicated().any():
        raise ValueError(f"Duplicate row IDs for {args.model}")
    frame["_batch"] = frame["row_id"].map(lambda value: stable_bucket(value, args.batches))
    output_dir = args.output_root / f"phase{args.phase}" / args.model
    output_dir.mkdir(parents=True, exist_ok=True)
    written: set[str] = set()
    for index in range(args.batches):
        shard = frame.loc[frame["_batch"] == index].drop(columns="_batch")
        overlap = written & set(shard["row_id"])
        if overlap:
            raise AssertionError(f"Overlapping batch rows: {sorted(overlap)[:3]}")
        written.update(shard["row_id"])
        path = output_dir / f"batch_{index + 1}.csv"
        shard.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"batch_{index + 1}: {len(shard):,} rows")
    expected = set(frame["row_id"])
    if written != expected:
        raise AssertionError(f"Shard coverage mismatch: {len(written):,}/{len(expected):,}")
    print(f"Total rows written exactly once: {len(written):,}")
    print(f"Batch directory: {output_dir}")


if __name__ == "__main__":
    main()
