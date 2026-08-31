"""Flatten gauge annotations into public and private per-question tables."""

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
META_KEYS = ("difficulty_score", "instrument_type", "unit", "min_value", "max_value", "tick_interval", "dial_sweep_degrees", "danger_zone_threshold", "seed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("annotations", nargs="?", type=Path, default=Path(__file__).resolve().parent / "annotations.jsonl")
    args = parser.parse_args()
    root = args.annotations.parent
    records = [json.loads(line) for line in args.annotations.read_text(encoding="utf-8").splitlines() if line]
    final_rows, question_rows, answer_rows = [], [], []
    counts = Counter()
    one_question_images = []
    for record in records:
        questions = record.get("questions", [])
        if len(questions) != 5:
            one_question_images.append(record.get("id", "<missing>"))
        metadata = json.dumps({key: record.get(key) for key in META_KEYS}, ensure_ascii=False, separators=(",", ":"))
        image = Path(record["image_path"]).name
        for question in questions:
            task = TASKS[question["difficulty_level"]]
            base = {"question_id": question["question_id"], "task": task, "image": image, "prompt": question["question_text"]}
            groundtruth = str(question["ground_truth"])
            question_rows.append(base)
            answer_rows.append({**base, "groundtruth": groundtruth})
            final_rows.append({"task": task, "image": image, "prompt": question["question_text"], "groundtruth": groundtruth, "metadata": metadata})
            counts[task] += 1

    def write_csv(path, fields, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)

    write_csv(root / "dataset_final.csv", ["task", "image", "prompt", "groundtruth", "metadata"], final_rows)
    write_csv(root / "question_set.csv", ["question_id", "task", "image", "prompt"], question_rows)
    write_csv(root / "answer_key.csv", ["question_id", "task", "image", "prompt", "groundtruth"], answer_rows)
    with (root / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in final_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    expected = 5 * len(records)
    if not (len(final_rows) == len(question_rows) == len(answer_rows) == expected) or one_question_images:
        raise ValueError(f"flatten sanity failure: records={len(records)} rows={len(final_rows)} bad={one_question_images[:10]}")
    print(f"Images: {len(records)}\nRows written: {len(final_rows)}")
    for task in TASKS.values():
        print(f"  {task}: {counts[task]}")
    print("Sanity check: PASS")


if __name__ == "__main__":
    main()
