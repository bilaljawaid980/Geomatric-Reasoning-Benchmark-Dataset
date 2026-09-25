"""Create deterministic monochrome-grain copies of the GRIP core images.

This script never changes source images. It writes PNG copies for the paid
noise levels so every evaluated model receives identical pixels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGMAS = (15, 25, 40)


def add_grain(img: Image.Image, sigma: int, seed: int) -> Image.Image:
    """Add one monochrome Gaussian-noise field to all three RGB channels."""

    rng = np.random.default_rng(seed)
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    n = np.repeat(rng.normal(0, sigma, a.shape[:2] + (1,)), 3, axis=2)
    return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))


def filename_seed(filename: str) -> int:
    """Return a process-independent seed derived only from the filename."""

    digest = hashlib.sha256(filename.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def parse_sigmas(value: str) -> tuple[int, ...]:
    """Parse a comma-separated list of unique, positive noise levels."""

    sigmas = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not sigmas or any(sigma <= 0 for sigma in sigmas):
        raise ValueError("Grain-image sigmas must be positive integers")
    if len(sigmas) != len(set(sigmas)):
        raise ValueError("Duplicate sigma values are not allowed")
    return sigmas


def load_core(path: Path) -> list[dict[str, str]]:
    """Load and validate the fixed 680-image core subset."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"domain", "stem", "image", "image_path"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain columns {sorted(required)}")
        rows = list(reader)
    keys = [(row["domain"], row["stem"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate domain/stem rows in {path}")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["domain"]] = counts.get(row["domain"], 0) + 1
    if len(rows) != 680 or len(counts) != 34 or set(counts.values()) != {20}:
        raise ValueError(
            f"Expected 680 core images (20 x 34); found {len(rows)} rows with "
            f"per-domain counts {counts}"
        )
    return sorted(rows, key=lambda row: (row["domain"], row["stem"]))


def generate(args: argparse.Namespace) -> None:
    """Write deterministic PNG copies for each requested positive sigma."""

    repository_root = args.repository_root.resolve()
    rows = load_core(args.core_subset)
    sigmas = parse_sigmas(args.sigmas)
    written = 0
    existing = 0
    for row in rows:
        source = repository_root / row["image_path"]
        if not source.is_file():
            raise FileNotFoundError(f"Core image not found: {source}")
        if source.suffix.lower() != ".png":
            raise ValueError(f"Core image is not PNG: {source}")
        seed = filename_seed(row["image"])
        with Image.open(source) as opened:
            original_size = opened.size
            for sigma in sigmas:
                destination = (
                    args.output_root / f"sigma_{sigma}" / row["domain"] / row["image"]
                )
                if destination.exists() and not args.overwrite:
                    existing += 1
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                noised = add_grain(opened, sigma, seed)
                if noised.size != original_size:
                    raise AssertionError(f"Image dimensions changed for {source}")
                noised.save(destination, format="PNG")
                written += 1
    print(f"Core images: {len(rows):,}")
    print(f"Sigmas generated: {', '.join(map(str, sigmas))}")
    print(f"PNG files written: {written:,}")
    print(f"Existing files left unchanged: {existing:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-subset", type=Path, default=REPO_ROOT / "tests" / "test_1_closed_loop" / "plan" / "core_subset.csv")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-root", type=Path, default=TEST_ROOT / "artifacts" / "grain_images")
    parser.add_argument(
        "--sigmas", default=",".join(map(str, DEFAULT_SIGMAS)), help="Positive sigmas"
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    generate(parse_args())


if __name__ == "__main__":
    main()
