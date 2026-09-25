"""Merge Test 4 batch JSONL files into validated canonical result files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

TEST_ROOT = Path(__file__).resolve().parents[1]
ARMS = ("natural", "constructed", "control_reask")


def read_latest(paths: list[Path]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error
                row_id = str(record.get("row_id", ""))
                if not row_id:
                    raise ValueError(f"Missing row_id at {path}:{line_number}")
                previous = records.get(row_id)
                if previous is None or previous.get("error") or not record.get("error"):
                    records[row_id] = record
    return records


def write_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=(1, 2), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--batches", type=int, default=4)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--batch-results-root", type=Path, default=TEST_ROOT / "results/batches")
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    args = parser.parse_args()
    manifest = args.manifest or TEST_ROOT / "plan" / (
        "crossexam_manifest.csv" if args.phase == 1 else "crossexam_round2_manifest.csv"
    )
    frame = pd.read_csv(manifest, dtype=str, keep_default_na=False)
    frame = frame.loc[frame["model"] == args.model].copy()
    if frame.empty:
        raise ValueError(f"No rows for {args.model} in {manifest}")
    batch_root = args.batch_results_root / f"phase{args.phase}" / args.model

    if args.phase == 1:
        canonical = args.results_dir / f"crossexam_r1_{args.model}.jsonl"
        paths = [
            batch_root / f"batch_{index}" / f"crossexam_r1_{args.model}.jsonl"
            for index in range(1, args.batches + 1)
        ]
        if canonical.is_file():
            # Canonical contains the older snapshot. Read it first so newer
            # shard retries with the same row_id take precedence.
            paths.insert(0, canonical)
        records = read_latest(paths)
        expected = set(frame["row_id"])
        successful = {
            key for key, row in records.items()
            if not row.get("error")
            and str(row.get("response_raw", "")).strip()
            and str(row.get("response_raw", "")).strip().casefold() not in {"none", "null"}
        }
        missing = expected - successful
        extra = set(records) - expected
        if missing or extra:
            raise ValueError(
                f"Cannot finalize merge: successful={len(successful & expected):,}/{len(expected):,}, "
                f"missing={len(missing):,}, extra={len(extra):,}"
            )
        write_atomic(canonical, [records[row_id] for row_id in frame["row_id"]])
        print(f"Merged {len(expected):,} Round-1 rows into {canonical}")
        return

    for arm in ARMS:
        arm_frame = frame.loc[frame["arm"] == arm]
        canonical = args.results_dir / f"crossexam_r2_{args.model}_{arm}.jsonl"
        paths = [
            batch_root / f"batch_{index}" / f"crossexam_r2_{args.model}_{arm}.jsonl"
            for index in range(1, args.batches + 1)
        ]
        if canonical.is_file():
            paths.insert(0, canonical)
        records = read_latest(paths)
        expected = set(arm_frame["row_id"])
        successful = {
            key for key, row in records.items()
            if not row.get("error")
            and str(row.get("response_raw", "")).strip()
            and str(row.get("response_raw", "")).strip().casefold() not in {"none", "null"}
        }
        missing = expected - successful
        extra = set(records) - expected
        if missing or extra:
            raise ValueError(
                f"Cannot finalize {arm}: successful={len(successful & expected):,}/{len(expected):,}, "
                f"missing={len(missing):,}, extra={len(extra):,}"
            )
        write_atomic(canonical, [records[row_id] for row_id in arm_frame["row_id"]])
        print(f"Merged {len(expected):,} {arm} rows into {canonical}")


if __name__ == "__main__":
    main()
