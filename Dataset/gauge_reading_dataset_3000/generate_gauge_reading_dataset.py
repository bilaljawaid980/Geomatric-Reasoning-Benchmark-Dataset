"""Generate 3,000 deterministic analog-gauge reading images and annotations."""

from __future__ import annotations

import argparse
import json
import math
import random
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS = 600
BACKGROUND = "#FDFAF4"
FACE = "#FFFDF9"
INK = "#18344B"
MINOR = "#7E8C94"
NEEDLE = "#137C78"
DANGER = "#C8433A"
CENTER = (300, 326)
RADIUS = 238
NEEDLE_LENGTH = 174

CONFIGS = (
    {"instrument_type": "speedometer", "unit": "km/h", "min": 0, "max": 200, "tick": 20, "start": -135, "sweep": 270},
    {"instrument_type": "pressure gauge", "unit": "psi", "min": 0, "max": 100, "tick": 10, "start": -135, "sweep": 270},
    {"instrument_type": "analog meter", "unit": "units", "min": 0, "max": 60, "tick": 5, "start": -90, "sweep": 180},
    {"instrument_type": "temperature dial", "unit": "°C", "min": -20, "max": 120, "tick": 20, "start": -135, "sweep": 270},
    {"instrument_type": "pressure gauge", "unit": "bar", "min": 0, "max": 10, "tick": 1, "start": -135, "sweep": 270},
)


def font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def value_angle(value: Fraction, minimum: Fraction, maximum: Fraction, start: Fraction, sweep: Fraction):
    return start + (value - minimum) * sweep / (maximum - minimum)


def round_half_up(value: Fraction):
    if value >= 0:
        return (2 * value.numerator + value.denominator) // (2 * value.denominator)
    return -round_half_up(-value)


def round_to_tick(value: Fraction, minimum: Fraction, interval: Fraction):
    steps = round_half_up((value - minimum) / interval)
    return minimum + steps * interval


def clean_number(value: Fraction):
    return str(value.numerator) if value.denominator == 1 else f"{float(value):g}"


