"""Generate v4 depth-order impossible-object weave diagrams with visible occlusion cues."""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DATASET_VERSION = "impossible-object-4.0.0"
BG = (26, 26, 26)
COLORS = [(65, 145, 170), (61, 157, 148), (91, 132, 181)]
AA = 3
HALF_BEAM = 7.0
STROKE_WIDTH = 1.15
MIN_CROSSING_SEPARATION_PX = 8.0
MIN_REFERENCE_DISTANCE_GAP_PX = 12.0
MIN_LABEL_SEPARATION_PX = 24.0
TARGET_SEPARATION_TOLERANCE_PX = 1.0
TARGET_REFERENCE_GAP_TOLERANCE_PX = 1.0
CROSSING_COUNTS = (6, 7, 8, 9)
TASKS = {1: "Image Description", 2: "Basic Relational Reasoning", 3: "Comparative Reasoning", 4: "Compound Reasoning", 5: "Extrapolative/Counterfactual Reasoning"}


def get_font(size, bold=True):
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)
    except OSError:
        return ImageFont.load_default()


def inversion_count(permutation):
    return sum(permutation[i] > permutation[j] for i in range(len(permutation)) for j in range(i + 1, len(permutation)))


PERMUTATIONS = {(n, k): [p for p in itertools.permutations(range(n)) if inversion_count(p) == k] for n in (5, 6) for k in CROSSING_COUNTS}


def segment_intersection(a, b, c, d):
    den = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
    if abs(den) < 1e-9:
        return None
    t = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) / den
    u = -((a[0] - b[0]) * (a[1] - c[1]) - (a[1] - b[1]) * (a[0] - c[0])) / den
    if 1e-7 < t < 1 - 1e-7 and 1e-7 < u < 1 - 1e-7:
        return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    return None


def crossings_for_lines(lines):
    result = []
    for i, first in enumerate(lines):
        for j in range(i + 1, len(lines)):
            point = segment_intersection(first[0], first[1], lines[j][0], lines[j][1])
            if point is not None:
                result.append({"line_a": i, "line_b": j, "point": point})
    return result


