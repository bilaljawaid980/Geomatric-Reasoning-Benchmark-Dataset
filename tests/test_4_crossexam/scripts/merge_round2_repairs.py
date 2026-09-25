"""Overlay isolated Phase-2 repair responses onto the original result set."""

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
    parser.add_argument("--repair-results-dir", type=Path, required=True)
    parser.add_argument("--output-results-dir", type=Path, required=True)
    args = parser.parse_args()

    frame = read_csv(args.manifest)
    frame = frame.loc[frame["model"] == args.model].copy()
    args.output_results_dir.mkdir(parents=True, exist_ok=True)
    repaired_total = 0
    for arm, arm_frame in frame.groupby("arm", sort=True):
        filename = f"crossexam_r2_{args.model}_{arm}.jsonl"
        original = load_jsonl_latest(args.original_results_dir / filename, args.model)
        repairs = load_jsonl_latest(args.repair_results_dir / filename, args.model)
        combined = dict(original)
        combined.update(repairs)
        expected_ids = [str(value) for value in arm_frame["row_id"]]
        incomplete = []
        for row_id in expected_ids:
            record = combined.get(row_id)
            answer = response_parts(
                str(record.get("response_raw", "")) if record else "", round2=True
            )["answer"]
            if not record or record.get("error") or not answer or not answer.strip():
                incomplete.append(row_id)
        if incomplete:
            raise ValueError(f"{arm} still has {len(incomplete):,} incomplete rows")
        output = args.output_results_dir / filename
        temporary = output.with_suffix(output.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for row_id in expected_ids:
                handle.write(json.dumps(combined[row_id], ensure_ascii=False) + "\n")
        temporary.replace(output)
        repaired_total += len(repairs)
        print(f"{arm}: wrote {len(expected_ids):,} complete rows ({len(repairs):,} repaired)")
    print(f"{args.model}: overlaid {repaired_total:,} Phase-2 repairs")


if __name__ == "__main__":
    main()

