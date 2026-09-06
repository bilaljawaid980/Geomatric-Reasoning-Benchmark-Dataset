"""Independently validate HOME-neighborhood open questions and PNG evidence."""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
ANSWER_COLUMNS = [
    "question_id", "image", "target", "home_on_boundary", "neighbour_count",
    "holes_touching", "walkable_touching", "hole_directions",
]
DIRECTIONS = [
    ("upper-left", (0, -1)), ("upper-right", (1, -1)), ("left", (-1, 0)),
    ("right", (1, 0)), ("lower-left", (-1, 1)), ("lower-right", (0, 1)),
]
PALETTE = {"white": (255, 253, 249), "black": (36, 42, 46), "grey": (157, 163, 168)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def derive(record: dict) -> dict:
    tiles = {tuple(tile["coordinate"]): tile["color"] for tile in record["all_tiles"]}
    home = tuple(record["home_coordinate"])
    neighbours = []
    for name, (dq, dr) in DIRECTIONS:
        coordinate = (home[0] + dq, home[1] + dr)
        if coordinate in tiles:
            neighbours.append((name, coordinate, tiles[coordinate]))
    holes = [item for item in neighbours if item[2] == "grey"]
    return {
        "home_on_boundary": len(neighbours) < 6,
        "neighbour_count": len(neighbours),
        "holes_touching": len(holes),
        "walkable_touching": len(neighbours) - len(holes),
        "hole_directions": [name for name, _ in DIRECTIONS if any(item[0] == name for item in holes)],
        "neighbours": neighbours,
    }


def pixel_geometry(canvas: int, radius: int) -> tuple[float, tuple[float, float]]:
    size = min((canvas - 72) / (math.sqrt(3) * (2 * radius + 1)), (canvas - 112) / (3 * radius + 2))
    return size, (canvas / 2, canvas / 2 - 22)


def to_pixel(coordinate: tuple[int, int], size: float, center: tuple[float, float]) -> tuple[float, float]:
    q, r = coordinate
    return center[0] + size * math.sqrt(3) * (q + r / 2), center[1] + size * 1.5 * r


def recover_class(image: Image.Image, coordinate: tuple[int, int], size: float, center: tuple[float, float]) -> str:
    x0, y0 = to_pixel(coordinate, size, center)
    samples = []
    for angle in range(0, 360, 30):
        radians = math.radians(angle)
        x, y = round(x0 + .65 * size * math.cos(radians)), round(y0 + .65 * size * math.sin(radians))
        samples.append(image.getpixel((x, y)))
    votes = Counter(min(PALETTE, key=lambda name: sum((pixel[index] - PALETTE[name][index]) ** 2 for index in range(3))) for pixel in samples)
    return votes.most_common(1)[0][0]


def distribution(values) -> dict[str, int]:
    return dict(sorted(Counter(json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value) for value in values).items()))


def baseline(counts: dict[str, int]) -> float:
    return max(counts.values()) / sum(counts.values()) if counts else 0.0


