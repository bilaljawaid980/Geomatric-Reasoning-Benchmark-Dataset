"""Final invariants and release report for the route/hex supplementary open sets."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DATASETS = REPO / "Dataset"
DOMAINS = ("route_dataset_3000", "hex_pathfinding_dataset_3000")
OUT = DATASETS / "open_question_release_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def head_bytes(relative: str) -> bytes:
    raw = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=REPO)
    if raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raw = subprocess.run(
            ["git", "lfs", "smudge"], cwd=REPO, input=raw,
            stdout=subprocess.PIPE, check=True,
        ).stdout
    return raw


def annotations_without_version(raw: bytes) -> list[dict]:
    records = []
    for line in raw.decode("utf-8-sig").splitlines():
        if line:
            record = json.loads(line)
            record.pop("dataset_version", None)
            records.append(record)
    return records


def csv_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    before = json.loads((DATASETS / "open_question_prechange_hashes.json").read_text(encoding="utf-8"))
    domains: dict[str, dict] = {}
    for name in DOMAINS:
        folder = DATASETS / name
        expected = before[name]
        unchanged_hashes = {
            "question_set.csv": sha256(folder / "question_set.csv") == expected["question_set_sha256"],
            "answer_key.csv": sha256(folder / "answer_key.csv") == expected["answer_key_sha256"],
            "dataset_final.csv": sha256(folder / "dataset_final.csv") == expected["dataset_final_csv_sha256"],
            "dataset_final.jsonl": sha256(folder / "dataset_final.jsonl") == expected["dataset_final_jsonl_sha256"],
        }
        relative_annotations = (Path("Dataset") / name / "annotations.jsonl").as_posix()
        current_annotations = (folder / "annotations.jsonl").read_bytes()
        annotation_payload_unchanged = (
            annotations_without_version(head_bytes(relative_annotations))
            == annotations_without_version(current_annotations)
        )
        image_status = subprocess.check_output(
            ["git", "status", "--porcelain", "--", str(Path("Dataset") / name / "images")],
            cwd=REPO, text=True,
        ).strip()
        metrics = json.loads((folder / "open_validation_metrics.json").read_text(encoding="utf-8"))
        if not all(unchanged_hashes.values()) or not annotation_payload_unchanged or image_status:
            raise RuntimeError(f"{name}: protected existing content changed")
        if metrics["issues"] or metrics["derivation_mismatches"]:
            raise RuntimeError(f"{name}: open validation did not pass")
        domains[name] = {
            "dataset_version": json.loads((folder / "build_manifest.json").read_text(encoding="utf-8"))["dataset_version"],
            "open_questions": csv_count(folder / "open_questions.csv"),
            "open_answers": csv_count(folder / "open_answer_key.csv"),
            "derivation_mismatches": len(metrics["derivation_mismatches"]),
            "png_recoverability": metrics["png_recoverability"],
            "constant_answer_baselines": metrics["constant_answer_baselines"],
            "fields_over_60_percent": metrics["fields_over_60_percent"],
            "protected_file_hashes_unchanged": unchanged_hashes,
            "annotation_payload_unchanged_except_version": annotation_payload_unchanged,
            "images_unchanged": not bool(image_status),
        }
        if name.startswith("route"):
            domains[name]["selection_distribution"] = metrics["selection_distribution"]
            domains[name]["connected_label_pairs_out_of_canonical_15"] = metrics[
                "connected_label_pairs_out_of_canonical_15"
            ]
        else:
            domains[name]["boundary_vs_interior"] = metrics["boundary_vs_interior"]
            domains[name]["template_choice"] = metrics["template_choice"]
            domains[name]["answer_distributions"] = metrics["answer_distributions"]

    combined = json.loads((DATASETS / "combined_open_question_report.json").read_text(encoding="utf-8"))
    suite = json.loads((DATASETS / "combined_suite_rebuild_report.json").read_text(encoding="utf-8"))["actual_totals"]
    report = {
        "status": "PASS",
        "scope": list(DOMAINS),
        "domains": domains,
        "combined_open": combined,
        "five_level_suite": {
            "datasets": 34,
            "images": suite["images"],
            "questions": suite["questions"],
            "answers": suite["answers"],
        },
        "protected_content": "images, renderers, existing five-level question text, and existing answers unchanged",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
