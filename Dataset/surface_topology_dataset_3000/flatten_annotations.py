"""Flatten five questions per annotation into CSV/JSONL and public/private splits."""

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
    5: "Extrapolative/Counterfactual Reasoning",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("annotations", type=Path)
    args = parser.parse_args()
    source = [json.loads(line) for line in args.annotations.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for item in source:
        metadata = json.dumps(
            {key: item[key] for key in (
                "difficulty_score", "surface_type", "surface_variant", "genus",
                "genus_kind", "is_orientable", "boundary_count", "euler_characteristic", "seed"
            )},
            sort_keys=True,
            separators=(",", ":"),
        )
        for question in item["questions"]:
            rows.append({
                "task": TASKS[question["difficulty_level"]],
                "image": Path(item["image_path"]).name,
                "prompt": question["question_text"],
                "groundtruth": str(question["ground_truth"]),
                "metadata": metadata,
                "question_id": question["question_id"],
            })
    output_dir = args.annotations.parent
    final_columns = ["task", "image", "prompt", "groundtruth", "metadata"]
    with (output_dir / "dataset_final.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=final_columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in final_columns} for row in rows)
    with (output_dir / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({key: row[key] for key in final_columns}, ensure_ascii=False, separators=(",", ":")) + "\n")
    question_columns = ["question_id", "task", "image", "prompt"]
    answer_columns = question_columns + ["groundtruth"]
    with (output_dir / "question_set.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=question_columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in question_columns} for row in rows)
    with (output_dir / "answer_key.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=answer_columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in answer_columns} for row in rows)
    counts = Counter(row["task"] for row in rows)
    print(f"Images: {len(source)}")
    print(f"Rows written: {len(rows)}")
    for task in TASKS.values():
        print(f"  {task}: {counts[task]}")
    assert len(rows) == 5 * len(source)
    print("Sanity check: PASS")


if __name__ == "__main__":
    main()
