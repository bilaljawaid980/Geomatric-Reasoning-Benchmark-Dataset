"""Generate deterministic orthographic multi-view voxel reasoning puzzles."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(items, **_kwargs):
        return items


BACKGROUND = "#1A1A1A"
PANEL = "#23272A"
GRID = "#AEBBC1"
FILLED = "#5FAAB7"
FILLED_EDGE = "#D3E6EA"
TEXT = "#F2F2F2"
MUTED = "#AEB8BC"
ISO_EDGE = "#18282D"
ISO_COLORS = {"top": "#BFD8DC", "left": "#79AAB3", "right": "#55838D"}
AA = 2

Cube = tuple[int, int, int]
Cell = tuple[int, int]


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size * AA)
    except OSError:  # pragma: no cover
        return ImageFont.load_default()


def gravity_valid(cubes: Iterable[Cube]) -> bool:
    cube_set = set(cubes)
    return bool(cube_set) and all(z >= 0 and (z == 0 or (x, y, z - 1) in cube_set) for x, y, z in cube_set)


def cubes_from_heights(heights: dict[Cell, int]) -> set[Cube]:
    return {(x, y, z) for (x, y), height in heights.items() for z in range(height)}


def heights_from_cubes(cubes: Iterable[Cube]) -> dict[Cell, int]:
    cube_set = set(cubes)
    if not gravity_valid(cube_set):
        raise ValueError("Cubes are not gravity-supported columns")
    heights: dict[Cell, int] = {}
    for x, y, z in cube_set:
        heights[(x, y)] = max(heights.get((x, y), 0), z + 1)
    if cubes_from_heights(heights) != cube_set:
        raise ValueError("Cube columns contain gaps")
    return heights


def project_top(cubes: Iterable[Cube]) -> set[Cell]:
    return {(x, y) for x, y, _z in cubes}


def project_front(cubes: Iterable[Cube]) -> set[Cell]:
    """View along the y axis: horizontal x, vertical z."""
    return {(x, z) for x, _y, z in cubes}


def project_side(cubes: Iterable[Cube]) -> set[Cell]:
    """View along the x axis: horizontal y, vertical z."""
    return {(y, z) for _x, y, z in cubes}


def projections(cubes: Iterable[Cube]) -> tuple[set[Cell], set[Cell], set[Cell]]:
    cube_set = set(cubes)
    return project_top(cube_set), project_front(cube_set), project_side(cube_set)


def generate_valid_structure(num_cubes: int, rng: random.Random) -> set[Cube]:
    """Grow a connected footprint and then add only vertically supported cubes."""
    base_count = rng.randint(4, min(8, num_cubes))
    footprint: set[Cell] = {(0, 0)}
    while len(footprint) < base_count:
        x, y = rng.choice(sorted(footprint))
        dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        footprint.add((x + dx, y + dy))
    heights = {cell: 1 for cell in footprint}
    for _ in range(num_cubes - base_count):
        choices = [cell for cell, height in heights.items() if height < 5]
        heights[rng.choice(sorted(choices))] += 1
    cubes = cubes_from_heights(heights)
    assert len(cubes) == num_cubes and gravity_valid(cubes)
    return cubes


def _view_requirements(top: set[Cell], front: set[Cell], side: set[Cell]) -> tuple[dict[int, int], dict[int, int], dict[Cell, int]]:
    if not top or not front or not side:
        raise ValueError("All three views must be non-empty")
    front_height: dict[int, int] = {}
    for x, z in front:
        front_height[x] = max(front_height.get(x, 0), z + 1)
    side_height: dict[int, int] = {}
    for y, z in side:
        side_height[y] = max(side_height.get(y, 0), z + 1)
    for x, height in front_height.items():
        if {(x, z) for z in range(height)} - front:
            raise ValueError("Front silhouette contains a vertical gap")
    for y, height in side_height.items():
        if {(y, z) for z in range(height)} - side:
            raise ValueError("Side silhouette contains a vertical gap")
    if {x for x, _ in top} != set(front_height) or {y for _, y in top} != set(side_height):
        raise ValueError("Projection axis domains disagree")
    upper = {(x, y): min(front_height[x], side_height[y]) for x, y in top}
    return front_height, side_height, upper


def enumerate_consistent_heights(
    top: set[Cell],
    front: set[Cell],
    side: set[Cell],
    *,
    max_solutions: int | None = None,
    total: int | None = None,
) -> list[dict[Cell, int]]:
    """Enumerate gravity-valid height maps that exactly reproduce all three views."""
    front_height, side_height, upper = _view_requirements(top, front, side)
    cells = sorted(top, key=lambda cell: (-upper[cell], cell[0], cell[1]))
    remaining_x = Counter(x for x, _ in cells)
    remaining_y = Counter(y for _, y in cells)
    assigned: dict[Cell, int] = {}
    row_max: dict[int, int] = {}
    col_max: dict[int, int] = {}
    solutions: list[dict[Cell, int]] = []

    def viable(index: int, running_total: int) -> bool:
        left = len(cells) - index
        if total is not None and not (running_total + left <= total <= running_total + sum(upper[c] for c in cells[index:])):
            return False
        for x, required in front_height.items():
            current = row_max.get(x, 0)
            if current > required:
                return False
            if current < required and not any(c[0] == x and upper[c] >= required for c in cells[index:]):
                return False
        for y, required in side_height.items():
            current = col_max.get(y, 0)
            if current > required:
                return False
            if current < required and not any(c[1] == y and upper[c] >= required for c in cells[index:]):
                return False
        return True

    def search(index: int, running_total: int) -> None:
        if max_solutions is not None and len(solutions) >= max_solutions:
            return
        if not viable(index, running_total):
            return
        if index == len(cells):
            if total is not None and running_total != total:
                return
            if all(row_max.get(x, 0) == h for x, h in front_height.items()) and all(col_max.get(y, 0) == h for y, h in side_height.items()):
                solutions.append(dict(assigned))
            return
        cell = cells[index]
        x, y = cell
        old_x, old_y = row_max.get(x, 0), col_max.get(y, 0)
        remaining_x[x] -= 1
        remaining_y[y] -= 1
        for height in range(1, upper[cell] + 1):
            assigned[cell] = height
            row_max[x] = max(old_x, height)
            col_max[y] = max(old_y, height)
            search(index + 1, running_total + height)
            if max_solutions is not None and len(solutions) >= max_solutions:
                break
        assigned.pop(cell, None)
        row_max[x], col_max[y] = old_x, old_y
        remaining_x[x] += 1
        remaining_y[y] += 1

    search(0, 0)
    return solutions


def analyze_views(top: set[Cell], front: set[Cell], side: set[Cell]) -> tuple[int, bool, dict[Cell, int] | None]:
    """Return true minimum count, global uniqueness, and one alternative if present."""
    front_height, side_height, upper = _view_requirements(top, front, side)
    lower = len(top)
    upper_total = sum(upper.values())
    first_solution: dict[Cell, int] | None = None
    minimum = upper_total
    for total in range(lower, upper_total + 1):
        found = enumerate_consistent_heights(top, front, side, max_solutions=1, total=total)
        if found:
            minimum = total
            first_solution = found[0]
            break
    two = enumerate_consistent_heights(top, front, side, max_solutions=2)
    return minimum, len(two) == 1, (two[1] if len(two) > 1 else first_solution)


def matching_views(candidate: set[Cube], target_views: tuple[set[Cell], set[Cell], set[Cell]]) -> dict[str, bool]:
    actual = projections(candidate)
    return {name: actual[i] == target_views[i] for i, name in enumerate(("top", "front", "side"))}


def candidate_distractors(target: set[Cube], rng: random.Random) -> list[tuple[set[Cube], dict[str, bool]]]:
    """Produce three distinct distractors, including one matching exactly two views."""
    heights = heights_from_cubes(target)
    target_views = projections(target)
    proposals: dict[tuple[Cube, ...], tuple[set[Cube], dict[str, bool]]] = {}

    def offer(new_heights: dict[Cell, int]) -> None:
        if not new_heights or any(h < 1 or h > 5 for h in new_heights.values()):
            return
        cubes = cubes_from_heights(new_heights)
        if cubes == target or not (6 <= len(cubes) <= 12):
            return
        matches = matching_views(cubes, target_views)
        match_count = sum(matches.values())
        if 1 <= match_count <= 2:
            proposals[tuple(sorted(cubes))] = (cubes, matches)

    cells = sorted(heights)
    for cell in cells:
        for delta in (-1, 1):
            changed = dict(heights)
            changed[cell] += delta
            offer(changed)
    for source in cells:
        if heights[source] <= 1:
            continue
        for destination in cells:
            if source == destination or heights[destination] >= 5:
                continue
            changed = dict(heights)
            changed[source] -= 1
            changed[destination] += 1
            offer(changed)
    boundary = sorted({(x + dx, y + dy) for x, y in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - set(cells))
    for source in cells:
        if heights[source] != 1:
            continue
        for destination in boundary:
            changed = dict(heights)
            del changed[source]
            changed[destination] = 1
            offer(changed)

    values = list(proposals.values())
    exact_two = [item for item in values if sum(item[1].values()) == 2]
    if not exact_two:
        return []
    chosen = [rng.choice(exact_two)]
    remaining = [item for item in values if item[0] != chosen[0][0]]
    rng.shuffle(remaining)
    chosen.extend(remaining[:2])
    return chosen if len(chosen) == 3 else []


def iso_project(x: float, y: float, z: float) -> tuple[float, float]:
    return (x - y) * math.sqrt(3) / 2, (x + y) * 0.5 - z


def visible_iso_faces(cubes: set[Cube]) -> list[tuple[Cube, str, list[tuple[float, float, float]]]]:
    faces = []
    for x, y, z in cubes:
        definitions = {
            "top": ((x, y, z + 1), (x + 1, y, z + 1), (x + 1, y + 1, z + 1), (x, y + 1, z + 1)),
            "right": ((x + 1, y, z), (x + 1, y + 1, z), (x + 1, y + 1, z + 1), (x + 1, y, z + 1)),
            "left": ((x, y + 1, z), (x + 1, y + 1, z), (x + 1, y + 1, z + 1), (x, y + 1, z + 1)),
        }
        if (x, y, z + 1) not in cubes:
            faces.append(((x, y, z), "top", list(definitions["top"])))
        if (x + 1, y, z) not in cubes:
            faces.append(((x, y, z), "right", list(definitions["right"])))
        if (x, y + 1, z) not in cubes:
            faces.append(((x, y, z), "left", list(definitions["left"])))
    return sorted(faces, key=lambda item: (item[0][0] + item[0][1] + item[0][2], item[0][2], item[1]))


def draw_isometric(draw: ImageDraw.ImageDraw, cubes: set[Cube], box: tuple[int, int, int, int], label: str) -> None:
    x0, y0, x1, y1 = [v * AA for v in box]
    draw.rounded_rectangle((x0, y0, x1, y1), radius=8 * AA, fill=PANEL, outline="#59666B", width=1 * AA)
    draw.text(((x0 + x1) / 2, y0 + 5 * AA), label, font=font(14, True), fill=TEXT, anchor="ma")
    faces = visible_iso_faces(cubes)
    raw = [iso_project(*vertex) for _cube, _face, vertices in faces for vertex in vertices]
    min_x, max_x = min(x for x, _ in raw), max(x for x, _ in raw)
    min_y, max_y = min(y for _, y in raw), max(y for _, y in raw)
    usable_w = x1 - x0 - 16 * AA
    usable_h = y1 - y0 - 28 * AA
    scale = min(usable_w / max(0.5, max_x - min_x), usable_h / max(0.5, max_y - min_y))
    origin_x = (x0 + x1) / 2 - scale * (min_x + max_x) / 2
    origin_y = y0 + 25 * AA + usable_h / 2 - scale * (min_y + max_y) / 2
    for _cube, face, vertices in faces:
        points = [(origin_x + scale * px, origin_y + scale * py) for px, py in (iso_project(*v) for v in vertices)]
        draw.polygon(points, fill=ISO_COLORS[face])
        draw.line(points + [points[0]], fill=ISO_EDGE, width=max(1, AA), joint="curve")


def projection_layout(cells: set[Cell], box: tuple[int, int, int, int]) -> tuple[dict[Cell, tuple[float, float, float, float]], tuple[int, int, int, int]]:
    min_a, max_a = min(a for a, _ in cells), max(a for a, _ in cells)
    min_b, max_b = min(b for _, b in cells), max(b for _, b in cells)
    cols, rows = max_a - min_a + 1, max_b - min_b + 1
    x0, y0, x1, y1 = box
    cell_size = min((x1 - x0 - 12) / cols, (y1 - y0 - 12) / rows, 30)
    grid_w, grid_h = cols * cell_size, rows * cell_size
    left = (x0 + x1 - grid_w) / 2
    top = (y0 + y1 - grid_h) / 2
    layout = {}
    for a in range(min_a, max_a + 1):
        for b in range(min_b, max_b + 1):
            col = a - min_a
            row = max_b - b
            layout[(a, b)] = (left + col * cell_size, top + row * cell_size, left + (col + 1) * cell_size, top + (row + 1) * cell_size)
    return layout, (min_a, max_a, min_b, max_b)


def draw_projection(draw: ImageDraw.ImageDraw, cells: set[Cell], box: tuple[int, int, int, int], label: str, axis_note: str) -> None:
    x0, y0, x1, y1 = [v * AA for v in box]
    draw.rounded_rectangle((x0, y0, x1, y1), radius=8 * AA, fill=PANEL, outline="#59666B", width=1 * AA)
    draw.text(((x0 + x1) / 2, y0 + 7 * AA), label, font=font(16, True), fill=TEXT, anchor="ma")
    draw.text(((x0 + x1) / 2, y0 + 27 * AA), axis_note, font=font(9), fill=MUTED, anchor="ma")
    inner = (box[0] + 6, box[1] + 40, box[2] - 6, box[3] - 8)
    layout, _bounds = projection_layout(cells, inner)
    for cell, rect in layout.items():
        scaled = tuple(round(v * AA) for v in rect)
        draw.rectangle(scaled, fill=FILLED if cell in cells else PANEL, outline=FILLED_EDGE if cell in cells else GRID, width=1 * AA)


def render_image(path: Path, size: tuple[int, int], target: set[Cube], candidates: list[dict] | None) -> None:
    width, height = size
    image = Image.new("RGB", (width * AA, height * AA), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((width * AA / 2, 8 * AA), "ORTHOGRAPHIC MULTI-VIEW", font=font(18, True), fill=TEXT, anchor="ma")
    views = projections(target)
    gap = 10
    margin = 14
    panel_width = (width - 2 * margin - 2 * gap) // 3
    view_bottom = 215 if candidates else height - 58
    boxes = [(margin + i * (panel_width + gap), 38, margin + i * (panel_width + gap) + panel_width, view_bottom) for i in range(3)]
    labels = (("TOP VIEW", "x-y footprint"), ("FRONT VIEW", "x-z silhouette"), ("SIDE VIEW", "y-z silhouette"))
    for cells, box, (label, note) in zip(views, boxes, labels):
        draw_projection(draw, cells, box, label, note)
    if candidates:
        draw.text((width * AA / 2, 224 * AA), "Which candidate matches all three views?", font=font(12, True), fill=TEXT, anchor="ma")
        cgap = 8
        cwidth = (width - 2 * margin - 3 * cgap) // 4
        for i, candidate in enumerate(candidates):
            box = (margin + i * (cwidth + cgap), 244, margin + i * (cwidth + cgap) + cwidth, height - 12)
            draw_isometric(draw, {tuple(c) for c in candidate["cubes"]}, box, candidate["choice_label"])
    else:
        draw.text((width * AA / 2, (height - 40) * AA), "Reconstruct the supported voxel structure from all three silhouettes.", font=font(11), fill=MUTED, anchor="ma")
    image.resize((width, height), Image.Resampling.LANCZOS).save(path, "PNG")


def cells_json(cells: set[Cell]) -> list[list[int]]:
    return [list(cell) for cell in sorted(cells)]


def cubes_json(cubes: set[Cube]) -> list[list[int]]:
    return [list(cube) for cube in sorted(cubes)]


def add_cube_view_changes(cubes: set[Cube]) -> tuple[list[int], list[str]]:
    heights = heights_from_cubes(cubes)
    tallest = min((cell for cell, h in heights.items() if h == max(heights.values())))
    x, y = tallest
    new_cube = (x, y, heights[tallest])
    before = projections(cubes)
    after = projections(cubes | {new_cube})
    changed = [name for i, name in enumerate(("top", "front", "side")) if before[i] != after[i]]
    return [x, y], changed


def make_questions(record: dict, rng: random.Random) -> list[dict]:
    iid = record["id"]
    counts = record["view_filled_counts"]
    questions = [
        {
            "question_id": f"{iid}_q1",
            "question_text": "How many unit cells are filled in the top view?",
            "question_type": "top_view_filled_count",
            "ground_truth": str(counts["top"]),
            "answer_format": "numeric",
            "difficulty_level": 1,
        },
        {
            "question_id": f"{iid}_q2",
            "question_text": "Based on the three views shown, what is the minimum possible number of cubes in a gravity-supported 3D structure? Answer with a number in curly brackets.",
            "question_type": "minimum_possible_cube_count",
            "ground_truth": str(record["minimum_possible_cube_count"]),
            "answer_format": "numeric",
            "difficulty_level": 2,
        },
    ]
    largest = max(counts.values())
    largest_views = [name for name in ("top", "front", "side") if counts[name] == largest]
    level3_pool = []
    if len(largest_views) == 1:
        level3_pool.append("largest_view")
    if record["has_candidate_panel"]:
        level3_pool.append("candidate_consistency")
    choice = rng.choice(level3_pool)
    if choice == "largest_view":
        q3 = {
            "question_id": f"{iid}_q3",
            "question_text": "Which view (top, front, or side) shows the largest filled area (most filled cells)?",
            "question_type": "largest_filled_view",
            "ground_truth": largest_views[0],
            "answer_format": "view_name",
            "difficulty_level": 3,
        }
    else:
        q3 = {
            "question_id": f"{iid}_q3",
            "question_text": "Which candidate structure (A, B, C, or D) is consistent with all three views shown? Answer with the letter.",
            "question_type": "candidate_consistent_all_views",
            "ground_truth": record["correct_answer_choice"],
            "answer_format": "choice_letter",
            "difficulty_level": 3,
        }
    questions.append(q3)

    level4_pool = ["uniqueness", "add_cube"]
    exact_two = []
    if record["has_candidate_panel"]:
        exact_two = [c for c in record["candidates"] if not c["matches_all_3_views"] and sum(c["view_matches"].values()) == 2]
        if exact_two:
            level4_pool.append("failed_view")
    choice = rng.choice(level4_pool)
    if choice == "uniqueness":
        q4 = {
            "question_id": f"{iid}_q4",
            "question_text": "Do these three views uniquely determine the gravity-supported 3D structure, or could a different arrangement of cubes produce the exact same three views? Answer 'unique' or 'not unique'.",
            "question_type": "unique_determination",
            "ground_truth": "unique" if record["is_uniquely_determined"] else "not unique",
            "answer_format": "unique_or_not_unique",
            "difficulty_level": 4,
        }
    elif choice == "failed_view":
        candidate = rng.choice(exact_two)
        failed = [name for name, matches in candidate["view_matches"].items() if not matches]
        q4 = {
            "question_id": f"{iid}_q4",
            "question_text": f"Candidate {candidate['choice_label']} matches two of the three views but not the third. Which view does it fail to match: top, front, or side?",
            "question_type": "candidate_failed_view",
            "reference_choice": candidate["choice_label"],
            "ground_truth": failed[0],
            "answer_format": "view_name",
            "difficulty_level": 4,
        }
    else:
        changed = record["add_cube_changed_views"]
        q4 = {
            "question_id": f"{iid}_q4",
            "question_text": "If one cube were added directly on top of a tallest column in the structure, which view or views would change? Answer using top, front, and/or side.",
            "question_type": "add_above_tallest_changed_views",
            "ground_truth": " and ".join(changed),
            "answer_format": "view_names",
            "difficulty_level": 4,
        }
    questions.append(q4)
    return questions


def generate_one(index: int, images_dir: Path) -> dict:
    rng = random.Random(index)
    has_panel = index % 2 == 0
    for _attempt in range(500):
        target = generate_valid_structure(rng.randint(6, 12), rng)
        top, front, side = projections(target)
        view_counts = {"top": len(top), "front": len(front), "side": len(side)}
        largest_unique = list(view_counts.values()).count(max(view_counts.values())) == 1
        if not has_panel and not largest_unique:
            continue
        distractors = candidate_distractors(target, rng) if has_panel else []
        if has_panel and len(distractors) != 3:
            continue
        break
    else:
        raise RuntimeError(f"Could not generate valid puzzle for seed {index}")

    minimum_count, unique, _alternative = analyze_views(top, front, side)
    target_same_count_solutions = enumerate_consistent_heights(top, front, side, max_solutions=2, total=len(target))
    size = (rng.randint(600, 650), rng.randint(470, 500))
    iid = f"orthographic_{index:04d}"
    candidates = None
    correct_choice = None
    if has_panel:
        raw_candidates = [(target, {"top": True, "front": True, "side": True})] + distractors
        rng.shuffle(raw_candidates)
        candidates = []
        for label, (cubes, matches) in zip("ABCD", raw_candidates):
            candidates.append({
                "choice_label": label,
                "cubes": cubes_json(cubes),
                "view_matches": matches,
                "matches_all_3_views": all(matches.values()),
            })
            if cubes == target:
                correct_choice = label
        assert sum(c["matches_all_3_views"] for c in candidates) == 1
    tallest_cell, changed_views = add_cube_view_changes(target)
    complexity = (len(target) - 6) / 6
    ambiguity = 0 if unique else 1
    difficulty = round(min(1.0, 0.3 * complexity + 0.25 * ambiguity + 0.25 * has_panel + 0.2 * (max(view_counts.values()) / 12)), 4)
    record = {
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": list(size),
        "seed": index,
        "difficulty_score": difficulty,
        "target_cubes": cubes_json(target),
        "total_cube_count": len(target),
        "minimum_possible_cube_count": minimum_count,
        "top_view_cells": cells_json(top),
        "front_view_cells": cells_json(front),
        "side_view_cells": cells_json(side),
        "view_filled_counts": view_counts,
        "has_candidate_panel": has_panel,
        "candidates": candidates or [],
        "correct_answer_choice": correct_choice,
        "is_uniquely_determined": unique,
        "is_uniquely_determined_same_count": len(target_same_count_solutions) == 1,
        "uniqueness_scope": "all gravity-supported structures consistent with the three silhouettes",
        "tallest_column_xy": tallest_cell,
        "add_cube_changed_views": changed_views,
    }
    record["questions"] = make_questions(record, rng)
    render_image(images_dir / f"{iid}.png", size, target, candidates)
    return record


def generate_dataset(count: int, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations = output_dir / "annotations.jsonl"
    with annotations.open("w", encoding="utf-8", newline="\n") as handle:
        for index in tqdm(range(1, count + 1), desc="Generating orthographic puzzles"):
            handle.write(json.dumps(generate_one(index, images_dir), sort_keys=True, separators=(",", ":")) + "\n")
    print(f"Generated {count} images and {annotations}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3000)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--sample", action="store_true", help="Generate five images for manual review")
    args = parser.parse_args()
    generate_dataset(5 if args.sample else args.n, args.output_dir)


if __name__ == "__main__":
    main()
