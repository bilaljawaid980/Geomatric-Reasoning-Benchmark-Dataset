"""Generate deterministic laser/mirror ray-tracing puzzles and all dataset tables."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKGROUND = "#FDFAF4"
GRID = "#8C969C"
BORDER = "#253743"
MIRROR = "#182E3A"
MIRROR_GLOW = "#8DD3E0"
ENTRY = "#D56A2D"
EXIT = "#25856D"
TEXT = "#24343D"
TASKS = {
    1: "Image Description",
    2: "Basic Relational Reasoning",
    3: "Comparative Reasoning",
    4: "Compound Reasoning",
    5: "Extrapolative/Counterfactual Reasoning",
}
STEP = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
REFLECT = {
    "/": {"right": "up", "up": "right", "left": "down", "down": "left"},
    "\\": {"right": "down", "down": "right", "left": "up", "up": "left"},
}


def font(size: int, bold: bool = False):
    try:
        name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default()


def cell_label(cell):
    return f"R{cell[0]}C{cell[1]}"


def edge_entry(edge, position, n):
    if edge == "top":
        return (1, position), "down"
    if edge == "bottom":
        return (n, position), "up"
    if edge == "left":
        return (position, 1), "right"
    return (position, n), "left"


def exit_data(row, col, direction, n):
    if row < 1:
        return "top", col
    if row > n:
        return "bottom", col
    if col < 1:
        return "left", row
    return "right", row


def simulate(n, mirrors, start_cell, start_direction):
    """Trace at cell-center resolution; repeated (cell,direction) means a loop."""
    row, col = start_cell
    direction = start_direction
    states = set()
    path = []
    reflections = []
    while 1 <= row <= n and 1 <= col <= n:
        state = (row, col, direction)
        if state in states:
            return {"loop": True, "path_cells": path, "reflection_points": reflections}
        states.add(state)
        path.append([row, col])
        orientation = mirrors.get((row, col))
        if orientation:
            direction = REFLECT[orientation][direction]
            reflections.append({"cell": [row, col], "orientation": orientation, "outgoing_direction": direction})
        dr, dc = STEP[direction]
        row += dr
        col += dc
    edge, position = exit_data(row, col, direction, n)
    return {
        "loop": False,
        "path_cells": path,
        "reflection_points": reflections,
        "num_reflections": len(reflections),
        "path_length": len(path),
        "exit_cell": path[-1],
        "exit_edge": edge,
        "exit_position": position,
        "exit_direction": direction,
    }


def place_mirrors(rng, n, count):
    cells = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
    rng.shuffle(cells)
    chosen = []
    for cell in cells:
        if all(abs(cell[0] - other[0]) + abs(cell[1] - other[1]) != 1 for other in chosen):
            chosen.append(cell)
            if len(chosen) == count:
                break
    if len(chosen) != count:
        return None
    return {cell: rng.choice(("/", "\\")) for cell in chosen}


def all_entries(n):
    for edge in ("top", "right", "bottom", "left"):
        for position in range(1, n + 1):
            cell, direction = edge_entry(edge, position, n)
            yield edge, position, cell, direction


def exit_answer(trace):
    return f"{trace['exit_edge']}, position {trace['exit_position']}"


def make_scene(index):
    rng = random.Random(73_000_000 + index)
    n = 5 + (index - 1) % 4
    mirror_count = 2 + ((index - 1) // 4) % 4
    for attempt in range(1000):
        mirrors = place_mirrors(rng, n, mirror_count)
        if mirrors is None:
            continue
        candidates = []
        for edge, position, cell, direction in all_entries(n):
            trace = simulate(n, mirrors, cell, direction)
            if not trace["loop"]:
                candidates.append((edge, position, cell, direction, trace))
        if not candidates:
            continue
        zero = [x for x in candidates if x[4]["num_reflections"] == 0]
        hit = [x for x in candidates if x[4]["num_reflections"] > 0]
        desired_hit = index % 4 != 0
        pool = hit if desired_hit else zero
        if not pool:
            continue
        # For one quarter of scenes prefer the longest valid multi-bounce trace.
        if index % 4 == 3 and desired_hit:
            best = max(x[4]["num_reflections"] for x in pool)
            pool = [x for x in pool if x[4]["num_reflections"] == best]
        entry_edge, entry_position, entry_cell, entry_direction, trace = rng.choice(pool)
        # Stronger than required: every possible single-mirror flip must also exit.
        flipped = {}
        all_finite = True
        for cell in mirrors:
            modified = dict(mirrors)
            modified[cell] = "\\" if modified[cell] == "/" else "/"
            candidate = simulate(n, modified, entry_cell, entry_direction)
            if candidate["loop"]:
                all_finite = False
                break
            flipped[cell] = candidate
        if not all_finite:
            continue
        hit_cells = [tuple(x["cell"]) for x in trace["reflection_points"]]
        target_pool = hit_cells if hit_cells else list(mirrors)
        target = rng.choice(target_pool)
        counterfactual = flipped[target]
        break
    else:
        raise RuntimeError(f"Could not generate finite scene {index}")

    iid = f"laser_mirror_{index:04d}"
    changed = (counterfactual["exit_edge"], counterfactual["exit_position"]) != (trace["exit_edge"], trace["exit_position"])
    l5_answer = ("yes" if changed else "no") + f"; exits at {exit_answer(counterfactual)}"
    target_label = cell_label(target)
    questions = [
        {"question_id": f"{iid}_q1", "difficulty_level": 1, "question_type": "mirror_count", "question_text": "How many mirrors are placed in this grid?", "ground_truth": str(mirror_count), "answer_format": "integer"},
        {"question_id": f"{iid}_q2", "difficulty_level": 2, "question_type": "hits_any_mirror", "question_text": "Does the laser hit at least one mirror before exiting the grid? Answer yes or no.", "ground_truth": "yes" if trace["num_reflections"] else "no", "answer_format": "yes or no"},
        {"question_id": f"{iid}_q3", "difficulty_level": 3, "question_type": "reflection_count", "question_text": "How many times does the laser reflect off a mirror before exiting the grid?", "ground_truth": str(trace["num_reflections"]), "answer_format": "integer"},
        {"question_id": f"{iid}_q4", "difficulty_level": 4, "question_type": "exit_edge_position", "question_text": "From which edge and position does the laser exit the grid? Answer with the edge (top/bottom/left/right) and cell position.", "ground_truth": exit_answer(trace), "answer_format": "edge, position N"},
        {"question_id": f"{iid}_q5", "difficulty_level": 5, "question_type": "flipped_mirror_exit", "question_text": f"If the mirror at cell {target_label} were rotated 90 degrees (changed from '/' to '\\' or vice versa), would the laser's exit point change? If so, where would it now exit?", "ground_truth": l5_answer, "answer_format": "yes/no; exits at edge, position N"},
    ]
    canvas = 500 + ((index * 13) % 51)
    mirror_rows = [{"cell": [r, c], "cell_label": cell_label((r, c)), "orientation": mirrors[(r, c)]} for r, c in sorted(mirrors)]
    difficulty = round(min(1.0, .16 + .055 * (n - 5) + .045 * mirror_count + .105 * trace["num_reflections"] + .018 * trace["path_length"]), 4)
    return {
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": [canvas, canvas],
        "seed": 73_000_000 + index,
        "grid_size": n,
        "mirrors": mirror_rows,
        "entry_edge": entry_edge,
        "entry_position": entry_position,
        "entry_cell": list(entry_cell),
        "entry_direction": entry_direction,
        "exit_cell": trace["exit_cell"],
        "exit_edge": trace["exit_edge"],
        "exit_position": trace["exit_position"],
        "exit_direction": trace["exit_direction"],
        "path_cells": trace["path_cells"],
        "reflection_points": trace["reflection_points"],
        "num_reflections": trace["num_reflections"],
        "path_length": trace["path_length"],
        "level5_mirror_cell": list(target),
        "level5_original_orientation": mirrors[target],
        "level5_flipped_orientation": "\\" if mirrors[target] == "/" else "/",
        "level5_exit_changed": changed,
        "level5_exit_cell": counterfactual["exit_cell"],
        "level5_exit_edge": counterfactual["exit_edge"],
        "level5_exit_position": counterfactual["exit_position"],
        "level5_exit_direction": counterfactual["exit_direction"],
        "level5_path_cells": counterfactual["path_cells"],
        "level5_num_reflections": counterfactual["num_reflections"],
        "generation_attempt": attempt,
        "difficulty_score": difficulty,
        "questions": questions,
    }


def grid_geometry(canvas, n):
    margin = 82
    side = canvas - 2 * margin
    cell = side / n
    return margin, margin, side, cell


def center_of(cell, x0, y0, size):
    r, c = cell
    return x0 + (c - .5) * size, y0 + (r - .5) * size


def boundary_point(edge, position, x0, y0, side, cell):
    if edge == "top":
        return x0 + (position - .5) * cell, y0
    if edge == "bottom":
        return x0 + (position - .5) * cell, y0 + side
    if edge == "left":
        return x0, y0 + (position - .5) * cell
    return x0 + side, y0 + (position - .5) * cell


def draw_arrow(draw, edge, position, inward, x0, y0, side, cell, scale, color, label):
    bx, by = boundary_point(edge, position, x0, y0, side, cell)
    outward = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}[edge]
    ox, oy = outward
    if inward:
        start = (bx + ox * 40, by + oy * 40)
        end = (bx + ox * 5, by + oy * 5)
    else:
        start = (bx + ox * 5, by + oy * 5)
        end = (bx + ox * 40, by + oy * 40)
    start = tuple(round(v * scale) for v in start)
    end = tuple(round(v * scale) for v in end)
    draw.line([start, end], fill=color, width=round(4 * scale))
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 9 * scale
    points = [end]
    for delta in (2.55, -2.55):
        points.append((end[0] + head * math.cos(angle + delta), end[1] + head * math.sin(angle + delta)))
    draw.polygon(points, fill=color)
    tx = (start[0] + end[0]) / 2 + oy * 13 * scale
    ty = (start[1] + end[1]) / 2 + ox * 13 * scale
    draw.text((round(tx), round(ty)), label, font=font(11 * scale, True), fill=color, anchor="mm")


def render(row, destination):
    scale = 3
    canvas = row["canvas_size"][0]
    x0, y0, side, cell = grid_geometry(canvas, row["grid_size"])
    image = Image.new("RGB", (canvas * scale, canvas * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    sx0, sy0, sside, scell = (v * scale for v in (x0, y0, side, cell))
    for k in range(row["grid_size"] + 1):
        p = round(k * scell)
        width = round((2.2 if k in (0, row["grid_size"]) else 1.1) * scale)
        color = BORDER if k in (0, row["grid_size"]) else GRID
        draw.line([(round(sx0 + p), round(sy0)), (round(sx0 + p), round(sy0 + sside))], fill=color, width=width)
        draw.line([(round(sx0), round(sy0 + p)), (round(sx0 + sside), round(sy0 + p))], fill=color, width=width)
    small = font(11 * scale, True)
    for i in range(1, row["grid_size"] + 1):
        cx = (x0 + (i - .5) * cell) * scale
        cy = (y0 + (i - .5) * cell) * scale
        draw.text((round(cx), round((y0 - 12) * scale)), str(i), font=small, fill=TEXT, anchor="mm")
        draw.text((round((x0 - 13) * scale), round(cy)), str(i), font=small, fill=TEXT, anchor="mm")
    inset = max(5, cell * .12)
    for mirror in row["mirrors"]:
        r, c = mirror["cell"]
        left = x0 + (c - 1) * cell + inset
        right = x0 + c * cell - inset
        top = y0 + (r - 1) * cell + inset
        bottom = y0 + r * cell - inset
        if mirror["orientation"] == "/":
            a, b = (left, bottom), (right, top)
        else:
            a, b = (left, top), (right, bottom)
        aa = tuple(round(v * scale) for v in a)
        bb = tuple(round(v * scale) for v in b)
        draw.line([aa, bb], fill=MIRROR_GLOW, width=round(8 * scale))
        draw.line([aa, bb], fill=MIRROR, width=round(3.5 * scale))
    draw_arrow(draw, row["entry_edge"], row["entry_position"], True, x0, y0, side, cell, scale, ENTRY, "IN")
    draw_arrow(draw, row["exit_edge"], row["exit_position"], False, x0, y0, side, cell, scale, EXIT, "OUT")
    image.resize((canvas, canvas), Image.Resampling.LANCZOS).save(destination, "PNG", optimize=True)


def compact_metadata(row):
    return json.dumps({
        "difficulty_score": row["difficulty_score"],
        "grid_size": row["grid_size"],
        "num_mirrors": len(row["mirrors"]),
        "num_reflections": row["num_reflections"],
        "path_length": row["path_length"],
        "seed": row["seed"],
    }, separators=(",", ":"))


def write_tables(output, rows):
    public_fields = ["question_id", "task", "image", "prompt"]
    answer_fields = public_fields + ["groundtruth", "answer_format"]
    final_fields = ["task", "image", "prompt", "groundtruth", "metadata"]
    public_rows, answer_rows, final_rows = [], [], []
    for row in rows:
        for question in row["questions"]:
            base = {"question_id": question["question_id"], "task": TASKS[question["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": question["question_text"]}
            public_rows.append(base)
            answer_rows.append({**base, "groundtruth": str(question["ground_truth"]), "answer_format": question["answer_format"]})
            final_rows.append({"task": base["task"], "image": base["image"], "prompt": base["prompt"], "groundtruth": str(question["ground_truth"]), "metadata": compact_metadata(row)})
    for filename, fields, data in (("question_set.csv", public_fields, public_rows), ("answer_key.csv", answer_fields, answer_rows), ("dataset_final.csv", final_fields, final_rows)):
        with (output / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
    with (output / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in final_rows:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")


def make_sheet(output, rows, filename, selected, columns=5, thumb=190):
    chosen = [rows[i] for i in selected if i < len(rows)]
    if not chosen:
        return
    rows_n = math.ceil(len(chosen) / columns)
    sheet = Image.new("RGB", (columns * thumb, rows_n * (thumb + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(chosen):
        with Image.open(output / row["image_path"]) as source:
            pic = source.convert("RGB")
            pic.thumbnail((thumb - 8, thumb - 28), Image.Resampling.LANCZOS)
        x = (i % columns) * thumb + (thumb - pic.width) // 2
        y = (i // columns) * (thumb + 24) + 2
        sheet.paste(pic, (x, y))
        draw.text((i % columns * thumb + thumb // 2, y + pic.height + 10), row["id"], font=font(12, True), fill=TEXT, anchor="mm")
    sheet.save(output / filename, "PNG", optimize=True)


def manual_trace_text(rows):
    lines = ["Manual trace aid (first five deterministic samples)", "=" * 55]
    for row in rows[:5]:
        path = " -> ".join(cell_label(c) for c in row["path_cells"])
        reflections = ", ".join(f"{cell_label(x['cell'])}{x['orientation']}->{x['outgoing_direction']}" for x in row["reflection_points"]) or "none"
        lines += [f"{row['id']}: IN {row['entry_edge']} {row['entry_position']} ({row['entry_direction']})", f"  path: {path}", f"  reflections: {reflections}", f"  OUT: {row['exit_edge']} position {row['exit_position']} ({row['exit_direction']})"]
    return "\n".join(lines) + "\n"


def generate(output, count, start_index, render_images=True):
    output.mkdir(parents=True, exist_ok=True)
    images = output / "images"
    images.mkdir(exist_ok=True)
    rows = []
    for position, index in enumerate(range(start_index, start_index + count), 1):
        row = make_scene(index)
        rows.append(row)
        if render_images:
            render(row, output / row["image_path"])
        if position % 100 == 0 or position == count:
            print(f"Generated {position}/{count}", flush=True)
    with (output / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    write_tables(output, rows)
    stats = {
        "images": len(rows),
        "questions": len(rows) * 5,
        "grid_sizes": dict(Counter(str(r["grid_size"]) for r in rows)),
        "mirror_counts": dict(Counter(str(len(r["mirrors"])) for r in rows)),
        "level2": dict(Counter(r["questions"][1]["ground_truth"] for r in rows)),
        "reflection_counts": dict(sorted(Counter(str(r["num_reflections"]) for r in rows).items(), key=lambda x: int(x[0]))),
        "level5_changed": dict(Counter("yes" if r["level5_exit_changed"] else "no" for r in rows)),
        "generation_rejections": sum(r["generation_attempt"] for r in rows),
    }
    (output / "generation_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    (output / "manual_trace_samples.txt").write_text(manual_trace_text(rows), encoding="utf-8")
    if render_images:
        review_indices = list(range(min(5, len(rows)))) if len(rows) < 2400 else [0, 599, 1199, 1799, 2399]
        make_sheet(output, rows, "review_sheet.png", review_indices, 5, 210)
        step = max(1, len(rows) // 64)
        make_sheet(output, rows, "contact_sheet.png", list(range(0, len(rows), step))[:64], 8, 145)
    (output / "stats.md").write_text("# Laser Mirror Dataset Statistics\n\n```json\n" + json.dumps(stats, indent=2) + "\n```\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--sample", action="store_true", help="Generate five deterministic images in sample_test/")
    args = parser.parse_args()
    if args.sample:
        args.output_dir = Path(__file__).resolve().parent / "sample_test"
        args.count = 5
    generate(args.output_dir, args.count, args.start_index, not args.metadata_only)


if __name__ == "__main__":
    main()
