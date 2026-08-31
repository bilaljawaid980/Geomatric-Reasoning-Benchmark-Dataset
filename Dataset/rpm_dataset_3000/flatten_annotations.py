"""Flatten RPM annotations and create public/private question splits."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


TASKS = {1: "Image Description", 2: "Inductive Pattern Completion", 3: "Comparative Reasoning", 4: "Compound Rule Reasoning"}
META_FIELDS = ["difficulty_score", "difficulty_tier", "num_active_rules", "orientation", "seed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", type=Path, nargs="?", default=Path(__file__).resolve().parent / "annotations.jsonl")
    args = parser.parse_args()
    records = [json.loads(line) for line in args.annotations.read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for record in records:
        if len(record["questions"]) != 4:
            raise ValueError(f"{record['id']} does not have four questions")
        meta = json.dumps({k: record[k] for k in META_FIELDS}, sort_keys=True, separators=(",", ":"))
        for q in record["questions"]:
            rows.append({"task": TASKS[q["difficulty_level"]], "image": Path(record["image_path"]).name, "prompt": q["question_text"], "groundtruth": str(q["ground_truth"]), "metadata": meta})
    root = args.annotations.parent
    fields = ["task", "image", "prompt", "groundtruth", "metadata"]
    with (root / "dataset_final.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with (root / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    qfields = ["question_id", "task", "image", "prompt"]
    afields = qfields + ["groundtruth"]
    with (root / "question_set.csv").open("w", encoding="utf-8-sig", newline="") as fq, (root / "answer_key.csv").open("w", encoding="utf-8-sig", newline="") as fa:
        wq, wa = csv.DictWriter(fq, fieldnames=qfields), csv.DictWriter(fa, fieldnames=afields)
        wq.writeheader(); wa.writeheader()
        for i, row in enumerate(rows, 1):
            qrow = {"question_id": f"rpm_dataset_3000_{i}", "task": row["task"], "image": row["image"], "prompt": row["prompt"]}
            wq.writerow(qrow); wa.writerow({**qrow, "groundtruth": row["groundtruth"]})
    counts = Counter(r["task"] for r in rows)
    print(f"Images: {len(records)}\nRows: {len(rows)}\nExpected: {4 * len(records)}")
    for task in TASKS.values():
        print(f"{task}: {counts[task]}")
    assert len(rows) == 4 * len(records)
    print("Sanity check: PASS")


if __name__ == "__main__":
    main()
