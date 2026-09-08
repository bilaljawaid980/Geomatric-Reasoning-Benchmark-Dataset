"""Repair the two closed-question defects identified by OPEN_QUESTION_SPEC.md."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summaries = {}
    for dataset in ("fold_punch_dataset_3000", "overlap_circles_dataset_3000"):
        folder = ROOT / dataset
        rows = [json.loads(line) for line in (folder / "annotations.jsonl").read_text(encoding="utf-8-sig").splitlines() if line]
        changed_by_qid: dict[str, tuple[str, str]] = {}
        changed_by_flat_index: dict[int, tuple[str, str]] = {}
        for item_index, row in enumerate(rows):
            if dataset.startswith("fold_punch"):
                q4, q5 = row["questions"][3], row["questions"][4]
                if q4["question_text"] == q5["question_text"] and str(q4["ground_truth"]) == str(q5["ground_truth"]):
                    q5.update(question_text="If one additional fold were made and the punch stayed away from the new crease, how many holes would appear after fully unfolding?", question_type="additional_fold_hole_count", ground_truth=str(row["num_holes"] * 2), answer_format="numeric")
                    changed_by_qid[q5["question_id"]] = (q5["question_text"], str(q5["ground_truth"]))
                    changed_by_flat_index[item_index * 5 + 4] = changed_by_qid[q5["question_id"]]
            else:
                q3 = row["questions"][2]
                if q3["question_type"] == "cluster_distribution" and q3["ground_truth"] == "target_density":
                    q3["ground_truth"] = "clustered" if row["target_overlap_density"] >= 0.40 else "spread"
                    changed_by_qid[q3["question_id"]] = (q3["question_text"], q3["ground_truth"])
                    changed_by_flat_index[item_index * 5 + 2] = changed_by_qid[q3["question_id"]]
        write_jsonl(folder / "annotations.jsonl", rows)
        for name in ("question_set.csv", "answer_key.csv", "dataset_final.csv"):
            path = folder / name
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                fields, flat = list(reader.fieldnames or []), list(reader)
            for index, data in changed_by_flat_index.items():
                prompt, answer = data
                if "prompt" in fields:
                    flat[index]["prompt"] = prompt
                if "groundtruth" in fields:
                    flat[index]["groundtruth"] = answer
            write_csv(path, fields, flat)
        jsonl_path = folder / "dataset_final.jsonl"
        flat_json = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines() if line]
        for index, (prompt, answer) in changed_by_flat_index.items():
            flat_json[index]["prompt"] = prompt
            flat_json[index]["groundtruth"] = answer
        write_jsonl(jsonl_path, flat_json)
        summaries[dataset] = len(changed_by_qid)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
