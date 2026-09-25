"""Create one clean-to-grain comparison strip per domain for manual review."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

from make_grain_images import DEFAULT_SIGMAS, load_core, parse_sigmas

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
GRAIN_IMAGE_RELATIVE_ROOT = Path("tests/test_2_grain_robustness/artifacts/grain_images")
STRIP_RELATIVE_ROOT = Path("tests/test_2_grain_robustness/artifacts/readability_strips")

CSV_COLUMNS = ["domain", "sigma", "stem", "image", "strip_path", "readable", "notes"]


def selection_key(domain: str, stem: str) -> bytes:
    """Return a deterministic ordering key for representative selection."""

    return hashlib.sha256(f"{domain}\x1f{stem}\x1freadability".encode("utf-8")).digest()


def existing_decisions(path: Path) -> dict[tuple[str, int], tuple[str, str]]:
    """Preserve hand-entered decisions when strips are regenerated."""

    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(CSV_COLUMNS).issubset(reader.fieldnames):
            raise ValueError(f"Unexpected verification schema in {path}")
        return {
            (row["domain"], int(row["sigma"])): (row["readable"], row["notes"])
            for row in reader
        }


def make_strip(images: list[tuple[int, Path]], destination: Path) -> None:
    """Place unscaled PNG panels side by side with a small sigma label header."""

    loaded: list[tuple[int, Image.Image]] = []
    for sigma, path in images:
        if not path.is_file():
            raise FileNotFoundError(f"Readability source missing: {path}")
        with Image.open(path) as opened:
            loaded.append((sigma, opened.convert("RGB").copy()))
    sizes = {image.size for _, image in loaded}
    if len(sizes) != 1:
        raise ValueError(f"Panel dimensions differ: {images}")
    width, height = next(iter(sizes))
    header = 32
    strip = Image.new("RGB", (width * len(loaded), height + header), "white")
    draw = ImageDraw.Draw(strip)
    for index, (sigma, image) in enumerate(loaded):
        x = index * width
        strip.paste(image, (x, header))
        draw.text((x + 8, 9), f"sigma = {sigma}", fill="black")
    destination.parent.mkdir(parents=True, exist_ok=True)
    strip.save(destination, format="PNG")


def build(args: argparse.Namespace) -> None:
    """Write 34 strips and a hand-editable domain/sigma verification CSV."""

    repository_root = args.repository_root.resolve()
    sigmas = (0,) + parse_sigmas(args.sigmas)
    core = load_core(args.core_subset)
    by_domain: dict[str, list[dict[str, str]]] = {}
    for row in core:
        by_domain.setdefault(row["domain"], []).append(row)
    selected = {
        domain: min(rows, key=lambda row: selection_key(domain, row["stem"]))
        for domain, rows in by_domain.items()
    }
    previous = existing_decisions(args.verification_csv)
    csv_rows: list[dict[str, object]] = []
    for domain, row in sorted(selected.items()):
        panels: list[tuple[int, Path]] = []
        for sigma in sigmas:
            path = (
                repository_root / row["image_path"]
                if sigma == 0
                else repository_root
                / GRAIN_IMAGE_RELATIVE_ROOT
                / f"sigma_{sigma}"
                / domain
                / row["image"]
            )
            panels.append((sigma, path))
        strip_relative = STRIP_RELATIVE_ROOT / f"{domain}.png"
        make_strip(panels, repository_root / strip_relative)
        for sigma in sigmas:
            readable, notes = previous.get((domain, sigma), ("", ""))
            csv_rows.append(
                {
                    "domain": domain,
                    "sigma": sigma,
                    "stem": row["stem"],
                    "image": row["image"],
                    "strip_path": strip_relative.as_posix(),
                    "readable": readable,
                    "notes": notes,
                }
            )
    args.verification_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.verification_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Readability strips written: {len(selected)}")
    print(f"Verification rows written: {len(csv_rows)}")
    print(
        f"Fill {args.verification_csv} column 'readable' with yes or no for every row."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-subset", type=Path, default=REPO_ROOT / "tests" / "test_1_closed_loop" / "plan" / "core_subset.csv")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--sigmas", default=",".join(map(str, DEFAULT_SIGMAS)))
    parser.add_argument(
        "--verification-csv",
        type=Path,
        default=TEST_ROOT / "plan" / "grain_readability.csv",
    )
    return parser.parse_args()


def main() -> None:
    build(parse_args())


if __name__ == "__main__":
    main()
