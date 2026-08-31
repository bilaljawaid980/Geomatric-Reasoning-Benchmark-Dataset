"""Generate the GRIP gear-train mechanical-reasoning dataset.

The renderer is deliberately schematic. All labels and answers are derived from
an exact tree-structured external-gear model; Fraction is used internally so
multi-mesh ratios are never accumulated approximately.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import deque
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = 600
BACKGROUND = "#FDFAF4"
INK = "#17324D"
GEAR_FILLS = ["#D8E9EE", "#F2D8B3", "#DCE7C8", "#E6D8EA", "#F0D5D1"]
DRIVER_ACCENT = "#C94C3B"
RPM_CHOICES = [30, 40, 45, 50, 60, 72, 90, 120]


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def opposite(direction: str) -> str:
    return "CCW" if direction == "CW" else "CW"


def adjacency(labels: list[str], edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    graph = {label: [] for label in labels}
    for left, right in edges:
        graph[left].append(right)
        graph[right].append(left)
    for label in graph:
        graph[label].sort()
    return graph


def compute_gear_train_rotation(
    gears: list[dict], edges: list[tuple[str, str]], driver_label: str,
    driver_rpm: int | Fraction, driver_direction: str,
) -> dict[str, dict]:
    """Propagate exact speed and direction through a connected gear tree."""
    teeth = {gear["label"]: int(gear["tooth_count"]) for gear in gears}
    graph = adjacency(list(teeth), edges)
    result = {
        driver_label: {
            "direction": driver_direction,
            "rpm_fraction": Fraction(driver_rpm),
        }
    }
    queue = deque([driver_label])
    while queue:
        current = queue.popleft()
        for neighbor in graph[current]:
            candidate_direction = opposite(result[current]["direction"])
            candidate_rpm = (
                result[current]["rpm_fraction"]
                * Fraction(teeth[current], teeth[neighbor])
            )
            if neighbor in result:
                if (
                    result[neighbor]["direction"] != candidate_direction
                    or result[neighbor]["rpm_fraction"] != candidate_rpm
                ):
                    raise ValueError("inconsistent geared cycle")
                continue
            result[neighbor] = {
                "direction": candidate_direction,
                "rpm_fraction": candidate_rpm,
            }
            queue.append(neighbor)
    if set(result) != set(teeth):
        raise ValueError("mesh graph is disconnected")
    return result


def graph_distances(graph: dict[str, list[str]], source: str):
    distance = {source: 0}
    parent = {source: None}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        for neighbor in graph[current]:
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                parent[neighbor] = current
                queue.append(neighbor)
    return distance, parent


def path_to(parent: dict[str, str | None], target: str) -> list[str]:
    path = []
    current = target
    while current is not None:
        path.append(current)
        current = parent[current]
    return list(reversed(path))


def make_scene(index: int) -> dict:
    rng = random.Random(index)
    branching = index % 10 in {0, 3, 7}
    arrangement_type = "branching" if branching else "linear_chain"
    num_gears = rng.choice([4, 5]) if branching else rng.choice([3, 4, 5])
    labels = [chr(ord("A") + i) for i in range(num_gears)]
    tooth_counts = rng.sample(range(8, 41), num_gears)
    gears = [
        {
            "label": label,
            "tooth_count": teeth,
            "radius": round(20.0 + 0.9 * teeth, 2),
            "mesh_partners": [],
        }
        for label, teeth in zip(labels, tooth_counts)
    ]
    if not branching:
        edges = [(labels[i], labels[i + 1]) for i in range(num_gears - 1)]
    elif num_gears == 4:
        edges = [(labels[0], labels[1]), (labels[1], labels[2]), (labels[1], labels[3])]
    else:
        edges = [
            (labels[0], labels[1]), (labels[1], labels[2]),
            (labels[2], labels[3]), (labels[2], labels[4]),
        ]
    graph = adjacency(labels, edges)
    for gear in gears:
        gear["mesh_partners"] = graph[gear["label"]]

    driver_label = labels[0]
    driver_rpm = rng.choice(RPM_CHOICES)
    driver_direction = rng.choice(["CW", "CCW"])
    exact = compute_gear_train_rotation(gears, edges, driver_label, driver_rpm, driver_direction)
    computed_rotation = {
        label: {
            "direction": value["direction"],
            "rpm": round(float(value["rpm_fraction"]), 6),
            "rpm_fraction": (
                f"{value['rpm_fraction'].numerator}/{value['rpm_fraction'].denominator}"
            ),
        }
        for label, value in exact.items()
    }

    distance, parent = graph_distances(graph, driver_label)
    direct_neighbor = rng.choice(graph[driver_label])
    farthest_distance = max(distance.values())
    farthest = sorted(label for label, d in distance.items() if d == farthest_distance)
    level4_target = rng.choice(farthest)
    target_path = path_to(parent, level4_target)

    # Parameter selection, rather than post-hoc answer rejection, gives an exact
    # one-third distribution across increase/decrease/unchanged outcomes.
    mode = index % 3
    if mode == 0:
        changed_gear = driver_label
    elif mode == 1:
        changed_gear = level4_target
    else:
        off_path = sorted(set(labels) - set(target_path))
        use_off_path = bool(off_path) and index % 2 == 0
        changed_gear = rng.choice(off_path) if use_off_path else rng.choice(target_path[1:-1])

    modified_gears = [dict(gear) for gear in gears]
    for gear in modified_gears:
        if gear["label"] == changed_gear:
            gear["tooth_count"] *= 2
            gear["radius"] = round(20.0 + 0.9 * gear["tooth_count"], 2)
    modified = compute_gear_train_rotation(
        modified_gears, edges, driver_label, driver_rpm, driver_direction
    )
    before = exact[level4_target]["rpm_fraction"]
    after = modified[level4_target]["rpm_fraction"]
    speed_change = "increase" if after > before else "decrease" if after < before else "stay the same"
    direction_change = (
        "direction changes"
        if modified[level4_target]["direction"] != exact[level4_target]["direction"]
        else "direction unchanged"
    )

    q3_fastest = index % 2 == 0
    if q3_fastest:
        q3_type = "fastest_gear"
        q3_text = "Which gear rotates the fastest (has the highest RPM)? Answer with the letter."
        q3_answer = min(gears, key=lambda gear: gear["tooth_count"])["label"]
    else:
        q3_type = "most_teeth"
        q3_text = "Which gear in this train has the most teeth? Answer with the letter."
        q3_answer = max(gears, key=lambda gear: gear["tooth_count"])["label"]

    iid = f"gear_train_{index:04d}"
    q4_rpm = f"{float(exact[level4_target]['rpm_fraction']):.1f}"
    q5_answer = f"{speed_change}; {direction_change}"
    questions = [
        {
            "question_id": f"{iid}_q1",
            "question_text": "How many gears are shown in this gear train?",
            "question_type": "gear_count",
            "ground_truth": str(num_gears),
            "answer_format": "number",
            "difficulty_level": 1,
        },
        {
            "question_id": f"{iid}_q2",
            "question_text": (
                f"Gear {direct_neighbor} directly meshes with gear {driver_label} (the driver). "
                f"Does gear {direct_neighbor} rotate in the same direction as the driver, "
                "or the opposite direction?"
            ),
            "question_type": "direct_mesh_direction",
            "ground_truth": "opposite",
            "answer_format": "same or opposite",
            "difficulty_level": 2,
        },
        {
            "question_id": f"{iid}_q3",
            "question_text": q3_text,
            "question_type": q3_type,
            "ground_truth": q3_answer,
            "answer_format": "single uppercase letter",
            "difficulty_level": 3,
        },
        {
            "question_id": f"{iid}_q4",
            "question_text": (
                f"Gear {driver_label} (the driver) rotates at {driver_rpm} RPM. "
                f"What is the RPM of gear {level4_target}, which is {farthest_distance} meshes "
                "from the driver? Answer with a number rounded to 1 decimal place."
            ),
            "question_type": "multi_mesh_target_rpm",
            "ground_truth": q4_rpm,
            "answer_format": "number rounded to 1 decimal place",
            "difficulty_level": 4,
        },
        {
            "question_id": f"{iid}_q5",
            "question_text": (
                f"If gear {changed_gear}'s tooth count were doubled while the driver's RPM "
                f"and direction stayed fixed, would gear {level4_target}'s rotation speed "
                "increase, decrease, or stay the same? Also state whether its rotation "
                "direction would change."
            ),
            "question_type": "double_teeth_counterfactual",
            "ground_truth": q5_answer,
            "answer_format": "'<increase|decrease|stay the same>; <direction changes|direction unchanged>'",
            "difficulty_level": 5,
        },
    ]

    difficulty = 0.28 + 0.09 * num_gears + (0.12 if branching else 0) + 0.04 * farthest_distance
    return {
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": [CANVAS_SIZE, CANVAS_SIZE],
        "seed": index,
        "arrangement_type": arrangement_type,
        "num_gears": num_gears,
        "gears": gears,
        "mesh_edges": [list(edge) for edge in edges],
        "driver_label": driver_label,
        "driver_rpm": driver_rpm,
        "driver_direction": driver_direction,
        "computed_rotation": computed_rotation,
        "level2_neighbor": direct_neighbor,
        "level4_target": level4_target,
        "level4_mesh_distance": farthest_distance,
        "level5_scenario": {
            "changed_gear": changed_gear,
            "target_gear": level4_target,
            "original_tooth_count": next(g["tooth_count"] for g in gears if g["label"] == changed_gear),
            "modified_tooth_count": 2 * next(g["tooth_count"] for g in gears if g["label"] == changed_gear),
        },
        "difficulty_score": round(min(difficulty, 0.98), 4),
        "questions": questions,
    }


def layout(scene: dict) -> dict[str, tuple[float, float]]:
    gears = {g["label"]: g for g in scene["gears"]}
    labels = list(gears)
    if scene["arrangement_type"] == "linear_chain":
        positions = {labels[0]: (0.0, 0.0)}
        for i in range(1, len(labels)):
            a, b = labels[i - 1], labels[i]
            dy = 14.0 if i % 2 else -14.0
            tangent = gears[a]["radius"] + gears[b]["radius"] + 3.0
            dx = math.sqrt(max(tangent * tangent - dy * dy, 1.0))
            x, y = positions[a]
            positions[b] = (x + dx, y + dy)
    else:
        positions = {labels[0]: (0.0, 0.0)}
        if len(labels) == 4:
            branch = labels[1]
            positions[branch] = (gears[labels[0]]["radius"] + gears[branch]["radius"] + 3, 0)
            for label, angle in zip(labels[2:], (-60, 60)):
                d = gears[branch]["radius"] + gears[label]["radius"] + 3
                positions[label] = (
                    positions[branch][0] + d * math.cos(math.radians(angle)),
                    positions[branch][1] + d * math.sin(math.radians(angle)),
                )
        else:
            middle = labels[1]
            branch = labels[2]
            positions[middle] = (gears[labels[0]]["radius"] + gears[middle]["radius"] + 3, 0)
            positions[branch] = (positions[middle][0] + gears[middle]["radius"] + gears[branch]["radius"] + 3, 0)
            for label, angle in zip(labels[3:], (-60, 60)):
                d = gears[branch]["radius"] + gears[label]["radius"] + 3
                positions[label] = (
                    positions[branch][0] + d * math.cos(math.radians(angle)),
                    positions[branch][1] + d * math.sin(math.radians(angle)),
                )
    min_x = min(x - gears[label]["radius"] for label, (x, y) in positions.items())
    max_x = max(x + gears[label]["radius"] for label, (x, y) in positions.items())
    min_y = min(y - gears[label]["radius"] for label, (x, y) in positions.items())
    max_y = max(y + gears[label]["radius"] for label, (x, y) in positions.items())
    shift_x = CANVAS_SIZE / 2 - (min_x + max_x) / 2
    shift_y = 325 - (min_y + max_y) / 2
    return {label: (x + shift_x, y + shift_y) for label, (x, y) in positions.items()}


def arrowhead(draw, tip, angle, color, width):
    length = 14 * width / 2
    spread = math.radians(28)
    p1 = (tip[0] - length * math.cos(angle - spread), tip[1] - length * math.sin(angle - spread))
    p2 = (tip[0] - length * math.cos(angle + spread), tip[1] - length * math.sin(angle + spread))
    draw.polygon([tip, p1, p2], fill=color)


def render(scene: dict, destination: Path):
    scale = 2
    image = Image.new("RGB", (CANVAS_SIZE * scale, CANVAS_SIZE * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    positions = layout(scene)
    gears = {g["label"]: g for g in scene["gears"]}

    def S(point):
        return tuple(int(round(value * scale)) for value in point)

    # A small legend provides only the known input state, never output answers.
    draw.rounded_rectangle(S((55, 42, 545, 105)), radius=18 * scale, fill="#F3EFE6", outline=INK, width=2 * scale)
    header = f"DRIVER: GEAR {scene['driver_label']}    {scene['driver_rpm']} RPM    {scene['driver_direction']}"
    box = draw.textbbox((0, 0), header, font=font(22 * scale, True))
    draw.text(((CANVAS_SIZE * scale - (box[2] - box[0])) / 2, 60 * scale), header, fill=INK, font=font(22 * scale, True))

    for idx, gear in enumerate(scene["gears"]):
        label = gear["label"]
        cx, cy = positions[label]
        radius = gear["radius"]
        tooth_len = 6.0
        for tooth in range(gear["tooth_count"]):
            angle = 2 * math.pi * tooth / gear["tooth_count"]
            p1 = S((cx + (radius - 1) * math.cos(angle), cy + (radius - 1) * math.sin(angle)))
            p2 = S((cx + (radius + tooth_len) * math.cos(angle), cy + (radius + tooth_len) * math.sin(angle)))
            draw.line([p1, p2], fill=INK, width=2 * scale)
        bbox = S((cx - radius, cy - radius, cx + radius, cy + radius))
        outline = DRIVER_ACCENT if label == scene["driver_label"] else INK
        draw.ellipse(bbox, fill=GEAR_FILLS[idx % len(GEAR_FILLS)], outline=outline, width=4 * scale)
        hub = max(7, radius * 0.18)
        draw.ellipse(S((cx - hub, cy - hub, cx + hub, cy + hub)), fill=BACKGROUND, outline=outline, width=3 * scale)
        label_font = font(24 * scale, True)
        label_box = draw.textbbox((0, 0), label, font=label_font)
        draw.text((cx * scale - (label_box[2] - label_box[0]) / 2, (cy - 33) * scale), label, fill=INK, font=label_font)
        teeth_text = f"{gear['tooth_count']}T"
        teeth_font = font(15 * scale, True)
        teeth_box = draw.textbbox((0, 0), teeth_text, font=teeth_font)
        draw.text((cx * scale - (teeth_box[2] - teeth_box[0]) / 2, (cy + 17) * scale), teeth_text, fill=INK, font=teeth_font)

    # Rotation arrow is offset outside the driver so it remains readable.
    dcx, dcy = positions[scene["driver_label"]]
    dr = gears[scene["driver_label"]]["radius"] + 22
    arc_box = S((dcx - dr, dcy - dr, dcx + dr, dcy + dr))
    if scene["driver_direction"] == "CW":
        draw.arc(arc_box, start=205, end=335, fill=DRIVER_ACCENT, width=4 * scale)
        theta = math.radians(335)
        tip = S((dcx + dr * math.cos(theta), dcy + dr * math.sin(theta)))
        arrowhead(draw, tip, theta + math.pi / 2, DRIVER_ACCENT, scale)
    else:
        draw.arc(arc_box, start=205, end=335, fill=DRIVER_ACCENT, width=4 * scale)
        theta = math.radians(205)
        tip = S((dcx + dr * math.cos(theta), dcy + dr * math.sin(theta)))
        arrowhead(draw, tip, theta - math.pi / 2, DRIVER_ACCENT, scale)

    note = "Tooth counts are marked inside each gear. Touching gears are meshed."
    note_font = font(17 * scale)
    note_box = draw.textbbox((0, 0), note, font=note_font)
    draw.text(((CANVAS_SIZE * scale - (note_box[2] - note_box[0])) / 2, 545 * scale), note, fill="#4C5D69", font=note_font)

    image = image.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def write_dataset(output_dir: Path, count: int, start_index: int, render_images: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(start_index, start_index + count):
        scene = make_scene(index)
        image_path = output_dir / scene["image_path"]
        if render_images:
            render(scene, image_path)
        elif not image_path.exists():
            raise FileNotFoundError(f"metadata-only pass requires existing image: {image_path}")
        rows.append(scene)
        if count >= 100 and (index - start_index + 1) % 100 == 0:
            verb = "Processed" if not render_images else "Rendered"
            print(f"{verb} {index - start_index + 1}/{count}", flush=True)
    with (output_dir / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    noun = "metadata rows" if not render_images else "images"
    print(f"Generated {len(rows)} {noun} in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--sample", action="store_true", help="Generate five images in sample_test/")
    parser.add_argument("--metadata-only", action="store_true", help="Regenerate annotations without touching existing PNGs")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output_dir = args.output_dir or (root / "sample_test" if args.sample else root)
    count = 5 if args.sample else args.count
    write_dataset(output_dir, count, args.start_index, render_images=not args.metadata_only)


if __name__ == "__main__":
    main()
