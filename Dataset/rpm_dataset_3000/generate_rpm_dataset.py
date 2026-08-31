"""Generate deterministic synthetic Raven-style Progressive Matrices puzzles."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(items, **_kwargs):
        return items


BG = "#FDFAF4"
DATASET_VERSION = "rpm-2.0.0"
PANEL_BG = "#FFFFFF"
BORDER = "#3F494D"
TEXT = "#15191B"
MUTED = "#596367"
AA = 2

SHAPES = ("circle", "square", "triangle", "pentagon", "hexagon", "star")
SIZES = ("small", "medium", "large")
COLORS = ("#B23A2E", "#C65D00", "#8A6800", "#147A68", "#246EB9", "#7040A0")
ROTATIONS = (0, 45, 90, 135, 180, 225, 270, 315)
COUNTS = (1, 2, 3)
ATTRS = ("shape", "size", "color", "rotation", "count")
DOMAINS = {"shape": SHAPES, "size": SIZES, "color": COLORS, "rotation": ROTATIONS, "count": COUNTS}
RULE_TYPES = (
    "shape_progression",
    "size_progression",
    "color_progression",
    "rotation_progression",
    "count_progression",
    "xor_addition",
    "constant",
)
RULE_ATTR = {
    "shape_progression": "shape",
    "size_progression": "size",
    "color_progression": "color",
    "rotation_progression": "rotation",
    "count_progression": "count",
    "xor_addition": "count",
}


def load_font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(path), size * AA)
    except OSError:  # pragma: no cover
        return ImageFont.load_default()


def rule_target(rule_type: str, occupied: set[str], rng: random.Random) -> str:
    if rule_type != "constant":
        return RULE_ATTR[rule_type]
    candidates = [a for a in ATTRS if a not in occupied]
    return rng.choice(candidates)


def compatible(first: str, second: str) -> bool:
    if first == second:
        return False
    if first != "constant" and second != "constant" and RULE_ATTR[first] == RULE_ATTR[second]:
        return False
    return {first, second} != {"shape_progression", "rotation_progression"}


def choose_rule_types(index: int) -> tuple[str, list[str]]:
    single = (index - 1) % 5 < 2
    first = RULE_TYPES[(index - 1) % len(RULE_TYPES)]
    if single:
        return "single_rule", [first]
    candidates = [rule_type for rule_type in RULE_TYPES if compatible(first, rule_type)]
    # Advancing once per five-image difficulty block produces a balanced rule
    # histogram without accepting/rejecting samples based on their answer.
    second = candidates[((index - 1) // 5) % len(candidates)]
    return "combined_rules", [first, second]


def random_base(rng: random.Random) -> dict:
    return {
        "shape": rng.choice(SHAPES),
        "size": rng.choice(SIZES),
        "color": rng.choice(COLORS),
        "rotation": rng.choice(ROTATIONS),
        "count": rng.choice(COUNTS),
    }


def make_rules(index: int, orientation: str, base: dict, rng: random.Random) -> tuple[str, list[dict]]:
    tier, types = choose_rule_types(index)
    # Reserve every fixed rule target before assigning the flexible target used
    # by a constant rule. This prevents two simultaneous rules from silently
    # governing the same attribute when ``constant`` happens to be selected
    # first.
    fixed_targets = {RULE_ATTR[t] for t in types if t != "constant"}
    constant_targets = iter(rng.sample([a for a in ATTRS if a not in fixed_targets], types.count("constant")))
    rules = []
    for rule_type in types:
        attribute = next(constant_targets) if rule_type == "constant" else RULE_ATTR[rule_type]
        details: dict = {}
        domain = DOMAINS[attribute]
        if rule_type == "shape_progression":
            details = {"start_index": rng.randrange(len(SHAPES)), "step": rng.choice((-1, 1)), "changes_between_sequences": True}
        elif rule_type in {"size_progression", "count_progression"}:
            step = rng.choice((-1, 1))
            details = {"start_index": 0 if step == 1 else 2, "step": step, "cyclic": False}
        elif rule_type in {"color_progression", "rotation_progression"}:
            details = {"start_index": rng.randrange(len(domain)), "step": rng.choice((-1, 1)), "cyclic": True}
        elif rule_type == "xor_addition":
            left = rng.choice(COUNTS)
            middle = rng.choice(COUNTS)
            details = {"left": left, "middle": middle, "operation": "modular_addition_1_to_3"}
        elif rule_type == "constant":
            details = {"value": base[attribute]}
        rules.append({"rule_type": rule_type, "attribute": attribute, "applies_to": orientation, "details": details})
    if any(r["rule_type"] == "rotation_progression" for r in rules):
        base["shape"] = rng.choice(("triangle", "pentagon", "star"))
    return tier, rules


def modular_add(left: int, right: int) -> int:
    return ((left + right - 1) % 3) + 1


def rule_value(rule: dict, group: int, position: int):
    rule_type = rule["rule_type"]
    attribute = rule["attribute"]
    details = rule["details"]
    domain = DOMAINS[attribute]
    if rule_type == "shape_progression":
        return domain[(details["start_index"] + details["step"] * group) % len(domain)]
    if rule_type in {"size_progression", "count_progression", "color_progression", "rotation_progression"}:
        raw = details["start_index"] + details["step"] * position
        return domain[raw % len(domain)]
    if rule_type == "xor_addition":
        if position == 0:
            return details["left"]
        if position == 1:
            return details["middle"]
        values = [details["left"], details["middle"]]
        while len(values) <= position:
            values.append(modular_add(values[-2], values[-1]))
        return values[position]
    if rule_type == "constant":
        return details["value"]
    raise KeyError(rule_type)


def apply_rules(base: dict, rules: list[dict], row: int, column: int) -> dict:
    panel = dict(base)
    for rule in rules:
        group, position = (row, column) if rule["applies_to"] == "row" else (column, row)
        panel[rule["attribute"]] = rule_value(rule, group, position)
    return panel


def different_value(attribute: str, current, rng: random.Random, salt: int = 0):
    domain = list(DOMAINS[attribute])
    alternatives = [v for v in domain if v != current]
    return alternatives[(rng.randrange(len(alternatives)) + salt) % len(alternatives)]


def violated_rule_name(attribute: str, rules: list[dict]) -> str:
    for rule in rules:
        if rule["attribute"] == attribute:
            return rule["rule_type"]
    return f"background_constant:{attribute}"


def make_distractors(correct: dict, rules: list[dict], rng: random.Random) -> tuple[list[dict], list[dict]]:
    candidates: list[tuple[dict, dict]] = []
    seen = {tuple(correct[a] for a in ATTRS)}

    def add(panel: dict, violation_type: str, changed: list[str]) -> bool:
        key = tuple(panel[a] for a in ATTRS)
        if key in seen:
            return False
        seen.add(key)
        claim = {
            "violation_type": violation_type,
            "violated_attributes": changed,
            "violates_rule": ",".join(violated_rule_name(a, rules) for a in changed),
        }
        candidates.append((panel, claim))
        return True

    # Near misses alter background constants first, preserving two distinct
    # active-rule alternatives for the deliberately wrong-progression group.
    active_set = {r["attribute"] for r in rules}
    priority = [a for a in ATTRS if a not in active_set] + [r["attribute"] for r in rules]
    for salt, attribute in enumerate(priority[:3]):
        panel = dict(correct)
        panel[attribute] = different_value(attribute, panel[attribute], rng, salt)
        add(panel, "single_attribute", [attribute])

    active = [r["attribute"] for r in rules]
    attempts = 0
    while sum(c[1]["violation_type"] == "wrong_progression" for c in candidates) < 2 and attempts < 50:
        attribute = active[attempts % len(active)]
        panel = dict(correct)
        panel[attribute] = different_value(attribute, panel[attribute], rng, attempts)
        add(panel, "wrong_progression", [attribute])
        attempts += 1

    attempts = 0
    while len(candidates) < 7 and attempts < 100:
        changed = rng.sample(list(ATTRS), 2 + int(attempts % 3 == 0))
        panel = dict(correct)
        for salt, attribute in enumerate(changed):
            panel[attribute] = different_value(attribute, panel[attribute], rng, attempts + salt)
        add(panel, "random", changed)
        attempts += 1
    if len(candidates) != 7:
        raise RuntimeError("Could not construct seven unique distractors")
    return [p for p, _ in candidates], [c for _, c in candidates]


def classification(correct: dict, distractor: dict) -> str:
    if distractor["shape"] == correct["shape"] and distractor["color"] != correct["color"]:
        return "correct shape but wrong color"
    if distractor["color"] == correct["color"] and distractor["shape"] != correct["shape"]:
        return "correct color but wrong shape"
    return "wrong in some other way"


def extrapolated(rule: dict, group: int = 2):
    # Counts are quantities, not categorical labels. Their Level-4 extension
    # must therefore continue the observed numeric sequence without wrapping
    # through the display-only 1..3 count domain.
    if rule["attribute"] == "count":
        details = rule["details"]
        if rule["rule_type"] == "count_progression":
            return COUNTS[details["start_index"]] + details["step"] * 3
        if rule["rule_type"] == "xor_addition":
            third = modular_add(details["left"], details["middle"])
            return third + (third - details["middle"])
    return rule_value(rule, group, 3)


def make_questions(record: dict, rng: random.Random) -> list[dict]:
    iid = record["id"]
    correct = record["grid_panels"][8]["attributes"]
    questions = [
        {"question_id": f"{iid}_q1", "question_text": "How many shapes appear in the panel at row 1, column 1 (top-left)?", "question_type": "top_left_shape_count", "ground_truth": str(record["grid_panels"][0]["attributes"]["count"]), "answer_format": "numeric", "difficulty_level": 1},
        {"question_id": f"{iid}_q2", "question_text": "Which of the 8 numbered choices correctly completes the pattern in the missing panel? Answer with the number.", "question_type": "correct_choice", "ground_truth": str(record["correct_answer_index"]), "answer_format": "choice_number", "difficulty_level": 2},
    ]
    changing = [r for r in record["active_rules"] if r["rule_type"] in {"size_progression", "color_progression", "rotation_progression", "count_progression"}]
    if len(changing) == 1 and rng.random() < 0.5:
        rule = changing[0]
        direction = "from left to right within each row" if rule["applies_to"] == "row" else "from top to bottom within each column"
        q3 = {"question_id": f"{iid}_q3", "question_text": f"What attribute changes consistently {direction}: shape, size, color, rotation, or count? Answer with one word.", "question_type": "consistent_attribute", "reference_attribute": rule["attribute"], "ground_truth": rule["attribute"], "answer_format": "attribute_name", "difficulty_level": 3}
    else:
        wrong = rng.choice([c for c in record["answer_choices"] if not c["is_correct"]])
        q3 = {"question_id": f"{iid}_q3", "question_text": f"Choice {wrong['choice_index']} is wrong. Does it have the correct shape but wrong color, the correct color but wrong shape, or is it wrong in some other way?", "question_type": "distractor_classification", "reference_choice": wrong["choice_index"], "ground_truth": classification(correct, wrong["attributes"]), "answer_format": "classification_phrase", "difficulty_level": 3}
    questions.append(q3)

    level4_pool = ["shape_match"]
    if record["difficulty_tier"] == "combined_rules":
        level4_pool.append("name_rules")
    if record["active_rules"]:
        level4_pool.append("extrapolate")
    choice = rng.choice(level4_pool)
    if choice == "name_rules":
        attrs = [r["attribute"] for r in record["active_rules"]]
        q4 = {"question_id": f"{iid}_q4", "question_text": "This puzzle uses two rules simultaneously. Name both attributes governed by those rules. Answer with two words separated by 'and'.", "question_type": "combined_rule_attributes", "ground_truth": " and ".join(attrs), "answer_format": "two_attributes", "difficulty_level": 4}
    elif choice == "extrapolate":
        rule = rng.choice(record["active_rules"])
        direction = "row" if rule["applies_to"] == "row" else "column"
        value = extrapolated(rule)
        q4 = {"question_id": f"{iid}_q4", "question_text": f"If the pattern in the final {direction} continued for one more panel beyond the missing one, what would that panel's {rule['attribute']} be?", "question_type": "rule_extrapolation", "reference_rule_type": rule["rule_type"], "reference_attribute": rule["attribute"], "ground_truth": str(value), "answer_format": "attribute_value", "difficulty_level": 4}
    else:
        count = sum(c["attributes"]["shape"] == correct["shape"] for c in record["answer_choices"])
        q4 = {"question_id": f"{iid}_q4", "question_text": "How many of the 8 answer choices share the same shape type as the correct answer, even though most of them are wrong for other reasons? Answer with a number.", "question_type": "choices_matching_correct_shape", "ground_truth": str(count), "answer_format": "numeric", "difficulty_level": 4}
    questions.append(q4)
    matching = sum(c["attributes"]["shape"] == correct["shape"] for c in record["answer_choices"])
    questions.append({"question_id": f"{iid}_q5", "question_text": "If a ninth, incorrect choice with the same shape type as the correct answer but a wrong color were added, how many choices would then share the correct shape type?", "question_type": "add_same_shape_distractor", "ground_truth": str(matching + 1), "answer_format": "numeric", "difficulty_level": 5})
    return questions


def regular_polygon(cx, cy, radius, sides, rotation):
    start = math.radians(rotation - 90)
    return [(cx + radius * math.cos(start + 2 * math.pi * i / sides), cy + radius * math.sin(start + 2 * math.pi * i / sides)) for i in range(sides)]


def star_points(cx, cy, radius, rotation):
    points = []
    start = math.radians(rotation - 90)
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.43
        angle = start + math.pi * i / 5
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def draw_one_shape(draw, shape, center, radius, color, rotation):
    cx, cy = center
    width = max(2, AA)
    if shape == "circle":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color, outline="#111719", width=width)
    elif shape == "square":
        draw.polygon(regular_polygon(cx, cy, radius, 4, rotation + 45), fill=color, outline="#111719")
    elif shape == "triangle":
        draw.polygon(regular_polygon(cx, cy, radius, 3, rotation), fill=color, outline="#111719")
    elif shape == "pentagon":
        draw.polygon(regular_polygon(cx, cy, radius, 5, rotation), fill=color, outline="#111719")
    elif shape == "hexagon":
        draw.polygon(regular_polygon(cx, cy, radius, 6, rotation), fill=color, outline="#111719")
    else:
        draw.polygon(star_points(cx, cy, radius, rotation), fill=color, outline="#111719")


def draw_panel(draw, box, attributes, missing=False, label=None):
    x0, y0, x1, y1 = [int(v * AA) for v in box]
    draw.rounded_rectangle((x0, y0, x1, y1), radius=5 * AA, fill=PANEL_BG, outline=BORDER, width=1 * AA)
    if label is not None:
        draw.text((x0 + 7 * AA, y0 + 5 * AA), str(label), fill=TEXT, font=load_font(11, True), anchor="la")
    if missing:
        draw.text(((x0 + x1) / 2, (y0 + y1) / 2), "?", fill=MUTED, font=load_font(34, True), anchor="mm")
        return
    count = int(attributes["count"])
    available_w = (x1 - x0) / AA - 14
    base_radius = {"small": 10, "medium": 15, "large": 20}[attributes["size"]]
    radius = min(base_radius, available_w / (2.5 * count)) * AA
    spacing = min(2.25 * radius, available_w * AA / max(1, count))
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2 + (5 * AA if label is not None else 0)
    starts = center_x - spacing * (count - 1) / 2
    for i in range(count):
        draw_one_shape(draw, attributes["shape"], (starts + i * spacing, center_y), radius, attributes["color"], attributes["rotation"])


def render(path: Path, size: tuple[int, int], panels: list[dict], choices: list[dict]):
    width, height = size
    image = Image.new("RGB", (width * AA, height * AA), BG)
    draw = ImageDraw.Draw(image)
    draw.text((width * AA / 2, 8 * AA), "PROGRESSIVE MATRIX PUZZLE", fill=TEXT, font=load_font(16, True), anchor="ma")
    grid_size = min(330, width - 120)
    cell = grid_size / 3
    gx = (width - grid_size) / 2
    gy = 34
    gap = 5
    for i, panel in enumerate(panels):
        row, col = divmod(i, 3)
        box = (gx + col * cell + gap / 2, gy + row * cell + gap / 2, gx + (col + 1) * cell - gap / 2, gy + (row + 1) * cell - gap / 2)
        draw_panel(draw, box, panel["attributes"], missing=i == 8)
    draw.text((width * AA / 2, (gy + grid_size + 7) * AA), "Choose the panel that completes the pattern", fill=MUTED, font=load_font(10), anchor="ma")
    margin, choice_gap = 18, 7
    choice_w = (width - 2 * margin - 3 * choice_gap) / 4
    choice_h = (height - (gy + grid_size + 34) - 18 - choice_gap) / 2
    start_y = gy + grid_size + 30
    for i, choice in enumerate(choices):
        row, col = divmod(i, 4)
        box = (margin + col * (choice_w + choice_gap), start_y + row * (choice_h + choice_gap), margin + col * (choice_w + choice_gap) + choice_w, start_y + row * (choice_h + choice_gap) + choice_h)
        draw_panel(draw, box, choice["attributes"], label=choice["choice_index"])
    image.resize((width, height), Image.Resampling.LANCZOS).save(path, "PNG")


def generate_one(index: int, images_dir: Path, output_index: int | None = None) -> dict:
    rng = random.Random(index)
    orientation = "column" if (index - 1) % 10 < 3 else "row"
    base = random_base(rng)
    tier, rules = make_rules(index, orientation, base, rng)
    panels = []
    for row in range(3):
        for column in range(3):
            panels.append({"row": row + 1, "column": column + 1, "attributes": apply_rules(base, rules, row, column), "shown_in_image": not (row == 2 and column == 2)})
    correct = panels[8]["attributes"]
    shown = [p["attributes"] for p in panels[:8]]
    rows = [[panels[r * 3 + c]["attributes"] for c in range(3)] for r in range(3)]
    if any(correct == panel for panel in shown):
        raise ValueError("copy-solvable missing panel")
    if len({json.dumps(row, sort_keys=True) for row in rows}) < 3:
        raise ValueError("identical matrix rows")
    if not any(len({panels[r * 3 + c]["attributes"][a] for r in range(3)}) > 1 for a in ATTRS for c in range(3)):
        raise ValueError("no attribute varies across rows")
    distractors, claims = make_distractors(correct, rules, rng)
    all_panels = [correct] + distractors
    rng.shuffle(all_panels)
    choices = []
    violations = []
    for choice_index, attributes in enumerate(all_panels, 1):
        is_correct = attributes == correct
        choices.append({"choice_index": choice_index, "attributes": attributes, "is_correct": is_correct})
        if not is_correct:
            original_index = next(i for i, panel in enumerate(distractors) if panel == attributes)
            violations.append({"choice_index": choice_index, **claims[original_index]})
    correct_index = next(c["choice_index"] for c in choices if c["is_correct"])
    iid = f"rpm_{(output_index or index):04d}"
    active_attrs = {r["attribute"] for r in rules}
    size = (rng.randint(620, 650), rng.randint(620, 650))
    difficulty = round(min(1.0, 0.35 + 0.3 * (tier == "combined_rules") + 0.12 * (orientation == "column") + 0.08 * any(r["rule_type"] == "xor_addition" for r in rules) + 0.08 * correct["count"] / 3), 4)
    record = {
        "id": iid,
        "dataset_version": DATASET_VERSION,
        "image_path": f"images/{iid}.png",
        "canvas_size": list(size),
        "seed": index,
        "difficulty_score": difficulty,
        "difficulty_tier": tier,
        "num_active_rules": len(rules),
        "orientation": orientation,
        "frame_conventions": {"row": "top_to_bottom", "column": "left_to_right", "missing_panel": [3, 3]},
        "active_rules": rules,
        "background_constants": {a: base[a] for a in ATTRS if a not in active_attrs},
        "grid_panels": panels,
        "answer_choices": choices,
        "correct_answer_index": correct_index,
        "distractor_violations": sorted(violations, key=lambda x: x["choice_index"]),
    }
    record["questions"] = make_questions(record, rng)
    render(images_dir / f"{iid}.png", size, panels, choices)
    return record


def generate_dataset(count: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    images = output_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    with (output_dir / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        seed = 1
        accepted = 0
        progress = tqdm(range(count), desc="Generating RPM puzzles")
        while accepted < count:
            try:
                record = generate_one(seed, images, accepted + 1)
            except ValueError:
                seed += 1
                continue
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            accepted += 1
            seed += 1
            if hasattr(progress, "update"):
                progress.update(1)
        if hasattr(progress, "close"):
            progress.close()
    print(f"Generated {count} RPM puzzles in {output_dir.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3000)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    # A bare --sample must never overwrite a completed full dataset.
    output_dir = args.output_dir or (root / "sample_output" if args.sample else root)
    generate_dataset(5 if args.sample else args.n, output_dir)


if __name__ == "__main__":
    main()
