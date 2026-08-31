"""Flatten gear-train annotations into public/private five-level tables."""

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
    parser.add_argument("annotations", nargs="?", type=Path)
    args = parser.parse_args()
    source_path = args.annotations or Path(__file__).resolve().parent / "annotations.jsonl"
    source = [json.loads(line) for line in source_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    metadata_keys = (
        "difficulty_score", "arrangement_type", "num_gears", "driver_label",
        "driver_rpm", "driver_direction", "seed",
    )
    for item in source:
        metadata = json.dumps(
            {key: item[key] for key in metadata_keys},
            sort_keys=True, separators=(",", ":"),
        )
        for question in item["questions"]:
            rows.append({
                "question_id": question["question_id"],
                "task": TASKS[question["difficulty_level"]],
                "image": Path(item["image_path"]).name,
                "prompt": question["question_text"],
                "groundtruth": str(question["ground_truth"]),
                "metadata": metadata,
            })
    output = source_path.parent
    final_columns = ["task", "image", "prompt", "groundtruth", "metadata"]
    with (output / "dataset_final.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=final_columns, lineterminator="\n")
        writer.writeheader(); writer.writerows({k: row[k] for k in final_columns} for row in rows)
    with (output / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({k: row[k] for k in final_columns}, ensure_ascii=False, separators=(",", ":")) + "\n")
    qcols = ["question_id", "task", "image", "prompt"]
    acols = qcols + ["groundtruth"]
    for filename, columns in (("question_set.csv", qcols), ("answer_key.csv", acols)):
        with (output / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader(); writer.writerows({k: row[k] for k in columns} for row in rows)
    counts = Counter(row["task"] for row in rows)
    print(f"Images: {len(source)}")
    print(f"Rows written: {len(rows)}")
    for task in TASKS.values(): print(f"  {task}: {counts[task]}")
    if len(rows) != 5 * len(source):
        raise SystemExit("row-count sanity check failed")
    print("Sanity check: PASS")


if __name__ == "__main__":
    main()
