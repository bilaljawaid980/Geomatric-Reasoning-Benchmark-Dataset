"""Create reproducible closed-loop accuracy and reusable core-subset manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grip_eval.config import (
    ESTIMATED_TOKENS_PER_QUERY,
    MODELS,
    PRICE_TABLE_USD_PER_MILLION,
)

CLOSED_ID = re.compile(r"^(?P<stem>.+)_q(?P<level>[1-5])$")
OPEN_ID = re.compile(r"_open_q\d+$")
OUTPUT_COLUMNS = [
    "row_id",
    "domain",
    "stem",
    "image_path",
    "question_id",
    "level",
    "prompt",
    "ground_truth",
    "answer_format",
    "tolerance",
    "in_core_subset",
]


def stable_seed(*parts: object) -> int:
    """Return a process-independent integer seed for the supplied identifiers."""

    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def domain_name(directory: Path) -> str:
    """Remove the dataset-size suffix from a GRIP domain directory name."""

    return re.sub(r"_dataset_(?:1000|3000)$", "", directory.name)


def json_maybe(value: Any) -> Any:
    """Decode a JSON cell when possible, preserving ordinary strings."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def compact_json(value: Any) -> str:
    """Serialize manifest metadata deterministically."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def annotation_question_metadata(path: Path) -> dict[str, dict[str, Any]]:
    """Index per-question formats and accepted answers from annotations.jsonl."""

    metadata: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {error}") from error
            for question in item.get("questions", []):
                question_id = str(question.get("question_id", ""))
                if question_id:
                    metadata[question_id] = question
    return metadata


def normalized_format(answer: dict[str, Any], metadata: dict[str, Any]) -> str:
    """Preserve source format and fold any acceptance set into its JSON form."""

    raw = answer.get("answer_format", "") or metadata.get("answer_format", "")
    parsed = json_maybe(raw)
    accepted = json_maybe(answer.get("valid_answers", "")) or metadata.get(
        "valid_answers", []
    )
    if accepted and not isinstance(accepted, list):
        accepted = [accepted]
    if isinstance(parsed, dict):
        result = dict(parsed)
        if accepted:
            result["acceptance_set"] = accepted
        return compact_json(result)
    if accepted:
        return compact_json({"type": str(parsed or "exact"), "acceptance_set": accepted})
    return str(parsed or "exact")


def normalized_tolerance(answer_format: str) -> str:
    """Extract numeric tolerance fields into the dedicated manifest column."""

    parsed = json_maybe(answer_format)
    if not isinstance(parsed, dict):
        return ""
    tolerance = {
        key: parsed[key]
        for key in ("absolute_tolerance", "tolerance", "tolerance_percent")
        if key in parsed
    }
    return compact_json(tolerance) if tolerance else ""


def load_domain_rows(dataset_dir: Path, repository_root: Path) -> list[dict[str, Any]]:
    """Join one domain's public questions to its private answer metadata."""

    questions_path = dataset_dir / "question_set.csv"
    answers_path = dataset_dir / "answer_key.csv"
    annotations_path = dataset_dir / "annotations.jsonl"
    for required in (questions_path, answers_path, annotations_path):
        if not required.is_file():
            raise FileNotFoundError(f"Discovered dataset is unreadable; missing {required}")

    questions = pd.read_csv(questions_path, dtype=str, keep_default_na=False)
    answers = pd.read_csv(answers_path, dtype=str, keep_default_na=False)
    expected_public = ["question_id", "task", "image", "prompt"]
    if list(questions.columns) != expected_public:
        raise ValueError(f"Unexpected public schema in {questions_path}: {list(questions.columns)}")
    for required_column in ("question_id", "groundtruth"):
        if required_column not in answers.columns:
            raise ValueError(f"{answers_path} lacks required column {required_column!r}")
    if questions["question_id"].duplicated().any() or answers["question_id"].duplicated().any():
        raise ValueError(f"Duplicate question IDs in {dataset_dir}")

    answer_map = answers.set_index("question_id").to_dict("index")
    metadata_map = annotation_question_metadata(annotations_path)
    domain = domain_name(dataset_dir)
    rows: list[dict[str, Any]] = []
    for question in questions.to_dict("records"):
        question_id = question["question_id"]
        if OPEN_ID.search(question_id):
            continue
        match = CLOSED_ID.fullmatch(question_id)
        if not match:
            raise ValueError(f"Unrecognized closed question ID: {question_id}")
        if question_id not in answer_map:
            raise ValueError(f"No answer row resolves {question_id}")
        answer = answer_map[question_id]
        metadata = metadata_map.get(question_id, {})
        image_file = dataset_dir / "images" / question["image"]
        if not image_file.is_file():
            raise FileNotFoundError(f"Question image does not exist: {image_file}")
        image_path = image_file.relative_to(repository_root).as_posix()
        answer_format = normalized_format(answer, metadata)
        rows.append(
            {
                "domain": domain,
                "stem": match.group("stem"),
                "image": question["image"],
                "image_path": image_path,
                "question_id": question_id,
                "level": int(match.group("level")),
                "prompt": question["prompt"],
                "ground_truth": answer["groundtruth"],
                "answer_format": answer_format,
                "tolerance": normalized_tolerance(answer_format),
            }
        )
    expected_closed = sum(
        not OPEN_ID.search(question_id) for question_id in questions["question_id"]
    )
    if len(rows) != expected_closed:
        raise ValueError(f"Closed-question row count drift in {questions_path}")
    return rows


