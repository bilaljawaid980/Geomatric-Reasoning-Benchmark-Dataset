"""Build a manifest containing Phase-2 rows without a complete ANSWER section."""

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

    frame = read_csv(args.manifest)
    frame = frame.loc[frame["model"] == args.model].copy()
    records: dict[str, dict] = {}
    for arm in ("natural", "constructed", "control_reask"):
        records.update(load_jsonl_latest(
            args.results_dir / f"crossexam_r2_{args.model}_{arm}.jsonl", args.model
        ))
    repair_ids = []
    for row_id in frame["row_id"]:
        record = records.get(str(row_id))
        answer = response_parts(
            str(record.get("response_raw", "")) if record else "", round2=True
        )["answer"]
        if not record or record.get("error") or not answer or not answer.strip():
            repair_ids.append(str(row_id))
    repairs = frame.loc[frame["row_id"].isin(repair_ids)].copy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    repairs.to_csv(args.output, index=False)
    print(f"{args.model}: {len(repairs):,} incomplete Phase-2 rows written to {args.output}")


if __name__ == "__main__":
    main()

