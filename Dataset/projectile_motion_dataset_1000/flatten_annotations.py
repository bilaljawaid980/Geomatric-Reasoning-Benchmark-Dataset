"""Flatten projectile-motion annotations into GRIP CSV/JSONL outputs."""
import csv
import json
from collections import Counter
from pathlib import Path

TASKS = {1: "Image Description", 2: "Basic Relational Reasoning", 3: "Comparative Reasoning", 4: "Compound Reasoning", 5: "Extrapolative/Counterfactual Reasoning"}


def clean(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) if isinstance(value, (dict, list)) else str(value)


def main():
    root = Path(__file__).resolve().parent
    items = [json.loads(line) for line in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for item in items:
        metadata = json.dumps({key: item[key] for key in ("difficulty_score", "initial_speed_m_s", "launch_angle_degrees", "has_obstacle", "seed")}, separators=(",", ":"), sort_keys=True)
        for question in item["questions"]:
            rows.append({"question_id": question["question_id"], "task": TASKS[question["difficulty_level"]], "image": Path(item["image_path"]).name, "prompt": question["question_text"], "groundtruth": clean(question["ground_truth"]), "metadata": metadata})
    final_columns = ["task", "image", "prompt", "groundtruth", "metadata"]
    with (root / "dataset_final.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=final_columns, lineterminator="\n"); writer.writeheader(); writer.writerows({key: row[key] for key in final_columns} for row in rows)
    with (root / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({key: row[key] for key in final_columns}, ensure_ascii=False, separators=(",", ":")) + "\n")
    for name, columns in (("question_set.csv", ["question_id", "task", "image", "prompt"]), ("answer_key.csv", ["question_id", "task", "image", "prompt", "groundtruth"])):
        with (root / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n"); writer.writeheader(); writer.writerows({key: row[key] for key in columns} for row in rows)
    counts = Counter(row["task"] for row in rows)
    print(f"Images: {len(items)}\nRows: {len(rows)}")
    for task, count in counts.items(): print(f"  {task}: {count}")
    if len(rows) != len(items) * 5: raise SystemExit("row count mismatch")


if __name__ == "__main__": main()