def choose_core(
    domain: str,
    rows: list[dict[str, Any]],
    target: int,
) -> list[str]:
    """Choose reproducible core stems that are present at all five levels."""

    levels_by_stem: dict[str, set[int]] = {}
    for row in rows:
        levels_by_stem.setdefault(row["stem"], set()).add(row["level"])
    complete = {stem for stem, levels in levels_by_stem.items() if levels == set(range(1, 6))}
    if len(complete) < target:
        raise ValueError(f"{domain} has only {len(complete)} images present at all five levels")
    return sorted(random.Random(stable_seed(domain, "core")).sample(sorted(complete), target))


def estimate_model_cost(model_key: str, query_count: int) -> float | None:
    """Estimate one model's run cost from editable token and price assumptions."""

    prices = PRICE_TABLE_USD_PER_MILLION[model_key]
    if prices["input"] is None or prices["output"] is None:
        return None
    reasoning_price = prices["reasoning"]
    if reasoning_price is None:
        reasoning_price = prices["output"]
    per_query = (
        ESTIMATED_TOKENS_PER_QUERY["input"] * prices["input"]
        + ESTIMATED_TOKENS_PER_QUERY["output"] * prices["output"]
        + int(
            MODELS[model_key].get(
                "estimated_reasoning_tokens",
                ESTIMATED_TOKENS_PER_QUERY["reasoning"],
            )
        )
        * reasoning_price
    ) / 1_000_000
    return query_count * per_query


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Write a UTF-8 CSV with a fixed column order."""

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_plan(dataset_root: Path, output_dir: Path, per_level: int, core_size: int) -> None:
    """Discover domains, sample levels independently, and write all plan files."""

    dataset_root = dataset_root.resolve()
    repository_root = dataset_root.parent
    discovered = sorted(
        path.parent for path in dataset_root.glob("*_dataset_*/build_manifest.json")
    )
    if not discovered:
        raise FileNotFoundError(f"No dataset directories discovered under {dataset_root}")

    accuracy_rows: list[dict[str, Any]] = []
    core_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    shortfalls: list[str] = []

    for dataset_dir in discovered:
        rows = load_domain_rows(dataset_dir, repository_root)
        domain = domain_name(dataset_dir)
        by_level = {level: [] for level in range(1, 6)}
        for row in rows:
            by_level[row["level"]].append(row)

        core_stems = choose_core(domain, rows, core_size)
        core_set = set(core_stems)
        sampled_by_level: dict[int, list[dict[str, Any]]] = {}
        for level in range(1, 6):
            candidates = sorted(by_level[level], key=lambda row: row["question_id"])
            if len({row["stem"] for row in candidates}) != len(candidates):
                raise ValueError(f"{domain} L{level} contains multiple questions for one image")
            core_rows_for_level = [row for row in candidates if row["stem"] in core_set]
            if len(core_rows_for_level) != core_size:
                raise ValueError(
                    f"{domain} L{level} resolves {len(core_rows_for_level)}/{core_size} core images"
                )
            remaining = [row for row in candidates if row["stem"] not in core_set]
            additional_needed = per_level - core_size
            additional_count = min(additional_needed, len(remaining))
            additional = random.Random(stable_seed(domain, level)).sample(
                remaining, additional_count
            )
            sampled_by_level[level] = core_rows_for_level + additional
            if len(sampled_by_level[level]) < per_level:
                shortfalls.append(
                    f"{domain} L{level}: {len(sampled_by_level[level])}/{per_level}"
                )

        sampled_ids = {
            row["question_id"]
            for selected in sampled_by_level.values()
            for row in selected
        }
        manifest_ids = sampled_ids

        for level in range(1, 6):
            for row in sampled_by_level[level]:
                accuracy_rows.append(
                    {key: row[key] for key in ("domain", "level", "question_id", "image", "image_path")}
                )
        row_by_stem = {row["stem"]: row for row in rows}
        for stem in core_stems:
            row = row_by_stem[stem]
            core_rows.append(
                {key: row[key] for key in ("domain", "stem", "image", "image_path")}
            )
        for row in rows:
            if row["question_id"] not in manifest_ids:
                continue
            manifest_rows.append(
                {
                    "row_id": f"{domain}:{row['question_id']}",
                    **{key: row[key] for key in OUTPUT_COLUMNS if key in row},
                    "in_core_subset": row["stem"] in core_set,
                }
            )

        unique_accuracy = {
            row["stem"] for selected in sampled_by_level.values() for row in selected
        }
        summary_rows.append(
            {
                "domain": domain,
                **{f"level_{level}_images": len(sampled_by_level[level]) for level in range(1, 6)},
                "unique_accuracy_images": len(unique_accuracy),
                "core_images": len(core_stems),
                "core_from_sample_intersection": len(core_stems),
                "core_fallback_images": 0,
                "manifest_rows": len(manifest_ids),
            }
        )

    accuracy_rows.sort(key=lambda row: (row["domain"], row["level"], row["question_id"]))
    core_rows.sort(key=lambda row: (row["domain"], row["stem"]))
    manifest_rows.sort(key=lambda row: (row["domain"], row["stem"], row["level"]))
    summary_rows.sort(key=lambda row: row["domain"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "part1_accuracy_sample.csv",
        accuracy_rows,
        ["domain", "level", "question_id", "image", "image_path"],
    )
    write_csv(
        output_dir / "core_subset.csv",
        core_rows,
        ["domain", "stem", "image", "image_path"],
    )
    write_csv(output_dir / "closed_loop_manifest.csv", manifest_rows, OUTPUT_COLUMNS)
    write_csv(output_dir / "sample_summary.csv", summary_rows, list(summary_rows[0]))

    total_selected = len(accuracy_rows)
    unique_selected = len({(row["domain"], row["image"]) for row in accuracy_rows})
    query_count = len(manifest_rows)
    print(f"Domains discovered: {len(discovered)}")
    print(f"Total images sampled across levels: {total_selected:,}")
    print(f"Total unique sampled images: {unique_selected:,}")
    print(f"Total manifest rows (queries per model): {query_count:,}")
    print(f"Total queries across all {len(MODELS)} models: {query_count * len(MODELS):,}")
    print("\nPer-domain sample summary:")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print("\nLevel availability shortfalls:")
    print("none" if not shortfalls else "\n".join(shortfalls))
    print("\nEstimated cost using grip_eval/config.py:")
    configured_total = 0.0
    complete = True
    for model_key in MODELS:
        estimate = estimate_model_cost(model_key, query_count)
        if estimate is None:
            complete = False
            print(f"  {model_key}: NOT CONFIGURED")
        else:
            configured_total += estimate
            print(f"  {model_key}: ${estimate:,.4f}")
    print(f"  total: ${configured_total:,.4f}" if complete else "  total: NOT CONFIGURED")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=REPO_ROOT / "Dataset")
    parser.add_argument("--output-dir", type=Path, default=TEST_ROOT / "plan")
    parser.add_argument("--per-level", type=int, default=50)
    parser.add_argument("--core-size", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    args = parse_args()
    if args.per_level < 1 or args.core_size < 1:
        raise ValueError("--per-level and --core-size must be positive")
    if args.core_size > args.per_level:
        raise ValueError("--core-size cannot exceed --per-level")
    build_plan(args.dataset_root, args.output_dir, args.per_level, args.core_size)


if __name__ == "__main__":
    main()
