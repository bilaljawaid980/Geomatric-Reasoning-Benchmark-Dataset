"""Overlay isolated Round-1 repair responses onto the original result set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from crossexam_common import load_jsonl_latest, read_csv, response_parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--original-results-dir", type=Path, required=True)
    parser.add_argument(
        "--repair-results-dir", type=Path, action="append", required=True,
        help="Repair result directory; repeat in oldest-to-newest overlay order",
    )
    parser.add_argument("--output-results-dir", type=Path, required=True)
    args = parser.parse_args()

    expected = read_csv(args.manifest)
    expected = expected.loc[expected["model"] == args.model]
    original = load_jsonl_latest(
        args.original_results_dir / f"crossexam_r1_{args.model}.jsonl", args.model
    )
    combined = dict(original)
    repair_count = 0
    for repair_dir in args.repair_results_dir:
        repairs = load_jsonl_latest(
            repair_dir / f"crossexam_r1_{args.model}.jsonl", args.model
        )
        combined.update(repairs)
        repair_count += len(repairs)
    expected_ids = [str(value) for value in expected["row_id"]]
    missing = [row_id for row_id in expected_ids if row_id not in combined]
    if missing:
        raise ValueError(f"Combined result set is missing {len(missing):,} rows")
    incomplete = []
    for row_id in expected_ids:
        record = combined[row_id]
        answer = response_parts(str(record.get("response_raw", "")))["answer"]
        if record.get("error") or not answer or not answer.strip():
            incomplete.append(row_id)
    if incomplete:
        raise ValueError(f"Repair set still has {len(incomplete):,} incomplete rows")

    args.output_results_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_results_dir / f"crossexam_r1_{args.model}.jsonl"
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row_id in expected_ids:
            handle.write(json.dumps(combined[row_id], ensure_ascii=False) + "\n")
    temporary.replace(output)
    print(
        f"{args.model}: overlaid {repair_count:,} repair records; "
        f"wrote {len(expected_ids):,} complete rows to {output}"
    )


if __name__ == "__main__":
    main()