def ceil_fraction(value: Fraction):
    return -((-value.numerator) // value.denominator)


def fraction_string(value: Fraction):
    return f"{value.numerator}/{value.denominator}"


def endpoint(angle: Fraction | float, length: float, center=CENTER):
    radians = math.radians(float(angle))
    return center[0] + length * math.sin(radians), center[1] - length * math.cos(radians)


def arc_points(start: Fraction | float, sweep: Fraction | float, radius: float, count: int = 181):
    return [endpoint(float(start) + float(sweep) * i / (count - 1), radius) for i in range(count)]


def make_scene(index: int):
    rng = random.Random(index)
    config = dict(CONFIGS[(index - 1) % len(CONFIGS)])
    minimum = Fraction(config["min"])
    maximum = Fraction(config["max"])
    interval = Fraction(config["tick"])
    start = Fraction(config["start"])
    sweep = Fraction(config["sweep"])
    full_range = maximum - minimum

    # Exactly 40% of images carry a danger band. Thresholds align to a labeled
    # tick and occupy the upper 20% or 30% of the scale.
    has_danger = index % 5 in (0, 1)
    if has_danger:
        target_steps = full_range * Fraction(7 if index % 2 else 8, 10) / interval
        threshold = minimum + interval * ceil_fraction(target_steps)
    else:
        threshold = None

    # Half-tick resolution makes interpolation meaningful. Index parity selects
    # the lower/upper half directly; the midpoint and a marked threshold are
    # excluded because their requested binary relations would be ambiguous.
    candidates = [minimum + interval * Fraction(step, 2) for step in range(1, int(2 * full_range / interval))]
    midpoint = (minimum + maximum) / 2
    relation_candidates = [
        value for value in candidates
        if (value < midpoint if index % 2 == 0 else value > midpoint) and value != threshold
    ]
    needle_value = rng.choice(relation_candidates)
    needle_angle = value_angle(needle_value, minimum, maximum, start, sweep)
    rounded_value = round_to_tick(needle_value, minimum, interval)
    projected_value = needle_value + full_range / 4
    projected_exceeds = projected_value > maximum

    if threshold is None:
        danger_answer = "no danger zone marked"
    elif needle_value > threshold:
        danger_answer = f"yes; exceeds threshold by {clean_number(needle_value - threshold)}"
    else:
        danger_answer = "no"
    projected_answer = f"{'yes' if projected_exceeds else 'no'}; new value {clean_number(projected_value)}"

    iid = f"gauge_reading_{index:04d}"
    questions = [
        {"question_id": f"{iid}_q1", "difficulty_level": 1, "question_type": "minimum_scale_value", "question_text": "What is the minimum value shown on this gauge's scale?", "ground_truth": clean_number(minimum), "answer_format": "number"},
        {"question_id": f"{iid}_q2", "difficulty_level": 2, "question_type": "lower_or_upper_half", "question_text": "Is the needle pointing to a value in the lower half or upper half of the gauge's range? Answer 'lower half' or 'upper half'.", "ground_truth": "lower half" if needle_value < midpoint else "upper half", "answer_format": "lower half or upper half"},
        {"question_id": f"{iid}_q3", "difficulty_level": 3, "question_type": "needle_value_nearest_tick", "question_text": "What value is the needle pointing to, rounded to the nearest tick mark interval?", "ground_truth": clean_number(rounded_value), "answer_format": "number using half-up rounding"},
        {"question_id": f"{iid}_q4", "difficulty_level": 4, "question_type": "danger_zone_status", "question_text": "Is the needle currently in the danger zone, if one is marked? If so, by how much does it exceed the threshold?", "ground_truth": danger_answer, "answer_format": "'yes; exceeds threshold by N', 'no', or 'no danger zone marked'"},
        {"question_id": f"{iid}_q5", "difficulty_level": 5, "question_type": "quarter_range_increase", "question_text": "If the needle value increased by 25% of the gauge's full range, would it exceed the maximum value on the scale? Answer yes or no, and give the new value.", "ground_truth": projected_answer, "answer_format": "'yes; new value N' or 'no; new value N'"},
    ]
    difficulty = Fraction(25, 100) + Fraction(12, 100) * (needle_value.denominator != 1) + Fraction(12, 100) * (config["sweep"] == 270) + Fraction(14, 100) * has_danger + Fraction(15, 100) * projected_exceeds
    return {
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": [CANVAS, CANVAS],
        "seed": index,
        "instrument_type": config["instrument_type"],
        "unit": config["unit"],
        "min_value": config["min"],
        "max_value": config["max"],
        "tick_interval": config["tick"],
        "dial_start_angle": config["start"],
        "dial_sweep_degrees": config["sweep"],
        "needle_value": float(needle_value) if needle_value.denominator != 1 else needle_value.numerator,
        "needle_value_fraction": fraction_string(needle_value),
        "needle_angle": float(needle_angle),
        "needle_angle_fraction": fraction_string(needle_angle),
        "rounded_tick_value": float(rounded_value) if rounded_value.denominator != 1 else rounded_value.numerator,
        "rounded_tick_value_fraction": fraction_string(rounded_value),
        "danger_zone_threshold": None if threshold is None else (float(threshold) if threshold.denominator != 1 else threshold.numerator),
        "danger_zone_threshold_fraction": None if threshold is None else fraction_string(threshold),
        "projected_value_after_quarter_range": float(projected_value) if projected_value.denominator != 1 else projected_value.numerator,
        "projected_value_fraction": fraction_string(projected_value),
        "projected_exceeds_maximum": projected_exceeds,
        "difficulty_score": round(float(min(difficulty, Fraction(98, 100))), 4),
        "questions": questions,
    }


def render(scene, destination: Path):
    scale = 2
    image = Image.new("RGB", (CANVAS * scale, CANVAS * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    S = lambda point: tuple(int(round(value * scale)) for value in point)
    cx, cy = CENTER
    start = Fraction(scene["dial_start_angle"])
    sweep = Fraction(scene["dial_sweep_degrees"])
    minimum = Fraction(scene["min_value"])
    maximum = Fraction(scene["max_value"])
    interval = Fraction(scene["tick_interval"])

    draw.ellipse(S((cx - RADIUS - 12, cy - RADIUS - 12, cx + RADIUS + 12, cy + RADIUS + 12)), fill=FACE, outline="#D9DDD9", width=2 * scale)
    dial = [S(point) for point in arc_points(start, sweep, RADIUS)]
    draw.line(dial, fill=INK, width=5 * scale, joint="curve")

    threshold_text = ""
    if scene["danger_zone_threshold_fraction"] is not None:
        threshold = Fraction(scene["danger_zone_threshold_fraction"])
        threshold_angle = value_angle(threshold, minimum, maximum, start, sweep)
        danger_sweep = start + sweep - threshold_angle
        draw.line([S(point) for point in arc_points(threshold_angle, danger_sweep, RADIUS - 10)], fill=DANGER, width=15 * scale, joint="curve")
        threshold_text = f"DANGER ≥ {clean_number(threshold)} {scene['unit']}"

    minor_interval = interval / 2
    minor_count = int((maximum - minimum) / minor_interval)
    label_font = font(20 * scale, True)
    for step in range(minor_count + 1):
        value = minimum + step * minor_interval
        angle = value_angle(value, minimum, maximum, start, sweep)
        major = step % 2 == 0
        outer = RADIUS - 2
        inner = RADIUS - (30 if major else 18)
        draw.line([S(endpoint(angle, inner)), S(endpoint(angle, outer))], fill=INK if major else MINOR, width=(4 if major else 2) * scale)
        if major:
            position = endpoint(angle, RADIUS - 58)
            text = clean_number(value)
            box = draw.textbbox((0, 0), text, font=label_font)
            draw.text((position[0] * scale - (box[2] - box[0]) / 2, position[1] * scale - (box[3] - box[1]) / 2), text, fill=INK, font=label_font)

    title_font = font(24 * scale, True)
    unit_font = font(18 * scale, False)
    title = scene["instrument_type"].upper()
    draw.text((cx * scale, 45 * scale), title, fill=INK, font=title_font, anchor="mm")
    draw.text((cx * scale, (cy + 76) * scale), scene["unit"], fill=INK, font=unit_font, anchor="mm")
    if threshold_text:
        draw.text((cx * scale, (cy + 111) * scale), threshold_text, fill=DANGER, font=font(14 * scale, True), anchor="mm")

    needle_angle = Fraction(scene["needle_angle_fraction"])
    needle_end = endpoint(needle_angle, NEEDLE_LENGTH)
    needle_back = endpoint(needle_angle, -28)
    draw.line([S(needle_back), S(CENTER), S(needle_end)], fill=NEEDLE, width=9 * scale)
    draw.polygon([S(endpoint(needle_angle - 90, 8)), S(needle_end), S(endpoint(needle_angle + 90, 8))], fill=NEEDLE)
    draw.ellipse(S((cx - 12, cy - 12, cx + 12, cy + 12)), fill=INK, outline=FACE, width=2 * scale)

    image = image.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def write_dataset(output: Path, count: int, start_index: int, render_images: bool = True):
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for position, index in enumerate(range(start_index, start_index + count), 1):
        scene = make_scene(index)
        if render_images:
            render(scene, output / scene["image_path"])
        rows.append(scene)
        if render_images and (position % 100 == 0 or position == count):
            print(f"Rendered {position}/{count}", flush=True)
    with (output / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Generated {count} records in {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--sample", action="store_true", help="Generate five deterministic samples in sample_test/")
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir
    count = args.count
    if args.sample:
        output = output / "sample_test"
        count = 5
    write_dataset(output, count, args.start_index, not args.metadata_only)


if __name__ == "__main__":
    main()
