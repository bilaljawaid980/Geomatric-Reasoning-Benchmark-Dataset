"""Independent validator for the laser-mirror dataset (does not import the generator)."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageStat

TASKS = {1: "Image Description", 2: "Basic Relational Reasoning", 3: "Comparative Reasoning", 4: "Compound Reasoning", 5: "Extrapolative/Counterfactual Reasoning"}
MOVE = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
BOUNCE = {
    "/": {"right": "up", "up": "right", "left": "down", "down": "left"},
    "\\": {"right": "down", "down": "right", "left": "up", "up": "left"},
}


def independent_trace(size, mirrors, cell, direction):
    r, c = cell
    seen, path, reflections = set(), [], []
    while 1 <= r <= size and 1 <= c <= size:
        state = (r, c, direction)
        if state in seen:
            return {"loop": True, "path_cells": path, "reflection_points": reflections}
        seen.add(state)
        path.append([r, c])
        if (r, c) in mirrors:
            direction = BOUNCE[mirrors[(r, c)]][direction]
            reflections.append({"cell": [r, c], "orientation": mirrors[(r, c)], "outgoing_direction": direction})
        dr, dc = MOVE[direction]
        r, c = r + dr, c + dc
    if r == 0:
        edge, pos = "top", c
    elif r == size + 1:
        edge, pos = "bottom", c
    elif c == 0:
        edge, pos = "left", r
    else:
        edge, pos = "right", r
    return {"loop": False, "path_cells": path, "reflection_points": reflections, "num_reflections": len(reflections), "path_length": len(path), "exit_cell": path[-1], "exit_edge": edge, "exit_position": pos, "exit_direction": direction}


def exit_answer(trace):
    return f"{trace['exit_edge']}, position {trace['exit_position']}"


def expected(row):
    mirrors = {tuple(x["cell"]): x["orientation"] for x in row["mirrors"]}
    trace = independent_trace(row["grid_size"], mirrors, tuple(row["entry_cell"]), row["entry_direction"])
    target = tuple(row["level5_mirror_cell"])
    modified = dict(mirrors)
    modified[target] = "\\" if modified[target] == "/" else "/"
    counter = independent_trace(row["grid_size"], modified, tuple(row["entry_cell"]), row["entry_direction"])
    changed = (trace["exit_edge"], trace["exit_position"]) != (counter["exit_edge"], counter["exit_position"])
    wants = [
        ("mirror_count", str(len(mirrors)), "integer"),
        ("hits_any_mirror", "yes" if trace["num_reflections"] else "no", "yes or no"),
        ("reflection_count", str(trace["num_reflections"]), "integer"),
        ("exit_edge_position", exit_answer(trace), "edge, position N"),
        ("flipped_mirror_exit", ("yes" if changed else "no") + f"; exits at {exit_answer(counter)}", "yes/no; exits at edge, position N"),
    ]
    return mirrors, trace, counter, changed, wants


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_tables(root, records):
    issues = []
    public = read_csv(root / "question_set.csv")
    answers = read_csv(root / "answer_key.csv")
    final = read_csv(root / "dataset_final.csv")
    pairs = [(r, q) for r in records for q in r["questions"]]
    if not len(public) == len(answers) == len(final) == len(pairs):
        return [f"table row counts: public={len(public)} answer={len(answers)} final={len(final)} expected={len(pairs)}"]
    if public and ("groundtruth" in public[0] or "answer_format" in public[0]):
        issues.append("question_set.csv leaks private columns")
    for i, ((row, q), pub, ans, flat) in enumerate(zip(pairs, public, answers, final), 1):
        base = {"question_id": q["question_id"], "task": TASKS[q["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": q["question_text"]}
        if any(pub.get(k) != v for k, v in base.items()):
            issues.append(f"public row {i}")
        if any(ans.get(k) != v for k, v in base.items()) or ans.get("groundtruth") != str(q["ground_truth"]) or ans.get("answer_format") != q["answer_format"]:
            issues.append(f"answer row {i}")
        if flat.get("groundtruth") != str(q["ground_truth"]):
            issues.append(f"final row {i}")
    return issues


def validate(root):
    root = Path(root)
    records = [json.loads(line) for line in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues, grids, mirrors_count, l2, l5, reflection_counts = [], Counter(), Counter(), Counter(), Counter(), Counter()
    png_checked = 0
    for position, row in enumerate(records, 1):
        iid = row["id"]
        try:
            mirrors, trace, counter, changed, wants = expected(row)
            grids[row["grid_size"]] += 1
            mirrors_count[len(mirrors)] += 1
            l2["yes" if trace["num_reflections"] else "no"] += 1
            l5["yes" if changed else "no"] += 1
            reflection_counts[trace["num_reflections"]] += 1
            if not 5 <= row["grid_size"] <= 8:
                issues.append(f"{iid}: grid size")
            if not 2 <= len(mirrors) <= 5 or any(x not in ("/", "\\") for x in mirrors.values()):
                issues.append(f"{iid}: mirror schema")
            cells = list(mirrors)
            if len(cells) != len(set(cells)) or any(not (1 <= r <= row["grid_size"] and 1 <= c <= row["grid_size"]) for r, c in cells):
                issues.append(f"{iid}: mirror cells")
            if any(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for i, a in enumerate(cells) for b in cells[i + 1:]):
                issues.append(f"{iid}: orthogonally adjacent mirrors")
            if trace["loop"] or counter["loop"]:
                issues.append(f"{iid}: loop")
            # Check every possible single-mirror counterfactual, not only the asked one.
            for cell in mirrors:
                modified = dict(mirrors)
                modified[cell] = "\\" if modified[cell] == "/" else "/"
                if independent_trace(row["grid_size"], modified, tuple(row["entry_cell"]), row["entry_direction"])["loop"]:
                    issues.append(f"{iid}: unasked flip at {cell} loops")
            for key in ("path_cells", "reflection_points", "num_reflections", "path_length", "exit_cell", "exit_edge", "exit_position", "exit_direction"):
                if row[key] != trace[key]:
                    issues.append(f"{iid}: original {key}")
            for stored_key, computed_key in (("level5_exit_cell", "exit_cell"), ("level5_exit_edge", "exit_edge"), ("level5_exit_position", "exit_position"), ("level5_exit_direction", "exit_direction"), ("level5_path_cells", "path_cells"), ("level5_num_reflections", "num_reflections")):
                if row[stored_key] != counter[computed_key]:
                    issues.append(f"{iid}: {stored_key}")
            if row["level5_exit_changed"] != changed:
                issues.append(f"{iid}: Level 5 changed flag")
            if len(row["questions"]) != 5 or [q["difficulty_level"] for q in row["questions"]] != [1, 2, 3, 4, 5]:
                issues.append(f"{iid}: question schema")
            else:
                for q, want in zip(row["questions"], wants):
                    if (q["question_type"], str(q["ground_truth"]), q["answer_format"]) != want:
                        issues.append(f"{q['question_id']}: ground truth")
        except Exception as exc:
            issues.append(f"{iid}: exception {exc}")
        image_path = root / row["image_path"]
        if not image_path.exists():
            issues.append(f"{iid}: missing PNG")
        else:
            with Image.open(image_path) as source:
                image = source.convert("RGB")
                image.load()
            if image.size != tuple(row["canvas_size"]):
                issues.append(f"{iid}: PNG dimensions")
            elif sum(ImageStat.Stat(image).var) < 100:
                issues.append(f"{iid}: blank PNG")
            else:
                png_checked += 1
        if position % 500 == 0:
            print(f"Validated {position}/{len(records)}", flush=True)
    issues.extend(validate_tables(root, records))
    metrics = {"images_checked": len(records), "questions_checked": sum(len(r["questions"]) for r in records), "mismatches": len(issues), "pngs_checked": png_checked, "grid_sizes": dict(grids), "mirror_counts": dict(mirrors_count), "level2": dict(l2), "reflection_counts": dict(sorted(reflection_counts.items())), "level5_exit_changed": dict(l5), "issues": issues}
    (root / "validation_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    lines = ["Laser Mirror Dataset Validation Report", "=" * 39, f"Total images checked: {len(records)}", f"Total questions checked: {metrics['questions_checked']}", f"PNG files checked: {png_checked}", f"Total mismatches found: {len(issues)}", "", f"Grid sizes: {dict(grids)}", f"Mirror counts: {dict(mirrors_count)}", f"Level 2 answers: {dict(l2)}", f"Reflection counts: {dict(sorted(reflection_counts.items()))}", f"Level 5 exit changed: {dict(l5)}", "", "Independent checks:", "  Original path re-simulation: complete", "  Every single-mirror flip loop test: complete", "  Asked Level 5 flip re-simulation: complete", "  Orthogonal-adjacency constraint: complete", "  CSV/public-leak checks: complete", "", "Issues:"] + ([f"  {x}" for x in issues] if issues else ["  None"]) + ["", f"Summary: {'PASS' if not issues else 'FAIL'}"]
    (root / "validation_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return len(issues)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    raise SystemExit(1 if validate(args.root) else 0)


if __name__ == "__main__":
    main()
