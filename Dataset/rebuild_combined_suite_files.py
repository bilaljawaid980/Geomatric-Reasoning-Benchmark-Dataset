"""Rebuild and verify the suite-level combined question and answer CSVs."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DATASET_ROOT = Path(__file__).resolve().parent
REPO_ROOT = DATASET_ROOT.parent
COMBINED_ROOT = REPO_ROOT / "All question and answer"
QUESTION_FILE = COMBINED_ROOT / "all_questions_combined.csv"
ANSWER_FILE = COMBINED_ROOT / "all_answers_combined.csv"
REPORT_FILE = DATASET_ROOT / "combined_suite_rebuild_report.json"

QUESTION_COLUMNS = ["dataset", "dataset_version", "question_id", "task", "image", "prompt"]
ANSWER_COLUMNS = QUESTION_COLUMNS + ["groundtruth", "answer_format"]
PUBLIC_COLUMNS = ["question_id", "task", "image", "prompt"]
PRIVATE_COLUMNS = PUBLIC_COLUMNS + ["groundtruth"]


def dataset_slug(folder: Path) -> str:
    return re.sub(r"_dataset_(3000|1000)$", "", folder.name)


def qid_prefix(question_id: str) -> str:
    match = re.fullmatch(r"(.+)_\d{4}_q[1-5]", question_id)
    if not match:
        raise ValueError(f"Unrecognized question_id format: {question_id}")
    return match.group(1)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in rows)


def read_annotations(folder: Path) -> list[dict]:
    path = folder / "annotations.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def dataset_version(folder: Path, annotations: list[dict]) -> str:
    if annotations and annotations[0].get("dataset_version"):
        return str(annotations[0]["dataset_version"])
    manifest = json.loads((folder / "build_manifest.json").read_text(encoding="utf-8"))
    return str(manifest.get("dataset_version", ""))


def normalize_answer_format(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def discovered_datasets() -> list[Path]:
    folders = sorted(path for path in DATASET_ROOT.iterdir()
                     if path.is_dir() and (path / "build_manifest.json").is_file())
    if not folders:
        raise RuntimeError("No dataset folders with build_manifest.json were discovered")
    return folders


def current_dataset_summary(folders: list[Path]) -> dict[str, dict]:
    summary = {}
    for folder in folders:
        annotations = read_annotations(folder)
        public = read_csv(folder / "question_set.csv")
        private = read_csv(folder / "answer_key.csv")
        manifest = json.loads((folder / "build_manifest.json").read_text(encoding="utf-8"))
        version = dataset_version(folder, annotations)
        if public and list(public[0].keys()) != PUBLIC_COLUMNS:
            raise RuntimeError(f"{folder.name}: question_set.csv has non-public columns")
        if private and list(private[0].keys())[:5] != PRIVATE_COLUMNS:
            raise RuntimeError(f"{folder.name}: answer_key.csv missing required columns")
        if len(public) != len(private):
            raise RuntimeError(f"{folder.name}: question/answer row count mismatch")
        question_ids = [row["question_id"] for row in public]
        duplicate_ids = [qid for qid, count in Counter(question_ids).items() if count != 1]
        if duplicate_ids:
            raise RuntimeError(f"{folder.name}: duplicate question_ids: {duplicate_ids[:5]}")
        public_by_image = defaultdict(list)
        for row in public:
            public_by_image[row["image"]].append(row)
        by_image = defaultdict(list)
        annotation_question_ids = set()
        for item in annotations:
            levels = [question["difficulty_level"] for question in item["questions"]]
            if levels != [1, 2, 3, 4, 5]:
                raise RuntimeError(f"{folder.name}/{item['id']}: non-ordered levels {levels}")
            for question in item["questions"]:
                annotation_question_ids.add(question["question_id"])
            image_name = Path(item["image_path"]).name
            by_image[image_name].extend(int(row["question_id"].rsplit("_q", 1)[1])
                                        for row in public_by_image[image_name])
        unresolved = set(question_ids) - annotation_question_ids
        missing_from_public = annotation_question_ids - set(question_ids)
        if unresolved or missing_from_public:
            raise RuntimeError(f"{folder.name}: question_set does not match annotations")
        for image_name, levels in by_image.items():
            if sorted(levels) != [1, 2, 3, 4, 5]:
                raise RuntimeError(f"{folder.name}/{image_name}: expected five ordered levels")
            if not (folder / "images" / image_name).is_file():
                raise RuntimeError(f"{folder.name}/{image_name}: referenced image missing")
        expected_questions = int(manifest.get("questions", len(annotations) * 5))
        if len(public) != expected_questions:
            raise RuntimeError(f"{folder.name}: rows {len(public)} != manifest questions {expected_questions}")
        summary[folder.name] = {
            "slug": dataset_slug(folder),
            "prefix": qid_prefix(public[0]["question_id"]) if public else "",
            "version": version,
            "images": len(annotations),
            "questions": len(public),
            "answers": len(private),
        }
    return summary


def existing_combined_summary(summary: dict[str, dict]) -> dict:
    if not QUESTION_FILE.is_file() or not ANSWER_FILE.is_file():
        return {"present": False}
    questions = read_csv(QUESTION_FILE)
    answers = read_csv(ANSWER_FILE)
    question_prefix_counts = Counter(qid_prefix(row["question_id"]) for row in questions)
    answer_prefix_counts = Counter(qid_prefix(row["question_id"]) for row in answers)
    present_prefixes = sorted(question_prefix_counts)
    expected_prefixes = sorted(item["prefix"] for item in summary.values())
    missing_prefixes = sorted(set(expected_prefixes) - set(present_prefixes))
    extra_prefixes = sorted(set(present_prefixes) - set(expected_prefixes))
    stale_or_mismatched = {}
    slug_to_folder = {item["slug"]: folder_name for folder_name, item in summary.items()}
    grouped = defaultdict(list)
    for row in questions:
        grouped[row["dataset"]].append(row)
    for slug, rows in grouped.items():
        folder_name = slug_to_folder.get(slug)
        if not folder_name:
            stale_or_mismatched[slug] = "no matching current dataset folder"
            continue
        folder = DATASET_ROOT / folder_name
        current_rows = read_csv(folder / "question_set.csv")
        current_version = summary[folder_name]["version"]
        comparable = [{key: row[key] for key in PUBLIC_COLUMNS} for row in rows]
        version_values = sorted(set(row.get("dataset_version", "") for row in rows))
        if comparable != current_rows:
            stale_or_mismatched[slug] = "question rows differ from current question_set.csv"
        elif version_values != [current_version]:
            stale_or_mismatched[slug] = f"dataset_version is {version_values}, expected {current_version}"
    return {
        "present": True,
        "question_rows": len(questions),
        "answer_rows": len(answers),
        "question_answer_row_counts_match": len(questions) == len(answers),
        "question_prefix_counts": dict(sorted(question_prefix_counts.items())),
        "answer_prefix_counts": dict(sorted(answer_prefix_counts.items())),
        "missing_prefixes": missing_prefixes,
        "extra_prefixes": extra_prefixes,
        "stale_or_mismatched": stale_or_mismatched,
    }


def rebuild(summary: dict[str, dict]) -> dict:
    combined_questions = []
    combined_answers = []
    for folder_name, item in summary.items():
        folder = DATASET_ROOT / folder_name
        public = read_csv(folder / "question_set.csv")
        private = read_csv(folder / "answer_key.csv")
        private_by_id = {row["question_id"]: row for row in private}
        answer_formats = {}
        for annotation in read_annotations(folder):
            for question in annotation["questions"]:
                answer_formats[question["question_id"]] = normalize_answer_format(question.get("answer_format"))
        for public_row in public:
            qid = public_row["question_id"]
            if qid not in private_by_id:
                raise RuntimeError(f"{folder_name}/{qid}: missing answer row")
            base = {"dataset": item["slug"], "dataset_version": item["version"], **public_row}
            combined_questions.append(base)
            combined_answers.append({**base, "groundtruth": private_by_id[qid]["groundtruth"],
                                     "answer_format": answer_formats.get(qid, private_by_id[qid].get("answer_format", ""))})
    expected_questions = sum(item["questions"] for item in summary.values())
    if len(combined_questions) != expected_questions or len(combined_answers) != expected_questions:
        raise RuntimeError("Combined row count does not equal sum of per-dataset question counts")
    duplicate_suite_ids = [qid for qid, count in Counter(row["question_id"] for row in combined_questions).items() if count != 1]
    if duplicate_suite_ids:
        raise RuntimeError(f"Duplicate suite question_ids: {duplicate_suite_ids[:5]}")
    for question_row, answer_row in zip(combined_questions, combined_answers):
        for key in QUESTION_COLUMNS:
            if question_row[key] != answer_row[key]:
                raise RuntimeError(f"Question/answer drift at {question_row['question_id']}")
    write_csv(QUESTION_FILE, combined_questions, QUESTION_COLUMNS)
    write_csv(ANSWER_FILE, combined_answers, ANSWER_COLUMNS)
    return {
        "question_rows": len(combined_questions),
        "answer_rows": len(combined_answers),
        "question_answer_row_counts_match": len(combined_questions) == len(combined_answers),
    }


def main() -> None:
    folders = discovered_datasets()
    summary = current_dataset_summary(folders)
    before = existing_combined_summary(summary)
    after = rebuild(summary)
    total_images = sum(item["images"] for item in summary.values())
    total_questions = sum(item["questions"] for item in summary.values())
    expected_images = 100_000
    expected_questions = 500_000
    if total_images != expected_images or total_questions != expected_questions:
        raise RuntimeError(f"Expected {expected_images} images/{expected_questions} questions, "
                           f"found {total_images}/{total_questions}")
    report = {
        "discovered_dataset_count": len(summary),
        "before": before,
        "after": after,
        "expected_totals": {
            "images": expected_images,
            "questions": expected_questions,
            "answers": expected_questions,
            "layout": "33 datasets x 3000 images plus projectile_motion_dataset_1000 x 1000 images",
        },
        "actual_totals": {
            "images": total_images,
            "questions": total_questions,
            "answers": after["answer_rows"],
        },
        "per_dataset": summary,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Discovered datasets: {len(summary)}")
    print(f"Combined questions: {after['question_rows']}")
    print(f"Combined answers: {after['answer_rows']}")
    print(f"Images: {total_images}")
    if before.get("present"):
        print(f"Previously missing: {', '.join(before['missing_prefixes'])}")


if __name__ == "__main__":
    main()
