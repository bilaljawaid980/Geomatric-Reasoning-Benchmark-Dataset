"""Flatten orthographic annotations into CSV and JSONL question rows."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


TASKS = {
    1: "Image Description",
    2: "Basic Relational Reasoning",
    3: "Comparative Reasoning",
    4: "Compound Reasoning",
}
METADATA_FIELDS = [
    "difficulty_score",
    "total_cube_count",
    "minimum_possible_cube_count",
    "has_candidate_panel",
    "is_uniquely_determined",
    "seed",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", type=Path, nargs="?", default=Path(__file__).resolve().parent / "annotations.jsonl")
    args = parser.parse_args()
    rows = []
    images = 0
    invalid = []
    for line in args.annotations.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        images += 1
        if len(record["questions"]) != 4:
            invalid.append(record["id"])
        metadata = json.dumps({key: record[key] for key in METADATA_FIELDS}, sort_keys=True, separators=(",", ":"))
        for question in record["questions"]:
            rows.append({
                "task": TASKS[question["difficulty_level"]],
                "image": Path(record["image_path"]).name,
                "prompt": question["question_text"],
                "groundtruth": str(question["ground_truth"]),
                "metadata": metadata,
            })
    out = args.annotations.parent
    columns = ["task", "image", "prompt", "groundtruth", "metadata"]
    with (out / "dataset_final.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with (out / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    counts = Counter(row["task"] for row in rows)
    print(f"Images: {images}\nRows: {len(rows)}\nExpected: {4 * images}\nImages without 4 questions: {len(invalid)}")
    for task in TASKS.values():
        print(f"{task}: {counts[task]}")
    assert len(rows) == 4 * images and not invalid
    print("Sanity check: PASS")


if __name__ == "__main__":
    main()