def main() -> None:
    records = [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    public = read_csv(ROOT / "open_questions.csv")
    answers = read_csv(ROOT / "open_answer_key.csv")
    annotations = [json.loads(line) for line in (ROOT / "open_annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues, derivation_mismatches = [], []
    png_pass = 0
    fields = ["home_on_boundary", "neighbour_count", "holes_touching", "walkable_touching", "hole_directions"]
    values = {key: [] for key in fields}
    if len(records) != len(public) or len(public) != len(answers) or len(answers) != len(annotations):
        issues.append("row-count mismatch among source/open files")
    if public and list(public[0]) != PUBLIC_COLUMNS:
        issues.append(f"public columns {list(public[0])} != {PUBLIC_COLUMNS}")
    if answers and list(answers[0]) != ANSWER_COLUMNS:
        issues.append(f"answer columns {list(answers[0])} != {ANSWER_COLUMNS}")
    permitted = {name for name, _ in DIRECTIONS}
    for position, (record, question, answer, annotation) in enumerate(zip(records, public, answers, annotations), 1):
        expected = derive(record)
        parsed = {
            "home_on_boundary": answer["home_on_boundary"].lower() == "true",
            "neighbour_count": int(answer["neighbour_count"]),
            "holes_touching": int(answer["holes_touching"]),
            "walkable_touching": int(answer["walkable_touching"]),
            "hole_directions": json.loads(answer["hole_directions"]),
        }
        for key in fields:
            if parsed[key] != expected[key]:
                derivation_mismatches.append(f"{record['id']}/{key}")
            values[key].append(expected[key])
        qid = f"{record['id']}_open_q1"
        if question["question_id"] != qid or answer["question_id"] != qid or annotation["question_id"] != qid:
            issues.append(f"{record['id']}: question_id mismatch")
        if question["image"] != Path(record["image_path"]).name or answer["image"] != question["image"]:
            issues.append(f"{record['id']}: image mismatch")
        prompt = question["prompt"]
        if re.search(r"\(\s*-?\d+\s*,\s*-?\d+\s*\)", prompt) or any(word in prompt.lower() for word in ["axial", "coordinate", "q,r", "q, r"]):
            issues.append(f"{record['id']}: prompt contains a coordinate scheme")
        if "start" in prompt.lower() or "outlined in blue" in prompt.lower():
            issues.append(f"{record['id']}: prompt restates Level 2 START-neighbor task")
        if any(prompt.strip() == old["question_text"].strip() for old in record["questions"]):
            issues.append(f"{record['id']}: exact existing-question paraphrase")
        directions_in_prompt = {name for name in permitted if name in prompt.lower()}
        if directions_in_prompt != permitted or not set(expected["hole_directions"]) <= permitted:
            issues.append(f"{record['id']}: invalid or incomplete direction vocabulary")
        if annotation.get("derivation", {}).get("home_coordinate") != record["home_coordinate"]:
            issues.append(f"{record['id']}: annotation derivation mismatch")
        with Image.open(ROOT / record["image_path"]) as source:
            image = source.convert("RGB")
            image.load()
        size, center = pixel_geometry(record["canvas_size"][0], record["grid_radius"])
        png_ok = image.size == tuple(record["canvas_size"])
        for _direction, coordinate, stored_color in expected["neighbours"]:
            recovered = recover_class(image, coordinate, size, center)
            wanted = "grey" if stored_color == "grey" else ("black" if stored_color == "black" else "white")
            if recovered != wanted:
                png_ok = False
        if png_ok:
            png_pass += 1
        else:
            issues.append(f"{record['id']}: PNG HOME-neighborhood recovery")
        if position % 500 == 0:
            print(f"Validated {position}/{len(records)}", flush=True)
    if derivation_mismatches:
        issues.append(f"independent derivation mismatches: {len(derivation_mismatches)}")
    distributions = {key: distribution(field_values) for key, field_values in values.items()}
    baselines = {key: baseline(counts) for key, counts in distributions.items()}
    metrics = {
        "question_count": len(public),
        "template_choice": "retained neighbour_count because HOME is boundary in 1,606 items and interior in 1,394",
        "boundary_vs_interior": {"boundary": values["home_on_boundary"].count(True), "interior": values["home_on_boundary"].count(False)},
        "answer_distributions": distributions,
        "constant_answer_baselines": baselines,
        "fields_over_60_percent": {key: value for key, value in baselines.items() if value > .60},
        "derivation_mismatches": derivation_mismatches,
        "png_recoverability": {"passed": png_pass, "total": len(records)},
        "public_columns": PUBLIC_COLUMNS,
        "permitted_directions": sorted(permitted),
        "no_coordinate_prompts": not any("coordinate scheme" in issue for issue in issues),
        "no_answer_leakage": not any("leaks" in issue for issue in issues),
        "no_existing_question_paraphrase": not any("paraphrase" in issue or "Level 2" in issue for issue in issues),
        "issues": issues,
    }
    (ROOT / "open_validation_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "HEX PATHFINDING OPEN-QUESTION VALIDATION REPORT", "=" * 48,
        f"Questions: {len(public)}", f"Derivation mismatches: {len(derivation_mismatches)}",
        f"PNG-recoverable items: {png_pass}/{len(records)}", f"Boundary/interior: {metrics['boundary_vs_interior']}",
        f"Constant baselines: {baselines}", f"Fields over 60%: {metrics['fields_over_60_percent']}",
        f"Issues: {len(issues)}", *(issues if issues else ["None"]), f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    (ROOT / "open_validation_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
