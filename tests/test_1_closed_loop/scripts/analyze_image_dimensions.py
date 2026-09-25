"""Read-only image-dimension and empty-margin audit for the GRIP suite."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = REPO_ROOT / "Dataset"
DIMENSION_SAMPLE_LIMIT = 200
MARGIN_SAMPLES_PER_DOMAIN = 3
BACKGROUND_THRESHOLD = 12


@dataclass(frozen=True)
class MarginResult:
    domain: str
    image: str
    width: int
    height: int
    bbox: tuple[int, int, int, int] | None
    content_percent: float

    @property
    def wasted_percent(self) -> float:
        return 100.0 - self.content_percent


def stable_seed(*parts: object) -> int:
    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def discover_domains(root: Path) -> list[Path]:
    domains = sorted(
        path
        for path in root.iterdir()
        if path.is_dir()
        and (path / "build_manifest.json").is_file()
        and (path / "images").is_dir()
    )
    if len(domains) != 34:
        raise ValueError(f"Expected 34 dataset domains, discovered {len(domains)}")
    return domains


def sample_files(files: list[Path], count: int, *seed_parts: object) -> list[Path]:
    if len(files) <= count:
        return list(files)
    return sorted(random.Random(stable_seed(*seed_parts)).sample(files, count))


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def modal_background(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    colors = rgb.getcolors(maxcolors=rgb.width * rgb.height)
    if colors is None:
        raise ValueError(f"Could not determine exact modal color for {image.filename}")
    return max(colors, key=lambda item: item[0])[1]


def measure_margin(domain: str, path: Path) -> MarginResult:
    with Image.open(path) as source:
        image = source.convert("RGB")
        width, height = image.size
        background = np.asarray(modal_background(image), dtype=np.int16)
        pixels = np.asarray(image, dtype=np.int16)
    mask = np.any(np.abs(pixels - background) > BACKGROUND_THRESHOLD, axis=2)
    y_coords, x_coords = np.nonzero(mask)
    if not x_coords.size:
        bbox = None
        content_percent = 0.0
    else:
        x0 = int(x_coords.min())
        y0 = int(y_coords.min())
        x1 = int(x_coords.max()) + 1
        y1 = int(y_coords.max()) + 1
        bbox = (x0, y0, x1, y1)
        content_percent = 100.0 * (x1 - x0) * (y1 - y0) / (width * height)
    return MarginResult(domain, path.name, width, height, bbox, content_percent)


def print_table(headers: list[str], rows: list[list[object]]) -> None:
    rendered = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rendered))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rendered:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def main() -> None:
    domains = discover_domains(DATASET_ROOT)
    overall_sizes: Counter[tuple[int, int]] = Counter()
    domain_rows: list[dict[str, object]] = []
    margin_rows: list[MarginResult] = []

    for position, domain_path in enumerate(domains, start=1):
        files = sorted((domain_path / "images").glob("*.png"))
        if not files:
            raise ValueError(f"No PNG files found in {domain_path / 'images'}")

        # Header-only reads provide exact suite totals without decoding 100,000 images.
        all_sizes = [image_size(path) for path in files]
        overall_sizes.update(all_sizes)
        total_pixels = sum(width * height for width, height in all_sizes)

        dimension_sample = sample_files(
            files, DIMENSION_SAMPLE_LIMIT, domain_path.name, "dimensions"
        )
        sampled_sizes = [image_size(path) for path in dimension_sample]
        sampled_distribution = Counter(sampled_sizes)
        modal_size, modal_count = sampled_distribution.most_common(1)[0]
        widths = [size[0] for size in sampled_sizes]
        heights = [size[1] for size in sampled_sizes]

        domain_rows.append(
            {
                "domain": domain_path.name,
                "files": len(files),
                "sample": len(dimension_sample),
                "modal": modal_size,
                "modal_count": modal_count,
                "varies": len(sampled_distribution) > 1,
                "range": (min(widths), min(heights), max(widths), max(heights)),
                "total_pixels": total_pixels,
            }
        )

        for path in sample_files(
            files, MARGIN_SAMPLES_PER_DOMAIN, domain_path.name, "margins"
        ):
            margin_rows.append(measure_margin(domain_path.name, path))
        print(
            f"Scanned {position:02d}/{len(domains)}: {domain_path.name} "
            f"({len(files):,} PNGs)",
            flush=True,
        )

    total_images = sum(overall_sizes.values())
    total_pixels = sum(width * height * count for (width, height), count in overall_sizes.items())
    if total_images != 100_000:
        raise ValueError(f"Expected 100,000 PNGs, found {total_images:,}")

    for row in domain_rows:
        row["share"] = 100.0 * int(row["total_pixels"]) / total_pixels

    print("\nPER-DOMAIN CANVAS AUDIT — largest modal canvas first")
    domain_rows.sort(
        key=lambda row: (
            int(row["modal"][0]) * int(row["modal"][1]),
            int(row["total_pixels"]),
        ),
        reverse=True,
    )
    print_table(
        [
            "Domain",
            "PNGs",
            "Sample",
            "Modal WxH",
            "Modal px",
            "Mode n",
            "Varies?",
            "Sample range",
            "Total pixels",
            "Suite %",
        ],
        [
            [
                row["domain"],
                f"{int(row['files']):,}",
                row["sample"],
                f"{row['modal'][0]}x{row['modal'][1]}",
                f"{row['modal'][0] * row['modal'][1]:,}",
                row["modal_count"],
                "yes" if row["varies"] else "no",
                (
                    f"{row['range'][0]}-{row['range'][2]} x "
                    f"{row['range'][1]}-{row['range'][3]}"
                ),
                f"{int(row['total_pixels']):,}",
                f"{float(row['share']):.2f}",
            ]
            for row in domain_rows
        ],
    )

    print("\nOVERALL IMAGE-SIZE DISTRIBUTION — most common first")
    print_table(
        ["Dimensions", "Pixels/image", "Images", "Image %", "Total pixels"],
        [
            [
                f"{width}x{height}",
                f"{width * height:,}",
                f"{count:,}",
                f"{100.0 * count / total_images:.2f}",
                f"{width * height * count:,}",
            ]
            for (width, height), count in overall_sizes.most_common()
        ],
    )

    print("\nMARGIN AUDIT — worst wasted bounding-box margin first")
    margin_rows.sort(key=lambda row: row.wasted_percent, reverse=True)
    print_table(
        ["Domain", "Image", "Canvas", "Content bbox (exclusive)", "BBox WxH", "Used %", "Wasted %"],
        [
            [
                row.domain,
                row.image,
                f"{row.width}x{row.height}",
                "none" if row.bbox is None else str(row.bbox),
                (
                    "0x0"
                    if row.bbox is None
                    else f"{row.bbox[2] - row.bbox[0]}x{row.bbox[3] - row.bbox[1]}"
                ),
                f"{row.content_percent:.2f}",
                f"{row.wasted_percent:.2f}",
            ]
            for row in margin_rows
        ],
    )

    print("\nSUITE TOTALS")
    print(f"Domains: {len(domains):,}")
    print(f"Images: {total_images:,}")
    print(f"Total pixels: {total_pixels:,}")
    print("Largest domain shares:")
    for row in sorted(domain_rows, key=lambda item: int(item["total_pixels"]), reverse=True)[:10]:
        print(
            f"  {row['domain']}: {int(row['total_pixels']):,} pixels "
            f"({float(row['share']):.2f}%)"
        )


if __name__ == "__main__":
    main()
