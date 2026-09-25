"""Build a manifest containing Round-1 rows without a complete ANSWER section."""

from __future__ import annotations

import argparse
from pathlib import Path

from crossexam_common import load_jsonl_latest, read_csv, response_parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = read_csv(args.manifest)
    frame = manifest.loc[manifest["model"] == args.model].copy()
    records = load_jsonl_latest(
        args.results_dir / f"crossexam_r1_{args.model}.jsonl", args.model
    )
    repair_ids: list[str] = []
    for row_id in frame["row_id"]:
        record = records.get(str(row_id))
        if not record or record.get("error"):
            repair_ids.append(str(row_id))
            continue
        answer = response_parts(str(record.get("response_raw", "")))["answer"]
        if not answer or not answer.strip():
            repair_ids.append(str(row_id))

    repairs = frame.loc[frame["row_id"].isin(repair_ids)].copy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    repairs.to_csv(args.output, index=False)
    print(f"{args.model}: {len(repairs):,} incomplete rows written to {args.output}")


if __name__ == "__main__":
    main()

