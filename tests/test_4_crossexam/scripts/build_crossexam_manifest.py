"""Build a deterministic 2,000-image open-ended cross-examination manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from crossexam_common import (
    FAMILIES, checkable_claims, claims_from_key_row, json_list, parse_models, read_csv,
    stable_int,
)

COLUMNS = [
    "row_id", "model", "domain", "stem", "image_path", "question_id", "prompt",
    "ground_truth", "acceptance_set", "checkable_claims",
]


def domain_sources(dataset_root: Path, domain: str) -> tuple[Path, Path]:
    matches = sorted(dataset_root.glob(f"{domain}_dataset_*/open_questions.csv"))
    if len(matches) != 1:
        raise ValueError(f"Expected one dataset directory for {domain}, found {len(matches)}")
    questions = matches[0]
    key = questions.with_name("open_answer_key.csv")
    if not key.is_file():
        raise FileNotFoundError(key)
    return questions, key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=REPO_ROOT / "Dataset")
    parser.add_argument("--output", type=Path, default=TEST_ROOT / "plan/crossexam_manifest.csv")
    parser.add_argument("--sample-output", type=Path, default=TEST_ROOT / "plan/crossexam_sample.csv")
    parser.add_argument("--sample-size", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--models", help="Comma-separated keys; default is the fixed six-model panel")
    args = parser.parse_args()

    models = parse_models(args.models)
    if args.sample_size < len(FAMILIES):
        raise ValueError("--sample-size must be at least the number of domains")

    sources: dict[str, dict[str, dict[str, str]]] = {}
    vocab: dict[str, dict[str, list[str]]] = {}
    dataset_dirs: dict[str, Path] = {}
    for domain in sorted(FAMILIES):
        questions_path, key_path = domain_sources(args.dataset_root, domain)
        dataset_dirs[domain] = questions_path.parent
        questions = read_csv(questions_path).set_index("image")
        key = read_csv(key_path).set_index("image")
        if not questions.index.is_unique:
            raise ValueError(f"Duplicate image keys in {questions_path}")
        if not key.index.is_unique:
            raise ValueError(f"Duplicate image keys in {key_path}")
        joined = questions[["question_id", "prompt"]].join(
            key.drop(columns=["question_id"], errors="ignore"), how="inner", validate="one_to_one"
        )
        sources[domain] = {index: row.to_dict() for index, row in joined.iterrows()}
        field_values: dict[str, set[str]] = defaultdict(set)
        for row in sources[domain].values():
            for field, value in claims_from_key_row(row).items():
                field_values[field].add(value)
        vocab[domain] = {field: sorted(values) for field, values in field_values.items()}

    domains = sorted(sources)
    base, remainder = divmod(args.sample_size, len(domains))
    extra_domains = set(sorted(domains, key=lambda value: (stable_int(args.seed, value), value))[:remainder])
    sample: list[dict[str, str]] = []
    for domain in domains:
        quota = base + int(domain in extra_domains)
        available = sorted(
            sources[domain], key=lambda image: (stable_int(args.seed, domain, image), image)
        )
        if len(available) < quota:
            raise ValueError(f"{domain} has only {len(available)} open images; needs {quota}")
        relative_dir = dataset_dirs[domain].relative_to(REPO_ROOT)
        for image in available[:quota]:
            sample.append({
                "domain": domain,
                "stem": Path(image).stem,
                "image": image,
                "image_path": (relative_dir / "images" / image).as_posix(),
            })
    if len(sample) != args.sample_size:
        raise AssertionError(f"Sampling produced {len(sample)} rows, expected {args.sample_size}")

    output_rows: list[dict[str, str]] = []
    for item in sample:
        domain, image = item["domain"], item["image"]
        if image not in sources[domain]:
            raise ValueError(f"No open question/key for {domain}/{image}")
        source = sources[domain][image]
        accepted = json_list(source["acceptance_set"])
        if not accepted:
            raise ValueError(f"Empty acceptance set for {domain}/{image}")
        claims = claims_from_key_row(source)
        ground_truth = accepted[0]
        if set(claims) != set(part.split("=", 1)[0].strip() for part in ground_truth.split(";")):
            raise ValueError(f"Acceptance fields do not match key columns for {domain}/{image}")
        for model in models:
            output_rows.append({
                "row_id": f"{model}:{domain}:{item['stem']}",
                "model": model,
                "domain": domain,
                "stem": item["stem"],
                "image_path": item["image_path"],
                "question_id": source["question_id"],
                "prompt": source["prompt"],
                "ground_truth": ground_truth,
                "acceptance_set": source["acceptance_set"],
                "checkable_claims": checkable_claims(source, vocab[domain]),
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.sample_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["domain", "stem", "image", "image_path"])
        writer.writeheader()
        writer.writerows(sample)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Models: {', '.join(models)}")
    print(f"Sample images per model: {len(sample):,}")
    print(f"Per-domain sample range: {base:,}-{base + int(remainder > 0):,}")
    print(f"Round-1 manifest rows: {len(output_rows):,}")


if __name__ == "__main__":
    main()
