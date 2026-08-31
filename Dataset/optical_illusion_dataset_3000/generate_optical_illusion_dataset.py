"""Generate deterministic Müller-Lyer, Ponzo, and Ebbinghaus illusion puzzles."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKGROUND = "#FDFAF4"
TARGET = "#174A69"
TARGET_FILL = "#E4F0F4"
CONTEXT = "#626B73"
LABEL = "#17232D"
SCHEDULE = ("muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo", "ebbinghaus", "muller_lyer", "ponzo")
TYPE_PER_BLOCK = Counter(SCHEDULE)


def font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def half_up(value: Fraction) -> int:
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def type_and_ordinal(index: int):
    zero = index - 1
    block, position = divmod(zero, len(SCHEDULE))
    illusion_type = SCHEDULE[position]
    ordinal = block * TYPE_PER_BLOCK[illusion_type] + sum(value == illusion_type for value in SCHEDULE[:position])
    return illusion_type, ordinal


def primitive_value(geometry: dict) -> int:
    if geometry["kind"] == "line":
        return geometry["x2"] - geometry["x1"]
    return geometry["diameter"]


def actual_answer(a: int, b: int) -> str:
    if a == b:
        return "equal"
    return "A" if a > b else "B"


def level5_answer(appearance: str, actual: str) -> str:
    changed = actual == "equal" or actual != appearance
    truth = "actually equal" if actual == "equal" else f"element {actual} is actually bigger"
    return f"{'yes' if changed else 'no'}; {truth}"


def build_scene(index: int):
    rng = random.Random(index)
    illusion_type, ordinal = type_and_ordinal(index)
    canvas = rng.randint(500, 550)
    equal = ordinal % 2 == 0
    matches = None if equal else ((ordinal // 2) % 2 == 0)
    appearance = rng.choice(("A", "B"))
    actual_bigger = None if equal else (appearance if matches else ("B" if appearance == "A" else "A"))

    if illusion_type in ("muller_lyer", "ponzo"):
        base = rng.randint(116, 148)
    else:
        base = rng.randint(44, 58)
    valid_differences = [delta for delta in range(1, base + 1) if Fraction(5) <= Fraction(delta * 100, base) <= Fraction(20)]
    difference = 0 if equal else rng.choice(valid_differences)
    values = {"A": base, "B": base}
    if actual_bigger:
        values[actual_bigger] += difference

    center_x = canvas // 2
    construction: dict = {}
    if illusion_type == "muller_lyer":
        ys = {"A": 180, "B": canvas - 180}
        contexts = {appearance: "outward", ("B" if appearance == "A" else "A"): "inward"}
        elements = {}
        for label in ("A", "B"):
            length = values[label]
            x1 = center_x - length // 2
            elements[label] = {"kind": "line", "x1": x1, "x2": x1 + length, "y": ys[label]}
        construction = {"elements": elements, "contexts": contexts, "fin_length": rng.randint(36, 46), "fin_angle_degrees": rng.randint(38, 48)}
    elif illusion_type == "ponzo":
        upper = appearance
        lower = "B" if appearance == "A" else "A"
        ys = {upper: 185, lower: canvas - 170}
        elements = {}
        for label in ("A", "B"):
            length = values[label]
            x1 = center_x - length // 2
            elements[label] = {"kind": "line", "x1": x1, "x2": x1 + length, "y": ys[label]}
        construction = {"elements": elements, "contexts": {upper: "near_convergence", lower: "far_from_convergence"}, "vanishing_y": 68, "track_top_half_width": rng.randint(42, 52), "track_bottom_half_width": rng.randint(205, 220), "track_bottom_y": canvas - 42}
    else:
        # A 150 px inset keeps the largest allowed inducer ring fully inside
        # even the minimum 500 px canvas, including antialiasing clearance.
        xs = {"A": 150, "B": canvas - 150}
        contexts = {appearance: "small_surrounds", ("B" if appearance == "A" else "A"): "large_surrounds"}
        elements = {label: {"kind": "circle", "cx": xs[label], "cy": canvas // 2, "diameter": values[label]} for label in ("A", "B")}
        small_ratio = Fraction(rng.randint(35, 45), 100)
        large_ratio = Fraction(rng.randint(130, 150), 100)
        construction = {"elements": elements, "contexts": contexts, "small_context_ratio_fraction": fraction_text(small_ratio), "large_context_ratio_fraction": fraction_text(large_ratio), "context_circle_count": 6}

    a = primitive_value(construction["elements"]["A"])
    b = primitive_value(construction["elements"]["B"])
    percent = Fraction(abs(a - b) * 100, min(a, b)) if a != b else Fraction(0)
    actual = actual_answer(a, b)
    noun = "target line segments" if illusion_type != "ebbinghaus" else "center circles"
    measure = "longer" if illusion_type != "ebbinghaus" else "bigger"
    context_words = {"muller_lyer": "fins", "ponzo": "converging lines", "ebbinghaus": "surrounding circles"}[illusion_type]
    iid = f"optical_illusion_{index:04d}"
    questions = [
        {"question_id": f"{iid}_q1", "difficulty_level": 1, "question_type": "comparison_element_count", "question_text": f"How many {noun} are being compared in this image?", "ground_truth": "2", "answer_format": "integer"},
        {"question_id": f"{iid}_q2", "difficulty_level": 2, "question_type": "contextual_apparent_size", "question_text": f"Because of the {context_words}, which element would a typical human viewer perceive as {measure}—element A or element B? Answer with the letter.", "ground_truth": appearance, "answer_format": "A or B"},
        {"question_id": f"{iid}_q3", "difficulty_level": 3, "question_type": "actual_size_comparison", "question_text": f"Ignoring the surrounding context, measure the actual {'length' if illusion_type != 'ebbinghaus' else 'diameter'} of element A and element B. Are they equal, or is one actually {measure}? Answer 'equal', 'A', or 'B'.", "ground_truth": actual, "answer_format": "equal, A, or B"},
        {"question_id": f"{iid}_q4", "difficulty_level": 4, "question_type": "true_size_percent_difference", "question_text": "By approximately what percentage do the two elements' TRUE sizes differ (0% if equal)? Answer with a number in curly brackets, e.g. {12}.", "ground_truth": str(half_up(percent)), "answer_format": "integer percentage in curly brackets"},
        {"question_id": f"{iid}_q5", "difficulty_level": 5, "question_type": "remove_illusion_context", "question_text": f"If the visual context ({context_words}) were removed entirely and only the two bare elements remained, would your answer to 'which one is bigger' change from what the illusion suggests? Answer yes or no, and state which is actually bigger without the context.", "ground_truth": level5_answer(appearance, actual), "answer_format": "yes/no; actual relation"},
    ]
    difficulty = round(0.35 + 0.12 * (not equal) + 0.14 * (matches is False) + 0.08 * (illusion_type == "ebbinghaus") + 0.08 * float(percent / 20), 4)
    return {"id": iid, "image_path": f"images/{iid}.png", "canvas_size": [canvas, canvas], "seed": index, "dataset_version": "optical-illusion-3.0.0", "illusion_type": illusion_type, "element_a_true_value": a, "element_b_true_value": b, "are_actually_equal": equal, "illusion_direction": f"{appearance}_appears_{measure}", "illusion_appears_larger_element": appearance, "matches_illusion_direction": matches, "percent_difference": float(percent), "percent_difference_fraction": fraction_text(percent), "percent_difference_definition": "abs(A-B)/min(A,B)*100", "construction": construction, "difficulty_score": difficulty, "questions": questions}


def S(value, scale):
    if isinstance(value, tuple):
        return tuple(int(round(item * scale)) for item in value)
    return int(round(value * scale))


def draw_label(draw, label, x, y, scale):
    draw.text((S(x, scale), S(y, scale)), label, fill=LABEL, font=font(21 * scale, True), anchor="mm")


def draw_muller_lyer(draw, scene, scale):
    data = scene["construction"]; fin = data["fin_length"]; angle = math.radians(data["fin_angle_degrees"])
    dx, dy = fin * math.cos(angle), fin * math.sin(angle)
    for label in ("A", "B"):
        element = data["elements"][label]; x1, x2, y = element["x1"], element["x2"], element["y"]
        sign = -1 if data["contexts"][label] == "outward" else 1
        draw.line([S((x1, y), scale), S((x1 + sign * dx, y - dy), scale)], fill=CONTEXT, width=4 * scale)
        draw.line([S((x1, y), scale), S((x1 + sign * dx, y + dy), scale)], fill=CONTEXT, width=4 * scale)
        draw.line([S((x2, y), scale), S((x2 - sign * dx, y - dy), scale)], fill=CONTEXT, width=4 * scale)
        draw.line([S((x2, y), scale), S((x2 - sign * dx, y + dy), scale)], fill=CONTEXT, width=4 * scale)
        draw.line([S((x1, y), scale), S((x2, y), scale)], fill=TARGET, width=5 * scale)
        draw_label(draw, label, x1 - 70, y, scale)


def draw_ponzo(draw, scene, scale):
    data = scene["construction"]; canvas = scene["canvas_size"][0]; cx = canvas / 2; vy = data["vanishing_y"]; by = data["track_bottom_y"]
    for direction in (-1, 1):
        draw.line([S((cx + direction * data["track_top_half_width"], vy), scale), S((cx + direction * data["track_bottom_half_width"], by), scale)], fill=CONTEXT, width=5 * scale)
    for fraction in (0.18, 0.36, 0.54, 0.72, 0.9):
        y = vy + fraction * (by - vy); half = data["track_top_half_width"] + fraction * (data["track_bottom_half_width"] - data["track_top_half_width"])
        draw.line([S((cx - half, y), scale), S((cx + half, y), scale)], fill="#B7B9B7", width=2 * scale)
    for label in ("A", "B"):
        element = data["elements"][label]; x1, x2, y = element["x1"], element["x2"], element["y"]
        draw.line([S((x1, y), scale), S((x2, y), scale)], fill=TARGET, width=6 * scale)
        draw.ellipse([S((x1 - 3, y - 3), scale), S((x1 + 3, y + 3), scale)], fill=TARGET)
        draw.ellipse([S((x2 - 3, y - 3), scale), S((x2 + 3, y + 3), scale)], fill=TARGET)
        draw_label(draw, label, x1 - 36, y, scale)


def draw_ebbinghaus(draw, scene, scale):
    data = scene["construction"]
    for label in ("A", "B"):
        target = data["elements"][label]; d = target["diameter"]; context = data["contexts"][label]
        ratio = Fraction(data["small_context_ratio_fraction"] if context == "small_surrounds" else data["large_context_ratio_fraction"])
        cd = float(Fraction(d) * ratio); ring = d / 2 + cd / 2 + (13 if context == "small_surrounds" else 9)
        for i in range(data["context_circle_count"]):
            theta = 2 * math.pi * i / data["context_circle_count"] - math.pi / 2; cx = target["cx"] + ring * math.cos(theta); cy = target["cy"] + ring * math.sin(theta)
            draw.ellipse([S((cx - cd / 2, cy - cd / 2), scale), S((cx + cd / 2, cy + cd / 2), scale)], fill=BACKGROUND, outline=CONTEXT, width=3 * scale)
        draw.ellipse([S((target["cx"] - d / 2, target["cy"] - d / 2), scale), S((target["cx"] + d / 2, target["cy"] + d / 2), scale)], fill=TARGET_FILL, outline=TARGET, width=5 * scale)
        draw_label(draw, label, target["cx"], target["cy"] + ring + cd / 2 + 26, scale)


def render(scene: dict, destination: Path):
    scale = 2; canvas = scene["canvas_size"][0]
    image = Image.new("RGB", (canvas * scale, canvas * scale), BACKGROUND); draw = ImageDraw.Draw(image)
    {"muller_lyer": draw_muller_lyer, "ponzo": draw_ponzo, "ebbinghaus": draw_ebbinghaus}[scene["illusion_type"]](draw, scene, scale)
    image.resize((canvas, canvas), Image.Resampling.LANCZOS).save(destination, "PNG", optimize=True)


def generate(output: Path, count: int, start_index: int, render_images: bool):
    output.mkdir(parents=True, exist_ok=True); images = output / "images"; images.mkdir(exist_ok=True)
    records = []
    for position, index in enumerate(range(start_index, start_index + count), 1):
        scene = build_scene(index); records.append(scene)
        if render_images: render(scene, images / Path(scene["image_path"]).name)
        if render_images and (position % 100 == 0 or position == count): print(f"Rendered {position}/{count}", flush=True)
    with (output / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records: handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    type_counts = Counter(row["illusion_type"] for row in records); equal_counts = {kind: Counter(row["are_actually_equal"] for row in records if row["illusion_type"] == kind) for kind in type_counts}
    stats = {"images": len(records), "illusion_types": dict(type_counts), "equal_by_type": {key: {str(k).lower(): v for k, v in value.items()} for key, value in equal_counts.items()}, "unequal_alignment_by_type": {kind: dict(Counter("matches" if row["matches_illusion_direction"] else "contradicts" for row in records if row["illusion_type"] == kind and not row["are_actually_equal"])) for kind in type_counts}}
    (output / "generation_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--count", type=int, default=3000); parser.add_argument("--start-index", type=int, default=1); parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent); parser.add_argument("--metadata-only", action="store_true"); parser.add_argument("--sample", action="store_true"); args = parser.parse_args()
    if args.sample: args.output_dir = Path(__file__).resolve().parent / "sample_test"; args.count = 5
    generate(args.output_dir, args.count, args.start_index, not args.metadata_only)


if __name__ == "__main__": main()
