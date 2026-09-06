"""Build the separate suite-level supplementary open-question CSVs."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parent
REPO_ROOT = DATASET_ROOT.parent
COMBINED_ROOT = REPO_ROOT / "combined"
PUBLIC_OUT = COMBINED_ROOT / "all_open_questions_combined.csv"
PRIVATE_OUT = COMBINED_ROOT / "all_open_answers_combined.csv"
REPORT_OUT = DATASET_ROOT / "combined_open_question_report.json"

SOURCE_PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
PUBLIC_COLUMNS = ["dataset", "dataset_version", "question_id", "image", "image_path", "prompt"]
PRIVATE_COLUMNS = PUBLIC_COLUMNS + [
    "target", "target_position", "target_degree", "lines_at_target", "colors",
    "reached", "unreached", "answer", "home_on_boundary", "neighbour_count",
    "holes_touching", "walkable_touching", "hole_directions",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in rows)


def main() -> None:
    discovered: list[Path] = []
    incomplete: list[str] = []
    for folder in sorted(path for path in DATASET_ROOT.iterdir() if path.is_dir()):
        public_exists = (folder / "open_questions.csv").is_file()
        private_exists = (folder / "open_answer_key.csv").is_file()
        if public_exists != private_exists:
            incomplete.append(folder.name)
        elif public_exists:
            discovered.append(folder)
    if incomplete:
        raise RuntimeError(f"Incomplete open-question file pairs: {incomplete}")
    expected = {"route_dataset_3000", "hex_pathfinding_dataset_3000"}
    if {folder.name for folder in discovered} != expected:
        raise RuntimeError(f"Expected open sets for {sorted(expected)}, found {[f.name for f in discovered]}")

    public_rows: list[dict[str, str]] = []
    private_rows: list[dict[str, str]] = []
    per_dataset: dict[str, dict[str, int | str]] = {}
    for folder in discovered:
        public_header, public = read_csv(folder / "open_questions.csv")
        private_header, private = read_csv(folder / "open_answer_key.csv")
        if public_header != SOURCE_PUBLIC_COLUMNS:
            raise RuntimeError(f"{folder.name}: public schema is {public_header}")
        if len(public) != 3000 or len(private) != 3000:
            raise RuntimeError(f"{folder.name}: expected 3000 public/private rows")
        private_by_id = {row["question_id"]: row for row in private}
        if len(private_by_id) != len(private):
            raise RuntimeError(f"{folder.name}: duplicate private question_id")
        manifest = json.loads((folder / "build_manifest.json").read_text(encoding="utf-8"))
        version = str(manifest["dataset_version"])
        dataset = folder.name.rsplit("_dataset_", 1)[0]
        for row in public:
            qid = row["question_id"]
            answer = private_by_id.get(qid)
            if answer is None:
                raise RuntimeError(f"{folder.name}/{qid}: no unique answer row")
            if any(answer.get(key, "") != row[key] for key in ("question_id", "image")):
                raise RuntimeError(f"{folder.name}/{qid}: public/private row drift")
            image_path = (Path("Dataset") / folder.name / "images" / row["image"]).as_posix()
            if not (REPO_ROOT / image_path).is_file():
                raise RuntimeError(f"{folder.name}/{qid}: missing image {image_path}")
            base = {
                "dataset": dataset,
                "dataset_version": version,
                **row,
                "image_path": image_path,
            }
            public_rows.append(base)
            private_rows.append({**base, **{key: answer.get(key, "") for key in private_header[2:]}})
        per_dataset[folder.name] = {
            "dataset_version": version,
            "images": len(public),
            "open_questions": len(public),
            "open_answers": len(private),
        }

    duplicate_ids = [qid for qid, count in Counter(row["question_id"] for row in public_rows).items() if count != 1]
    if duplicate_ids:
        raise RuntimeError(f"Combined open question IDs are not unique: {duplicate_ids[:5]}")
    if len(public_rows) != 6000 or len(private_rows) != 6000:
        raise RuntimeError("Combined open row count must be exactly 6000")
    write_csv(PUBLIC_OUT, public_rows, PUBLIC_COLUMNS)
    write_csv(PRIVATE_OUT, private_rows, PRIVATE_COLUMNS)
    report = {
        "status": "PASS",
        "datasets": per_dataset,
        "combined_open_questions": len(public_rows),
        "combined_open_answers": len(private_rows),
        "unique_question_ids": len({row["question_id"] for row in public_rows}),
        "resolved_image_paths": len({row["image_path"] for row in public_rows}),
        "public_columns": PUBLIC_COLUMNS,
        "private_columns": PRIVATE_COLUMNS,
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