def is_acyclic(node_count, directed_edges, skip=None):
    graph = [[] for _ in range(node_count)]
    indegree = [0] * node_count
    for front, back in directed_edges:
        if front == skip or back == skip:
            continue
        graph[front].append(back)
        indegree[back] += 1
    queue = [node for node in range(node_count) if node != skip and indegree[node] == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return seen == node_count - (skip is not None)


def unique_removable(node_count, directed_edges):
    if is_acyclic(node_count, directed_edges):
        return []
    return [node for node in range(node_count) if is_acyclic(node_count, directed_edges, node)]


def impossible_orientation(node_count, crossings, rng):
    pairs = [(item["line_a"], item["line_b"]) for item in crossings]
    masks = list(range(1 << len(pairs)))
    rng.shuffle(masks)
    for mask in masks:
        edges = [(a, b) if (mask >> k) & 1 else (b, a) for k, (a, b) in enumerate(pairs)]
        removable = unique_removable(node_count, edges)
        if len(removable) == 1:
            return edges, removable[0]
    return None, None


def possible_orientation(node_count, crossings, rng):
    order = list(range(node_count))
    rng.shuffle(order)
    rank = {node: position for position, node in enumerate(order)}
    return [(item["line_a"], item["line_b"]) if rank[item["line_a"]] < rank[item["line_b"]] else (item["line_b"], item["line_a"]) for item in crossings]


def min_pair_distance(points):
    if len(points) < 2:
        return float("inf")
    return min(math.dist(a, b) for i, a in enumerate(points) for b in points[i + 1:])


def label_mapping(node_count, removable, desired_label, rng):
    labels = list("ABCDEF"[:node_count])
    mapping = {}
    if removable is not None:
        mapping[removable] = desired_label
        remaining_labels = [x for x in labels if x != desired_label]
        remaining_nodes = [x for x in range(node_count) if x != removable]
        rng.shuffle(remaining_labels)
        for node, label in zip(remaining_nodes, remaining_labels):
            mapping[node] = label
    else:
        rng.shuffle(labels)
        mapping = {node: labels[node] for node in range(node_count)}
    return mapping


def normalized_direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max(1e-9, math.hypot(dx, dy))
    return dx / length, dy / length


def make_scene(index, recovery_retry=0):
    rng = random.Random(82_000_000 + index + recovery_retry * 10_000_019)
    size_rng = random.Random(index)
    width, height = size_rng.randint(500, 600), size_rng.randint(350, 400)
    mode = "possible" if index % 2 else "impossible"
    target_crossings = CROSSING_COUNTS[((index - 1) // 2) % len(CROSSING_COUNTS)]
    beam_count = 5 + (((index - 1) // 8) % 2)
    impossible_number = (index // 2) - 1
    desired_removal_label = "ABCDEF"[impossible_number % beam_count] if mode == "impossible" else None
    shared_block = (index - 1) // 16
    target_label_separation = 40.0 + ((shared_block * 17) % 41) / 10.0
    target_crossing_separation = 9.0 if shared_block % 2 == 0 else 11.0
    target_reference_gap = 13.5 + ((shared_block * 7) % 11) / 10.0
    for attempt in range(120000):
        permutation = rng.choice(PERMUTATIONS[(beam_count, target_crossings)])
        x_left, x_right = 90.0, width - 42.0
        top, bottom = 55.0, height - 50.0
        spacing = (bottom - top) / (beam_count - 1)
        left_levels = sorted(top + i * spacing + rng.uniform(-spacing * .40, spacing * .40) for i in range(beam_count))
        right_rank_levels = sorted(top + i * spacing + rng.uniform(-spacing * .40, spacing * .40) for i in range(beam_count))
        lines = [[[x_left, left_levels[i]], [x_right, right_rank_levels[permutation[i]]]] for i in range(beam_count)]
        crossings = crossings_for_lines(lines)
        if len(crossings) != target_crossings:
            continue
        points = [x["point"] for x in crossings]
        separation = min_pair_distance(points)
        if separation < MIN_CROSSING_SEPARATION_PX:
            continue
        if abs(separation - target_crossing_separation) > TARGET_SEPARATION_TOLERANCE_PX:
            continue
        center = [width / 2, height / 2]
        ordered = sorted((math.dist(item["point"], center), k) for k, item in enumerate(crossings))
        reference_gap = ordered[1][0] - ordered[0][0]
        if reference_gap < MIN_REFERENCE_DISTANCE_GAP_PX:
            continue
        if abs(reference_gap - target_reference_gap) > TARGET_REFERENCE_GAP_TOLERANCE_PX:
            continue
        label_levels = [height / 2 - (beam_count - 1) * target_label_separation / 2 + i * target_label_separation for i in range(beam_count)]
        label_separation = min(abs(a - b) for i, a in enumerate(label_levels) for b in label_levels[i + 1:])
        if label_separation < MIN_LABEL_SEPARATION_PX:
            continue
        if mode == "possible":
            directed, removable = possible_orientation(beam_count, crossings, rng), None
        else:
            directed, removable = impossible_orientation(beam_count, crossings, rng)
            if directed is None:
                continue
        mapping = label_mapping(beam_count, removable, desired_removal_label, rng)
        break
    else:
        raise RuntimeError(f"Unable to generate scene {index}")

    edge_by_pair = {frozenset((a, b)): (a, b) for a, b in directed}
    crossing_rows = []
    for number, item in enumerate(crossings, 1):
        front_line, back_line = edge_by_pair[frozenset((item["line_a"], item["line_b"]))]
        crossing_rows.append({
            "crossing_id": f"X{number}",
            "point": [round(item["point"][0], 4), round(item["point"][1], 4)],
            "beam_a": mapping[item["line_a"]],
            "beam_b": mapping[item["line_b"]],
            "front_beam": mapping[front_line],
            "back_beam": mapping[back_line],
        })
    beams = []
    for line_number, endpoints in enumerate(lines):
        beams.append({"beam_label": mapping[line_number], "line_index": line_number, "points": [[round(v, 4) for v in p] for p in endpoints], "label_anchor": [42.0, round(label_levels[line_number], 4)]})
    beams.sort(key=lambda item: item["beam_label"])
    reference_index = ordered[0][1]
    reference = crossing_rows[reference_index]
    depth_constraints = [{"crossing_id": c["crossing_id"], "front_beam": c["front_beam"], "back_beam": c["back_beam"]} for c in crossing_rows]
    removable_label = mapping[removable] if removable is not None else None
    iid = f"impossible_object_{index:04d}"
    questions = [
        {"question_id": f"{iid}_q1", "difficulty_level": 1, "question_type": "beam_count", "question_text": "How many distinct beams or segments make up this structure?", "ground_truth": str(beam_count), "answer_format": "integer"},
        {"question_id": f"{iid}_q2", "difficulty_level": 2, "question_type": "constructible", "question_text": "Is this 3D structure physically constructible in real space? Answer yes or no.", "ground_truth": "yes" if mode == "possible" else "no", "answer_format": "yes or no"},
        {"question_id": f"{iid}_q3", "difficulty_level": 3, "question_type": "nearest_center_front_beam", "question_text": "At the crossing closest to the image centre, which beam passes in front? Answer with the beam label.", "ground_truth": reference["front_beam"], "answer_format": "beam label"},
        {"question_id": f"{iid}_q4", "difficulty_level": 4, "question_type": "crossing_count", "question_text": "How many crossing points are visible where one beam passes over another? Answer with a number.", "ground_truth": str(target_crossings), "answer_format": "integer"},
        {"question_id": f"{iid}_q5", "difficulty_level": 5, "question_type": "single_beam_constructibility_repair", "question_text": "Which single beam, if removed, would make this structure physically constructible? Answer with the beam label, or 'already constructible' if the structure requires no change.", "ground_truth": removable_label if removable_label else "already constructible", "answer_format": "beam label or already constructible"},
    ]
    color_index = random.Random(94_000_000 + index).randrange(len(COLORS))
    scene_params = {
        "canvas_width": width,
        "canvas_height": height,
        "mode": mode,
        "beam_count": beam_count,
        "target_crossing_count": target_crossings,
        "target_crossing_separation_px": round(target_crossing_separation, 6),
        "minimum_crossing_separation_px": round(separation, 6),
        "target_reference_distance_gap_px": round(target_reference_gap, 6),
        "reference_distance_gap_px": round(reference_gap, 6),
        "target_label_separation_px": round(target_label_separation, 6),
        "minimum_label_separation_px": round(label_separation, 6),
        "reference_front_beam": reference["front_beam"],
        "removable_beam_label": removable_label,
        "color_index": color_index,
    }
    return {
        "dataset_version": DATASET_VERSION,
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": [width, height],
        "seed": 82_000_000 + index,
        "mode": mode,
        "color": list(COLORS[color_index]),
        "num_beams": beam_count,
        "beams": beams,
        "crossings": crossing_rows,
        "num_crossings": target_crossings,
        "depth_constraints": depth_constraints,
        "depth_constraint_representation": "directed beam-label front/back relation per projected crossing",
        "reference_rule": "crossing with minimum Euclidean distance to image centre",
        "reference_crossing_id": reference["crossing_id"],
        "reference_crossing_point": reference["point"],
        "reference_front_beam": reference["front_beam"],
        "removable_beam_label": removable_label,
        "difficulty_score": round(.40 + .04 * (beam_count - 5) + .035 * (target_crossings - 6) + .18 * (mode == "impossible"), 4),
        "scene_params": scene_params,
        "questions": questions,
    }, {"generation_attempt": attempt, "png_recovery_retry": recovery_retry, "beam_count": beam_count, "crossing_count": target_crossings}


def beam_by_label(row):
    return {beam["beam_label"]: beam for beam in row["beams"]}


def band_edges(points, half=HALF_BEAM):
    a, b = points
    dx, dy = normalized_direction(a, b)
    nx, ny = -dy * half, dx * half
    return ([a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny]), ([a[0] - nx, a[1] - ny], [b[0] - nx, b[1] - ny])


def draw_band(draw, points, color, scale, center=None, half_length=None):
    a, b = points
    if center is not None:
        dx, dy = normalized_direction(a, b)
        a = [center[0] - dx * half_length, center[1] - dy * half_length]
        b = [center[0] + dx * half_length, center[1] + dy * half_length]
    for edge in band_edges([a, b]):
        draw.line([(round(edge[0][0] * scale), round(edge[0][1] * scale)), (round(edge[1][0] * scale), round(edge[1][1] * scale))], fill=color, width=max(2, round(STROKE_WIDTH * scale)))


def render(row, destination):
    width, height = row["canvas_size"]
    scale = AA
    color = tuple(row["color"])
    image = Image.new("RGB", (width * scale, height * scale), BG)
    draw = ImageDraw.Draw(image)
    lookup = beam_by_label(row)
    for beam in row["beams"]:
        draw_band(draw, beam["points"], color, scale)
    # Erase both members locally, then redraw only the foreground member as a bridge.
    for crossing in row["crossings"]:
        x, y = crossing["point"]
        radius = 11.0
        draw.ellipse((round((x - radius) * scale), round((y - radius) * scale), round((x + radius) * scale), round((y + radius) * scale)), fill=BG)
        front_points = lookup[crossing["front_beam"]]["points"]
        draw_band(draw, front_points, color, scale, crossing["point"], 9.0)
        dx, dy = normalized_direction(front_points[0], front_points[1])
        draw.line([(round((x - dx * 9.0) * scale), round((y - dy * 9.0) * scale)), (round((x + dx * 9.0) * scale), round((y + dy * 9.0) * scale))], fill=color, width=round(5.0 * scale))
    badge_font = get_font(13 * scale, True)
    for beam in row["beams"]:
        x, y = beam["label_anchor"]
        endpoint = beam["points"][0]
        draw.line([(round((x + 11) * scale), round(y * scale)), (round((endpoint[0] - 5) * scale), round(endpoint[1] * scale))], fill=color, width=max(2, round(STROKE_WIDTH * scale)))
        radius = 10.5
        draw.ellipse((round((x - radius) * scale), round((y - radius) * scale), round((x + radius) * scale), round((y + radius) * scale)), fill=color)
        draw.text((round(x * scale), round((y + .3) * scale)), beam["beam_label"], font=badge_font, fill=BG, anchor="mm")
    image.resize((width, height), Image.Resampling.LANCZOS).save(destination, "PNG", optimize=True)


def raster_colored(pixel):
    return max(abs(pixel[k] - BG[k]) for k in range(3)) > 24


def raster_template_error(image, point, beam_a, beam_b, front_label):
    candidates = {beam_a["beam_label"]: beam_a, beam_b["beam_label"]: beam_b}; error = 0
    for oy in range(-10, 11):
        for ox in range(-10, 11):
            if ox * ox + oy * oy > 105: continue
            actual = raster_colored(image.getpixel((round(point[0] + ox), round(point[1] + oy))))
            initial = False
            for beam in (beam_a, beam_b):
                dx, dy = normalized_direction(*beam["points"]); nx, ny = -dy, dx; signed = ox * nx + oy * ny
                if min(abs(signed - 7), abs(signed + 7)) <= 1.25: initial = True
            predicted = initial and math.hypot(ox, oy) > 11.0
            front = candidates[front_label]; dx, dy = normalized_direction(*front["points"]); nx, ny = -dy, dx; along = ox * dx + oy * dy; signed = ox * nx + oy * ny
            if abs(along) <= 9.0 and min(abs(signed - 7), abs(signed + 7)) <= 1.5: predicted = True
            if abs(along) <= 9.0 and abs(signed) <= 3.0: predicted = True
            error += int(actual != predicted)
    return error


def png_depth_is_recoverable(row, image_path):
    with Image.open(image_path) as source: image = source.convert("RGB"); image.load()
    lookup = beam_by_label(row)
    for crossing in row["crossings"]:
        a, b = crossing["beam_a"], crossing["beam_b"]
        ea = raster_template_error(image, crossing["point"], lookup[a], lookup[b], a); eb = raster_template_error(image, crossing["point"], lookup[a], lookup[b], b)
        if abs(ea - eb) < 3 or (a if ea < eb else b) != crossing["front_beam"]: return False
    return True


def compact_metadata(row):
    return json.dumps({"dataset_version": row["dataset_version"], "difficulty_score": row["difficulty_score"], "mode": row["mode"], "num_beams": row["num_beams"], "num_crossings": row["num_crossings"], "seed": row["seed"]}, separators=(",", ":"))


def write_tables(root, rows):
    public_fields = ["question_id", "task", "image", "prompt"]
    answer_fields = public_fields + ["groundtruth", "answer_format"]
    final_fields = ["task", "image", "prompt", "groundtruth", "metadata"]
    public, answers, final = [], [], []
    for row in rows:
        for q in row["questions"]:
            base = {"question_id": q["question_id"], "task": TASKS[q["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": q["question_text"]}
            public.append(base)
            answers.append({**base, "groundtruth": str(q["ground_truth"]), "answer_format": q["answer_format"]})
            final.append({"task": base["task"], "image": base["image"], "prompt": base["prompt"], "groundtruth": str(q["ground_truth"]), "metadata": compact_metadata(row)})
    for filename, fields, data in (("question_set.csv", public_fields, public), ("answer_key.csv", answer_fields, answers), ("dataset_final.csv", final_fields, final)):
        with (root / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerows(data)
    with (root / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in final:
            handle.write(json.dumps(item, separators=(",", ":")) + "\n")


def make_sheet(root, rows, filename, indices, columns=5, thumb_w=210, thumb_h=160):
    chosen = [rows[i] for i in indices if i < len(rows)]
    sheet = Image.new("RGB", (columns * thumb_w, math.ceil(len(chosen) / columns) * (thumb_h + 26)), BG)
    draw = ImageDraw.Draw(sheet)
    for pos, row in enumerate(chosen):
        with Image.open(root / row["image_path"]) as source:
            pic = source.convert("RGB"); pic.thumbnail((thumb_w - 8, thumb_h - 16), Image.Resampling.LANCZOS)
        x = pos % columns * thumb_w + (thumb_w - pic.width) // 2
        y = pos // columns * (thumb_h + 26)
        sheet.paste(pic, (x, y))
        draw.text((pos % columns * thumb_w + thumb_w // 2, y + thumb_h + 4), row["id"], font=get_font(11, True), fill=(220, 224, 226), anchor="mm")
    sheet.save(root / filename, "PNG", optimize=True)


def git_commit(root):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def generate(root, count, start_index=1):
    root.mkdir(parents=True, exist_ok=True)
    images = root / "images"; images.mkdir(exist_ok=True)
    rows = []; diagnostics = []
    for position, index in enumerate(range(start_index, start_index + count), 1):
        for recovery_retry in range(100):
            row, diagnostic = make_scene(index, recovery_retry); render(row, root / row["image_path"])
            if png_depth_is_recoverable(row, root / row["image_path"]): break
        else: raise RuntimeError(f"Unable to produce PNG-recoverable scene {index}")
        rows.append(row); diagnostics.append(diagnostic)
        if position % 100 == 0 or position == count:
            print(f"Generated {position}/{count}", flush=True)
    with (root / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows: handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    write_tables(root, rows)
    attempt_values = [d["generation_attempt"] for d in diagnostics]
    attempt_by_configuration = {}
    for beam_count in (5, 6):
        for crossing_count in CROSSING_COUNTS:
            values = [d["generation_attempt"] for d in diagnostics if d["beam_count"] == beam_count and d["crossing_count"] == crossing_count]
            if not values:
                continue
            ordered = sorted(values)
            attempt_by_configuration[f"beams={beam_count},crossings={crossing_count}"] = {"count": len(values), "min": min(values), "p50": ordered[len(ordered)//2], "p95": ordered[min(len(ordered)-1, round(.95*(len(ordered)-1)))], "max": max(values), "mean": sum(values)/len(values)}
    stats = {"images": len(rows), "questions": len(rows) * 5, "modes": dict(Counter(r["mode"] for r in rows)), "beam_counts": dict(Counter(str(r["num_beams"]) for r in rows)), "crossing_counts": dict(Counter(str(r["num_crossings"]) for r in rows)), "level3": dict(Counter(r["reference_front_beam"] for r in rows)), "level5": dict(Counter(r["questions"][4]["ground_truth"] for r in rows)), "generation_attempts": {"count": len(attempt_values), "min": min(attempt_values), "p25": sorted(attempt_values)[len(attempt_values)//4], "p50": sorted(attempt_values)[len(attempt_values)//2], "p75": sorted(attempt_values)[3*len(attempt_values)//4], "p95": sorted(attempt_values)[round(.95*(len(attempt_values)-1))], "max": max(attempt_values), "mean": sum(attempt_values)/len(attempt_values)}, "generation_attempts_by_configuration": attempt_by_configuration, "png_recovery_retry_distribution": dict(Counter(str(d["png_recovery_retry"]) for d in diagnostics))}
    (root / "_generation_diagnostics.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    manifest = {"dataset_version": DATASET_VERSION, "generator_commit_hash": git_commit(root), "record_count": len(rows), "question_count": len(rows) * 5, "constraints": {"crossing_count_targets": list(CROSSING_COUNTS), "minimum_crossing_separation_px": MIN_CROSSING_SEPARATION_PX, "target_separation_tolerance_px": TARGET_SEPARATION_TOLERANCE_PX, "minimum_reference_distance_gap_px": MIN_REFERENCE_DISTANCE_GAP_PX, "target_reference_gap_tolerance_px": TARGET_REFERENCE_GAP_TOLERANCE_PX, "minimum_label_separation_px": MIN_LABEL_SEPARATION_PX, "beam_counts": [5, 6], "constructibility_balance": "1500 possible / 1500 impossible", "impossible_unique_removable_beam": True, "png_depth_order_recoverable_at_every_crossing": True, "all_crossings_have_directed_beam-label depth constraints": True}, "depth_constraint_representation": "directed beam-label front/back relation per projected crossing", "superseded_build": None, "private_build_diagnostics": ["generation_attempt", "png_recovery_retry"]}
    (root / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    make_sheet(root, rows, "review_sheet.png", list(range(min(20, len(rows)))), 5)
    make_sheet(root, rows, "contact_sheet.png", list(range(0, len(rows), max(1, len(rows) // 60)))[:60], 5)
    print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--render-existing", action="store_true", help="Re-render PNGs from the current annotations without changing geometry or questions")
    args = parser.parse_args()
    if args.render_existing:
        rows = [json.loads(line) for line in (args.output_dir / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
        for position, row in enumerate(rows, 1):
            render(row, args.output_dir / row["image_path"])
            if position % 100 == 0 or position == len(rows): print(f"Rendered {position}/{len(rows)}", flush=True)
        make_sheet(args.output_dir, rows, "review_sheet.png", list(range(min(20, len(rows)))), 5)
        make_sheet(args.output_dir, rows, "contact_sheet.png", list(range(0, len(rows), max(1, len(rows) // 60)))[:60], 5)
        return
    if args.sample:
        args.count = 20
        args.output_dir = Path(__file__).resolve().parent / "sample_v4"
    generate(args.output_dir, args.count, args.start_index)


if __name__ == "__main__":
    main()
