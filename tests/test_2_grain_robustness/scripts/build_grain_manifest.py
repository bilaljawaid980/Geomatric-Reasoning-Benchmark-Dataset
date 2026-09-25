"""Build the 10,200-query paid grain manifest from the fixed core subset."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from make_grain_images import DEFAULT_SIGMAS, load_core, parse_sigmas

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
GRAIN_IMAGE_RELATIVE_ROOT = Path("tests/test_2_grain_robustness/artifacts/grain_images")

OUTPUT_COLUMNS = [
    "row_id",
    "domain",
    "stem",
    "sigma",
    "image_path",
    "question_id",
    "level",
    "prompt",
    "ground_truth",
    "answer_format",
]


def load_closed_manifest(path: Path) -> list[dict[str, str]]:
    """Load the closed-loop manifest without rewriting prompt or answer cells."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "domain",
            "stem",
            "question_id",
            "level",
            "prompt",
            "ground_truth",
            "answer_format",
            "in_core_subset",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain columns {sorted(required)}")
        return list(reader)


def build(args: argparse.Namespace) -> None:
    """Join each core image to all five unchanged closed-loop questions."""

    repository_root = args.repository_root.resolve()
    core = load_core(args.core_subset)
    sigmas = parse_sigmas(args.sigmas)
    closed = load_closed_manifest(args.closed_manifest)
    core_lookup = {(row["domain"], row["stem"]): row for row in core}
    questions: dict[tuple[str, str], list[dict[str, str]]] = {
        key: [] for key in core_lookup
    }
    for row in closed:
        key = (row["domain"], row["stem"])
        if key in questions:
            questions[key].append(row)

    output: list[dict[str, object]] = []
    for key, core_row in sorted(core_lookup.items()):
        rows = sorted(questions[key], key=lambda row: int(row["level"]))
        levels = [int(row["level"]) for row in rows]
        if levels != [1, 2, 3, 4, 5]:
            raise ValueError(f"Core image {key} does not resolve exactly L1-L5: {levels}")
        for sigma in sigmas:
            relative_image = GRAIN_IMAGE_RELATIVE_ROOT / f"sigma_{sigma}" / key[0] / core_row["image"]
            absolute_image = repository_root / relative_image
            if not absolute_image.is_file():
                raise FileNotFoundError(
                    f"Missing grain image {absolute_image}; run make_grain_images.py first"
                )
            for row in rows:
                output.append(
                    {
                        "row_id": f"{key[0]}:{row['question_id']}:grain_sigma{sigma}",
                        "domain": key[0],
                        "stem": key[1],
                        "sigma": sigma,
                        "image_path": relative_image.as_posix(),
                        "question_id": row["question_id"],
                        "level": int(row["level"]),
                        "prompt": row["prompt"],
                        "ground_truth": row["ground_truth"],
                        "answer_format": row["answer_format"],
                    }
                )

    row_ids = [str(row["row_id"]) for row in output]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Duplicate row_id values generated")
    expected_per_sigma = len(core) * 5
    counts = Counter(int(row["sigma"]) for row in output)
    if any(counts[sigma] != expected_per_sigma for sigma in sigmas):
        raise ValueError(f"Unexpected per-sigma row counts: {dict(counts)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output)
    for sigma in sigmas:
        print(f"sigma={sigma}: {counts[sigma]:,} rows")
    print(f"Total paid grain queries per model: {len(output):,}")
    print(f"sigma=0: {expected_per_sigma:,} rows reused from closed-loop results")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-subset", type=Path, default=REPO_ROOT / "tests" / "test_1_closed_loop" / "plan" / "core_subset.csv")
    parser.add_argument(
        "--closed-manifest", type=Path, default=REPO_ROOT / "tests" / "test_1_closed_loop" / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=TEST_ROOT / "plan" / "grain_manifest.csv")
    parser.add_argument("--sigmas", default=",".join(map(str, DEFAULT_SIGMAS)))
    return parser.parse_args()


def main() -> None:
    build(parse_args())


if __name__ == "__main__":
    main()
