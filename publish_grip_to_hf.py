"""Build, publish, and verify the private GRIP-Benchmark Hugging Face dataset.

Run this script from a normal terminal. It reads HF_TOKEN/hf_token from the
project .env without printing it and publishes one unified `train` split.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
from collections import Counter
from pathlib import Path


PROJECT = Path(r"C:\Users\bilal\OneDrive\Desktop\geomstry").resolve()
DATASET_ROOT = PROJECT / "Dataset"
REPO_ID = "bilaljawaid980/GRIP-Benchmark"
CATEGORIES = {
    "route": "route_dataset_3000",
    "nested_squares": "nested_squares_dataset_3000",
    "cube_structure": "cube_structure_dataset_3000",
    "line_intersection": "line_intersection_dataset_3000",
    "overlap_circles": "overlap_circles_dataset_3000",
    "cube_net": "cube_net_dataset_3000",
    "shadow_inference": "shadow_inference_dataset_3000",
    "impossible_object": "impossible_object_dataset_3000",
    "polyhedron": "polyhedron_dataset_3000",
    "depth_height": "depth_height_dataset_3000",
    "embedded_figures": "embedded_figures_dataset_3000",
    "rotation_matching": "rotation_matching_dataset_3000",
    "combination": "combination_dataset_3000",
    "combination3d": "combination3d_dataset_3000",
    "fold_punch": "fold_punch_dataset_3000",
    "symmetry_pattern": "symmetry_pattern_dataset_3000",
    "occluded_pattern": "occluded_pattern_dataset_3000",
    "angle_estimation": "angle_estimation_dataset_3000",
    "coordinate_geometry": "coordinate_geometry_dataset_3000",
    "orthographic": "orthographic_dataset_3000",
    "rpm": "rpm_dataset_3000",
    "surface_topology": "surface_topology_dataset_3000",
    "gear_train": "gear_train_dataset_3000",
    "physical_stability": "physical_stability_dataset_3000",
    "free_body_diagram": "fbd_dataset_3000",
    "clock_reading": "clock_reading_dataset_3000",
    "gauge_reading": "gauge_reading_dataset_3000",
    "nested_triangles": "nested_triangles_dataset_3000",
    "nested_hexagons": "nested_hexagons_dataset_3000",
    "optical_illusion": "optical_illusion_dataset_3000",
    "compass_bearing": "compass_bearing_dataset_3000",
    "hex_pathfinding": "hex_pathfinding_dataset_3000",
    "laser_mirror": "laser_mirror_dataset_3000",
    "projectile_motion": "projectile_motion_dataset_1000",
}

EXPECTED_IMAGES = {category: (1000 if category == "projectile_motion" else 3000) for category in CATEGORIES}
EXPECTED_ROWS = {category: count * 5 for category, count in EXPECTED_IMAGES.items()}
TOTAL_IMAGES = sum(EXPECTED_IMAGES.values())
TOTAL_ROWS = sum(EXPECTED_ROWS.values())


def read_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("hf_token")
    env_path = PROJECT / ".env"
    if not token and env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().lower() in {"hf_token", "huggingface_token"}:
                token = value.strip().strip('"').strip("'")
                break
    if not token:
        raise RuntimeError("No HF_TOKEN/hf_token found in the environment or project .env")
    return token


def protect_secrets() -> None:
    path = PROJECT / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = [entry for entry in (".env", ".hf_cache/", "hf_upload_verification/") if entry not in current.splitlines()]
    if additions:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write("\n".join(additions) + "\n")


def local_audit() -> None:
    actual = sorted(p.name for p in DATASET_ROOT.iterdir() if p.is_dir() and re.fullmatch(r".+_dataset_(?:1000|3000)", p.name))
    expected = sorted(CATEGORIES.values())
    if actual != expected:
        raise RuntimeError(f"Expected exactly {len(CATEGORIES)} dataset folders. Missing/extra: expected={expected}, actual={actual}")
    if any("jigsaw" in name.lower() for name in actual):
        raise RuntimeError("Jigsaw must not be published")
    for category, folder_name in CATEGORIES.items():
        folder = DATASET_ROOT / folder_name
        csv_path = folder / "dataset_final.csv"
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"task", "image", "prompt", "groundtruth", "metadata"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise RuntimeError(f"{category}: dataset_final.csv is missing required columns: {reader.fieldnames}")
            rows = list(reader)
        expected_rows = EXPECTED_ROWS[category]
        expected_images = EXPECTED_IMAGES[category]
        if len(rows) != expected_rows:
            raise RuntimeError(f"{category}: expected {expected_rows:,} rows, got {len(rows):,}")
        image_counts = Counter(row["image"] for row in rows)
        image_names = set(image_counts)
        if len(image_names) != expected_images or set(image_counts.values()) != {5}:
            raise RuntimeError(f"{category}: each of {expected_images:,} image names must appear exactly five times")
        missing = [name for name in image_names if not (folder / "images" / name).is_file()]
        if missing:
            raise RuntimeError(f"{category}: {len(missing)} referenced images are missing")
        print(f"AUDIT {category}: {expected_images:,} images / {expected_rows:,} rows")


def row_generator():
    for category, folder_name in CATEGORIES.items():
        folder = DATASET_ROOT / folder_name
        per_image = Counter()
        with (folder / "dataset_final.csv").open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                filename = row["image"]
                per_image[filename] += 1
                match = re.search(r"(\d+)(?=\.[^.]+$)", filename)
                if not match:
                    raise RuntimeError(f"Cannot derive numeric image id from {filename}")
                image_number = int(match.group(1))
                q_number = per_image[filename]
                yield {
                    "id": f"{category}_{image_number:04d}_q{q_number}",
                    # Explicit bytes make every row self-contained in Parquet.
                    "image": {"bytes": (folder / "images" / filename).read_bytes(), "path": filename},
                    "category": category,
                    "question": row["prompt"],
                    "ground_truth": str(row["groundtruth"]),
                    "metadata": row["metadata"],
                }


def dataset_card() -> str:
    project_readme = (PROJECT / "README.md").read_text(encoding="utf-8")
    summary_start = project_readme.find("## 2. Dataset summary")
    summary_end = project_readme.find("## 3. Shared methodology")
    summary = project_readme[summary_start:summary_end].strip() if summary_start >= 0 and summary_end > summary_start else ""
    summary = re.sub(r"\[([^\]]+)\]\(Dataset/[^)]+\)", r"\1", summary)
    method_start = project_readme.find("## 3. Shared methodology")
    method_end = project_readme.find("## 4. Transparency")
    methodology = project_readme[method_start:method_end].strip() if method_start >= 0 and method_end > method_start else ""
    return f'''---
license: mit
task_categories:
- visual-question-answering
language:
- en
tags:
- geometry
- spatial-reasoning
- visual-reasoning
- synthetic
- benchmark
- vqa
pretty_name: GRIP-Benchmark
size_categories:
- 100K<n<1M
---

# GRIP-Benchmark

GRIP-Benchmark is a fully synthetic, programmatically generated and independently validated visual geometry, spatial-reasoning, and physical-reasoning suite. The current release contains **{len(CATEGORIES)} categories**, **{TOTAL_IMAGES:,} unique images**, and **{TOTAL_ROWS:,} image-question rows**. Every image is paired with five questions ordered from direct perception through extrapolative/counterfactual reasoning.

The repository provides data and ground truth only. It does not include model inference, scoring, or an evaluation harness.

{summary}

{methodology}

## Dataset Structure

The Hub release uses one unified `train` split with {TOTAL_ROWS:,} rows and the following schema:

| Field | Type | Description |
|---|---|---|
| `id` | string | Globally unique identifier such as `route_0001_q1` |
| `image` | Image | Embedded image bytes; the dataset is self-contained |
| `category` | string | One of the {len(CATEGORIES)} benchmark categories |
| `question` | string | Question prompt |
| `ground_truth` | string | Validated answer |
| `metadata` | string | Compact JSON metadata retained from the source dataset |

Example (image omitted from the textual representation):

```json
{{
  "id": "route_0001_q1",
  "category": "route",
  "question": "How many distinct colored routes are visible in this image?",
  "ground_truth": "7",
  "metadata": "{{\\"difficulty_score\\":0.42,\\"num_routes\\":7}}"
}}
```

Each unique image appears in five rows with different IDs, questions, and answers but identical embedded image content.

## Loading

```python
from datasets import load_dataset
dataset = load_dataset("{REPO_ID}", split="train")
```

## Validation and limitations

Ground truth is independently re-derived from stored scene geometry or structured metadata by category-specific validators. Known limitations include synthetic rather than photographic imagery, bounded shape/rule vocabularies, and category-specific procedural distributions. These data should be treated as a diagnostic benchmark, not as a substitute for real-world spatial reasoning evaluation.

## Related Work

- [GIQ: Benchmarking 3D Geometric Reasoning of Vision Foundation Models](https://arxiv.org/abs/2506.08194)
- [Pathfinder / Long Range Arena](https://arxiv.org/abs/2011.04006)
- [GeoMeter: Probing Depth and Height Perception of Large Visual-Language Models](https://arxiv.org/abs/2408.11748)
- [Spatial-DISE: A Unified Benchmark for Evaluating Spatial Reasoning in Vision-Language Models](https://arxiv.org/abs/2510.13394)
- [CAPTURe: Evaluating Spatial Reasoning in Vision Language Models via Occluded Object Counting](https://arxiv.org/abs/2504.15485)

## License

MIT. See the repository license and individual related-work citations for details.
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true", help="Validate all local inputs without uploading")
    args = parser.parse_args()
    try:
        from datasets import Dataset, Features, Image as HFImage, Value, load_dataset
        from huggingface_hub import HfApi, login
    except ImportError as exc:
        raise SystemExit("Install dependencies first: python -m pip install -U huggingface_hub datasets pillow") from exc

    token = read_token()
    protect_secrets()
    local_audit()
    if args.audit_only:
        print(f"LOCAL AUDIT VERIFIED: {len(CATEGORIES)} categories, {TOTAL_IMAGES:,} images, {TOTAL_ROWS:,} rows")
        return
    login(token=token, add_to_git_credential=False)
    api = HfApi(token=token)
    identity = api.whoami(token=token)
    print(f"Authenticated Hugging Face account: {identity.get('name', '<unknown>')}")

    features = Features({
        "id": Value("string"), "image": HFImage(), "category": Value("string"),
        "question": Value("string"), "ground_truth": Value("string"), "metadata": Value("string"),
    })
    cache = PROJECT / ".hf_cache"
    print(f"Building {TOTAL_ROWS:,}-row Arrow dataset incrementally...")
    dataset = Dataset.from_generator(row_generator, features=features, cache_dir=str(cache))
    if len(dataset) != TOTAL_ROWS:
        raise RuntimeError(f"Built row count is {len(dataset)}, expected {TOTAL_ROWS:,}")
    counts = Counter(dataset["category"])
    if set(counts) != set(CATEGORIES) or any(counts[key] != EXPECTED_ROWS[key] for key in CATEGORIES):
        raise RuntimeError(f"Built category distribution is invalid: {counts}")

    # README.md is the only dataset card recognized by the Hub.  It is maintained
    # in the repository so publishing cannot create a second, conflicting card.
    card_path = PROJECT / "README.md"
    card = card_path.read_text(encoding="utf-8")
    print("\n===== DATASET CARD =====\n")
    print(card)
    print("===== END DATASET CARD =====\n")

    dataset.push_to_hub(
        REPO_ID, split="train", private=True, token=token, max_shard_size="500MB",
        commit_message=f"Update GRIP-Benchmark: {len(CATEGORIES)} categories and {TOTAL_ROWS:,} questions",
    )
    api.upload_file(
        path_or_fileobj=str(card_path), path_in_repo="README.md", repo_id=REPO_ID,
        repo_type="dataset", token=token, commit_message="Add GRIP-Benchmark dataset card",
    )

    verify_dir = PROJECT / "hf_upload_verification"
    verify_dir.mkdir(exist_ok=True)
    print("Reloading the private dataset from the Hub for verification...")
    remote = load_dataset(REPO_ID, split="train", token=token, cache_dir=str(verify_dir / "cache"))
    if len(remote) != TOTAL_ROWS:
        raise RuntimeError(f"Remote row count is {len(remote)}, expected {TOTAL_ROWS:,}")
    remote_counts = Counter(remote["category"])
    if set(remote_counts) != set(CATEGORIES) or any(remote_counts[key] != EXPECTED_ROWS[key] for key in CATEGORIES):
        raise RuntimeError(f"Remote category distribution invalid: {remote_counts}")
    indices = random.Random(20260818).sample(range(len(remote)), 3)
    for index in indices:
        row = remote[index]
        print(json.dumps({key: row[key] for key in ("id", "category", "question", "ground_truth")}, ensure_ascii=False))
    sample_path = verify_dir / "verification_sample.png"
    remote[indices[0]]["image"].save(sample_path)

    total_bytes = 0
    for item in api.list_repo_tree(REPO_ID, repo_type="dataset", recursive=True, expand=True, token=token):
        size = getattr(item, "size", None)
        if size: total_bytes += size
    print("\nUPLOAD VERIFIED")
    print(f"Remote rows: {TOTAL_ROWS}")
    print(f"Categories: {len(CATEGORIES)} (33 at 15,000 rows; projectile_motion at 5,000 rows)")
    print(f"Hub repository size: {total_bytes / (1024**3):.2f} GiB")
    print(f"Downloaded image verification sample: {sample_path}")
    print(f"Repository: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
