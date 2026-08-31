"""Independently validate orthographic dataset geometry, labels, and rendered view cells."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


FILLED_RGB = (95, 170, 183)
EMPTY_RGB = (35, 39, 42)


def supported(cubes):
    cubes = set(cubes)
    return bool(cubes) and all(z >= 0 and (z == 0 or (x, y, z - 1) in cubes) for x, y, z in cubes)


def derive_views(cubes):
    cubes = set(cubes)
    return (
        {(x, y) for x, y, _ in cubes},
        {(x, z) for x, _, z in cubes},
        {(y, z) for _, y, z in cubes},
    )


def requirements(top, front, side):
    fx = {x: max(z for xx, z in front if xx == x) + 1 for x, _ in top}
    sy = {y: max(z for yy, z in side if yy == y) + 1 for _, y in top}
    upper = {(x, y): min(fx[x], sy[y]) for x, y in top}
    return fx, sy, upper


def solutions(top, front, side, limit=None, wanted_total=None):
    fx, sy, upper = requirements(top, front, side)
    cells = sorted(top, key=lambda c: (-upper[c], c))
    found = []
    values = {}

    def search(index, running):
        if limit is not None and len(found) >= limit:
            return
        remaining = cells[index:]
        if wanted_total is not None and not (running + len(remaining) <= wanted_total <= running + sum(upper[c] for c in remaining)):
            return
        row_now = {x: max((values.get(c, 0) for c in cells[:index] if c[0] == x), default=0) for x in fx}
        col_now = {y: max((values.get(c, 0) for c in cells[:index] if c[1] == y), default=0) for y in sy}
        if any(row_now[x] < fx[x] and not any(c[0] == x and upper[c] == fx[x] for c in remaining) for x in fx):
            return
        if any(col_now[y] < sy[y] and not any(c[1] == y and upper[c] == sy[y] for c in remaining) for y in sy):
            return
        if index == len(cells):
            if wanted_total is not None and running != wanted_total:
                return
            if all(row_now[x] == fx[x] for x in fx) and all(col_now[y] == sy[y] for y in sy):
                found.append(dict(values))
            return
        cell = cells[index]
        for height in range(1, upper[cell] + 1):
            values[cell] = height
            search(index + 1, running + height)
            if limit is not None and len(found) >= limit:
                break
        values.pop(cell, None)

    search(0, 0)
    return found


def independent_analysis(top, front, side):
    _fx, _sy, upper = requirements(top, front, side)
    minimum = None
    for total in range(len(top), sum(upper.values()) + 1):
        if solutions(top, front, side, limit=1, wanted_total=total):
            minimum = total
            break
    first_two = solutions(top, front, side, limit=2)
    return minimum, len(first_two) == 1


def layout(cells, box):
    min_a, max_a = min(a for a, _ in cells), max(a for a, _ in cells)
    min_b, max_b = min(b for _, b in cells), max(b for _, b in cells)
    cols, rows = max_a - min_a + 1, max_b - min_b + 1
    x0, y0, x1, y1 = box
    size = min((x1 - x0 - 12) / cols, (y1 - y0 - 12) / rows, 30)
    left = (x0 + x1 - cols * size) / 2
    top_px = (y0 + y1 - rows * size) / 2
    return {
        (a, b): (left + (a - min_a + 0.5) * size, top_px + (max_b - b + 0.5) * size)
        for a in range(min_a, max_a + 1)
        for b in range(min_b, max_b + 1)
    }


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def png_views_match(path, size, expected_views, has_candidates):
    image = Image.open(path).convert("RGB")
    if image.size != tuple(size):
        return [f"PNG size {image.size} != {tuple(size)}"]
    width, height = size
    gap, margin = 10, 14
    panel_width = (width - 2 * margin - 2 * gap) // 3
    view_bottom = 215 if has_candidates else height - 58
    boxes = [(margin + i * (panel_width + gap) + 6, 78, margin + i * (panel_width + gap) + panel_width - 6, view_bottom - 8) for i in range(3)]
    issues = []
    for view_name, cells, box in zip(("top", "front", "side"), expected_views, boxes):
        for cell, (x, y) in layout(cells, box).items():
            pixel = image.getpixel((round(x), round(y)))
            appears_filled = distance(pixel, FILLED_RGB) < distance(pixel, EMPTY_RGB)
            if appears_filled != (cell in cells):
                issues.append(f"PNG {view_name} cell {cell} rendered={'filled' if appears_filled else 'empty'}")
                if len(issues) >= 8:
                    return issues
    return issues


def answer_for(question, record, views, minimum, unique):
    qtype = question["question_type"]
    counts = dict(zip(("top", "front", "side"), map(len, views)))
    if qtype == "top_view_filled_count":
        return str(counts["top"])
    if qtype == "minimum_possible_cube_count":
        return str(minimum)
    if qtype == "largest_filled_view":
        maximum = max(counts.values())
        winners = [name for name in ("top", "front", "side") if counts[name] == maximum]
        return winners[0] if len(winners) == 1 else "AMBIGUOUS"
    if qtype == "candidate_consistent_all_views":
        winners = [c["choice_label"] for c in record["candidates"] if all(c["view_matches"].values())]
        return winners[0] if len(winners) == 1 else "AMBIGUOUS"
    if qtype == "unique_determination":
        return "unique" if unique else "not unique"
    if qtype == "candidate_failed_view":
        candidate = next(c for c in record["candidates"] if c["choice_label"] == question["reference_choice"])
        failed = [name for name, match in candidate["view_matches"].items() if not match]
        return failed[0] if len(failed) == 1 else "AMBIGUOUS"
    if qtype == "add_above_tallest_changed_views":
        cubes = {tuple(c) for c in record["target_cubes"]}
        x, y = record["tallest_column_xy"]
        height = max(z for xx, yy, z in cubes if (xx, yy) == (x, y)) + 1
        after = derive_views(cubes | {(x, y, height)})
        changed = [name for i, name in enumerate(("top", "front", "side")) if views[i] != after[i]]
        return " and ".join(changed)
    raise KeyError(qtype)


def validate(root: Path):
    issues = []
    checked = 0
    panel_count = 0
    question_types = Counter()
    for line in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        checked += 1
        iid = record["id"]
        cubes = {tuple(c) for c in record["target_cubes"]}
        if len(cubes) != len(record["target_cubes"]):
            issues.append(f"{iid}: duplicate target cube")
        if not supported(cubes):
            issues.append(f"{iid}: target contains a floating cube")
        if not 6 <= len(cubes) <= 12 or record["total_cube_count"] != len(cubes):
            issues.append(f"{iid}: target count mismatch/range failure")
        views = derive_views(cubes)
        stored_views = tuple({tuple(cell) for cell in record[key]} for key in ("top_view_cells", "front_view_cells", "side_view_cells"))
        if views != stored_views:
            issues.append(f"{iid}: stored projection mismatch")
        minimum, unique = independent_analysis(*views)
        if minimum != record["minimum_possible_cube_count"]:
            issues.append(f"{iid}: minimum count stored={record['minimum_possible_cube_count']} actual={minimum}")
        if unique != record["is_uniquely_determined"]:
            issues.append(f"{iid}: uniqueness stored={record['is_uniquely_determined']} actual={unique}")
        image_path = root / record["image_path"]
        if not image_path.is_file():
            issues.append(f"{iid}: missing image")
        else:
            issues.extend(f"{iid}: {msg}" for msg in png_views_match(image_path, record["canvas_size"], views, record["has_candidate_panel"]))
        if record["has_candidate_panel"]:
            panel_count += 1
            candidates = record["candidates"]
            if len(candidates) != 4 or [c["choice_label"] for c in candidates] != list("ABCD"):
                issues.append(f"{iid}: invalid candidate labels/count")
            all_matches = 0
            exact_two = 0
            for candidate in candidates:
                ccubes = {tuple(c) for c in candidate["cubes"]}
                if not supported(ccubes):
                    issues.append(f"{iid}/{candidate['choice_label']}: unsupported candidate")
                matches = dict(zip(("top", "front", "side"), (a == b for a, b in zip(derive_views(ccubes), views))))
                if matches != candidate["view_matches"] or all(matches.values()) != candidate["matches_all_3_views"]:
                    issues.append(f"{iid}/{candidate['choice_label']}: candidate match flags wrong")
                all_matches += all(matches.values())
                exact_two += sum(matches.values()) == 2 and not all(matches.values())
            if all_matches != 1 or exact_two < 1:
                issues.append(f"{iid}: candidate discrimination failure")
            winner = next((c["choice_label"] for c in candidates if c["matches_all_3_views"]), None)
            if winner != record["correct_answer_choice"]:
                issues.append(f"{iid}: correct candidate mismatch")
        elif record["candidates"] or record["correct_answer_choice"] is not None:
            issues.append(f"{iid}: candidate data present without panel")
        questions = record["questions"]
        if len(questions) != 4 or [q["difficulty_level"] for q in questions] != [1, 2, 3, 4]:
            issues.append(f"{iid}: question levels/count invalid")
        for question in questions:
            question_types[question["question_type"]] += 1
            try:
                actual = answer_for(question, record, views, minimum, unique)
            except Exception as exc:
                issues.append(f"{iid}/{question.get('question_id')}: answer derivation error {exc}")
                continue
            if actual != question["ground_truth"]:
                issues.append(f"{iid}/{question['question_id']}: stored={question['ground_truth']!r} actual={actual!r}")
    # Alternating seeds yield an exact split for even-sized datasets and the nearest
    # possible split for odd samples (for example, 2/5 rather than an impossible 2.5/5).
    if checked and abs(panel_count - checked / 2) > 0.5:
        issues.append(f"dataset: candidate panel ratio {panel_count}/{checked} is not the nearest possible 50/50 split")
    return checked, panel_count, question_types, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, nargs="?", default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    checked, panels, types, issues = validate(args.dataset)
    lines = [
        f"Total images checked: {checked}",
        f"Candidate-panel images: {panels}",
        f"Direct-question images: {checked - panels}",
        f"Total mismatches found: {len(issues)}",
        f"Question types: {json.dumps(dict(sorted(types.items())), sort_keys=True)}",
        f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    if issues:
        lines.extend(issues)
    report = args.dataset / "validation_report.txt"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report.read_text(encoding="utf-8"))
    raise SystemExit(bool(issues))


if __name__ == "__main__":
    main()
