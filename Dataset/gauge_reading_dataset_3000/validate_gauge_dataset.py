"""Independently validate gauge metadata, questions, flattened tables, and PNG needles."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


CENTER = (300, 326)
NEEDLE_LENGTH = 174
NEEDLE_RGB = (19, 124, 120)
DANGER_RGB = (200, 67, 58)
TASKS = {1: "Image Description", 2: "Basic Relational Reasoning", 3: "Comparative Reasoning", 4: "Compound Reasoning", 5: "Extrapolative/Counterfactual Reasoning"}


def fresh_angle(value, minimum, maximum, start, sweep):
    return start + (value - minimum) * sweep / (maximum - minimum)


def half_up(value):
    if value >= 0:
        return (2 * value.numerator + value.denominator) // (2 * value.denominator)
    return -half_up(-value)


def nearest_tick(value, minimum, interval):
    return minimum + half_up((value - minimum) / interval) * interval


def clean(value):
    return str(value.numerator) if value.denominator == 1 else f"{float(value):g}"


def endpoint(angle, length):
    radians = math.radians(float(angle))
    return CENTER[0] + length * math.sin(radians), CENTER[1] - length * math.cos(radians)


def close_color(pixel, target, tolerance=5):
    return max(abs(pixel[i] - target[i]) for i in range(3)) <= tolerance


def color_near(image, target, point, radius, tolerance=5):
    x0, y0 = (int(round(value)) for value in point)
    for y in range(max(0, y0-radius), min(image.height, y0+radius+1)):
        for x in range(max(0, x0-radius), min(image.width, x0+radius+1)):
            if close_color(image.getpixel((x, y)), target, tolerance):
                return True
    return False


def color_mask(image, target, tolerance=5):
    difference = ImageChops.difference(image, Image.new("RGB", image.size, target))
    channels = [channel.point(lambda value: 255 if value <= tolerance else 0) for channel in difference.split()]
    return ImageChops.multiply(ImageChops.multiply(channels[0], channels[1]), channels[2])


def rendered_needle_issues(image, row):
    issues = []
    iid = row["id"]
    expected = Fraction(row["needle_angle_fraction"])
    for fraction in (0.35, 0.65, 0.92, 0.98):
        if not color_near(image, NEEDLE_RGB, endpoint(expected, NEEDLE_LENGTH*fraction), 7):
            issues.append(f"{iid}: PNG needle misses expected angle/length at {fraction:.2f}")
    mask = color_mask(image, NEEDLE_RGB)
    bbox = mask.getbbox()
    pixels = []
    if bbox:
        cropped = mask.crop(bbox)
        for offset_y in range(cropped.height):
            for offset_x in range(cropped.width):
                if cropped.getpixel((offset_x, offset_y)):
                    x, y = bbox[0]+offset_x, bbox[1]+offset_y
                    distance = math.hypot(x-CENTER[0], y-CENTER[1])
                    if distance > 25:
                        pixels.append((distance, x, y))
    if not pixels:
        issues.append(f"{iid}: PNG contains no detectable needle pixels")
    else:
        distance, x, y = max(pixels)
        observed = math.degrees(math.atan2(x-CENTER[0], CENTER[1]-y))
        delta = abs((observed-float(expected)+180) % 360 - 180)
        if delta > 2.0:
            issues.append(f"{iid}: PNG needle angle differs by {delta:.2f} degrees")
        if not 168 <= distance <= 181:
            issues.append(f"{iid}: PNG needle length {distance:.2f} outside tolerance")
    threshold_text = row.get("danger_zone_threshold_fraction")
    if threshold_text is not None:
        minimum, maximum = Fraction(row["min_value"]), Fraction(row["max_value"])
        start, sweep = Fraction(row["dial_start_angle"]), Fraction(row["dial_sweep_degrees"])
        threshold = Fraction(threshold_text)
        middle = (threshold+maximum)/2
        danger_angle = fresh_angle(middle, minimum, maximum, start, sweep)
        if not color_near(image, DANGER_RGB, endpoint(danger_angle, 228), 10, 8):
            issues.append(f"{iid}: PNG danger arc missing at expected scale location")
    return issues


def expected_answer(row, question):
    minimum, maximum = Fraction(row["min_value"]), Fraction(row["max_value"])
    interval, value = Fraction(row["tick_interval"]), Fraction(row["needle_value_fraction"])
    midpoint = (minimum + maximum) / 2
    kind = question["question_type"]
    if kind == "minimum_scale_value":
        return clean(minimum)
    if kind == "lower_or_upper_half":
        return "lower half" if value < midpoint else "upper half"
    if kind == "needle_value_nearest_tick":
        return clean(nearest_tick(value, minimum, interval))
    if kind == "danger_zone_status":
        text = row.get("danger_zone_threshold_fraction")
        if text is None:
            return "no danger zone marked"
        threshold = Fraction(text)
        return f"yes; exceeds threshold by {clean(value-threshold)}" if value > threshold else "no"
    if kind == "quarter_range_increase":
        projected = value + (maximum-minimum)/4
        return f"{'yes' if projected>maximum else 'no'}; new value {clean(projected)}"
    raise ValueError(f"unknown question type {kind}")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_tables(root, records):
    issues = []
    expected = []
    for row in records:
        for question in row["questions"]:
            expected.append({"question_id": question["question_id"], "task": TASKS[question["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": question["question_text"], "groundtruth": str(question["ground_truth"])})
    question_rows, answer_rows, final_rows = read_csv(root/"question_set.csv"), read_csv(root/"answer_key.csv"), read_csv(root/"dataset_final.csv")
    if question_rows and list(question_rows[0]) != ["question_id", "task", "image", "prompt"]:
        issues.append("tables: question_set columns mismatch")
    if answer_rows and list(answer_rows[0]) != ["question_id", "task", "image", "prompt", "groundtruth"]:
        issues.append("tables: answer_key columns mismatch")
    if not (len(question_rows) == len(answer_rows) == len(final_rows) == len(expected)):
        return issues + [f"tables: row counts {len(question_rows)}/{len(answer_rows)}/{len(final_rows)}/{len(expected)}"]
    seen = set()
    for index, (wanted, public, private, final) in enumerate(zip(expected, question_rows, answer_rows, final_rows), 1):
        if wanted["question_id"] in seen:
            issues.append(f"tables: duplicate question ID {wanted['question_id']}")
        seen.add(wanted["question_id"])
        for key in ("question_id", "task", "image", "prompt"):
            if public.get(key) != wanted[key]:
                issues.append(f"tables: public row {index} {key} mismatch")
            if private.get(key) != wanted[key]:
                issues.append(f"tables: private row {index} {key} mismatch")
        if private.get("groundtruth") != wanted["groundtruth"]:
            issues.append(f"tables: answer mismatch {wanted['question_id']}")
        for key in ("task", "image", "prompt", "groundtruth"):
            if final.get(key) != wanted[key]:
                issues.append(f"tables: final row {index} {key} mismatch")
    return issues


def validate(root):
    records = [json.loads(line) for line in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues = []
    types, relations, question_types = Counter(), Counter(), Counter()
    danger_count = 0
    projected_yes = 0
    for row in records:
        iid = row.get("id", "<missing>")
        try:
            minimum, maximum = Fraction(row["min_value"]), Fraction(row["max_value"])
            interval, value = Fraction(row["tick_interval"]), Fraction(row["needle_value_fraction"])
            start, sweep = Fraction(row["dial_start_angle"]), Fraction(row["dial_sweep_degrees"])
            types[row["instrument_type"]] += 1
            midpoint = (minimum+maximum)/2
            relations["lower half" if value<midpoint else "upper half"] += 1
            if not minimum < value < maximum or value == midpoint:
                issues.append(f"{iid}: invalid or ambiguous needle value")
            angle = fresh_angle(value, minimum, maximum, start, sweep)
            if Fraction(row["needle_angle_fraction"]) != angle or abs(float(row["needle_angle"])-float(angle)) > 1e-9:
                issues.append(f"{iid}: stored needle angle mismatch")
            rounded = nearest_tick(value, minimum, interval)
            if Fraction(row["rounded_tick_value_fraction"]) != rounded:
                issues.append(f"{iid}: stored nearest-tick value mismatch")
            projected = value+(maximum-minimum)/4
            projected_yes += projected>maximum
            if Fraction(row["projected_value_fraction"]) != projected or row["projected_exceeds_maximum"] != (projected>maximum):
                issues.append(f"{iid}: stored projected value mismatch")
            threshold_text = row.get("danger_zone_threshold_fraction")
            if threshold_text is not None:
                danger_count += 1
                threshold = Fraction(threshold_text)
                if (threshold-minimum) % interval != 0 or not midpoint < threshold < maximum:
                    issues.append(f"{iid}: danger threshold not an upper-half major tick")
                if value == threshold:
                    issues.append(f"{iid}: needle equals threshold ambiguously")
            questions = row.get("questions", [])
            if len(questions) != 5 or [question.get("difficulty_level") for question in questions] != [1, 2, 3, 4, 5]:
                issues.append(f"{iid}: expected five ordered questions")
            else:
                for question in questions:
                    question_types[question["question_type"]] += 1
                    expected = expected_answer(row, question)
                    if str(question["ground_truth"]) != expected:
                        issues.append(f"{iid}: {question['question_type']} answer mismatch ({question['ground_truth']!r} != {expected!r})")
        except Exception as exc:
            issues.append(f"{iid}: metadata validation exception ({exc})")
        path = root / row["image_path"]
        if not path.exists():
            issues.append(f"{iid}: missing PNG")
        else:
            try:
                with Image.open(path) as source:
                    image = source.convert("RGB")
                    image.load()
                    if image.size != (600, 600):
                        issues.append(f"{iid}: expected 600x600 PNG")
                    if sum(ImageStat.Stat(image).var) < 100:
                        issues.append(f"{iid}: PNG appears blank")
                    issues.extend(rendered_needle_issues(image, row))
            except Exception as exc:
                issues.append(f"{iid}: unreadable PNG ({exc})")
    for path in (root/"question_set.csv", root/"answer_key.csv", root/"dataset_final.csv"):
        if not path.exists():
            issues.append(f"tables: missing {path.name}")
    if not any(issue.startswith("tables: missing") for issue in issues):
        issues.extend(validate_tables(root, records))
    if len(records) == 3000:
        if danger_count != 1200:
            issues.append(f"dataset: danger-zone count {danger_count} != 1200")
        if relations != Counter({"lower half": 1500, "upper half": 1500}):
            issues.append(f"dataset: half distribution {dict(relations)}")
        expected_types = {"analog meter": 600, "pressure gauge": 1200, "speedometer": 600, "temperature dial": 600}
        if dict(types) != expected_types:
            issues.append(f"dataset: instrument distribution {dict(types)}")
        if any(count != 3000 for count in question_types.values()) or len(question_types) != 5:
            issues.append(f"dataset: question distribution {dict(question_types)}")
    lines = ["Gauge Reading Dataset Validation Report", "=======================================", f"Total images checked: {len(records)}", f"Total questions checked: {sum(len(row.get('questions', [])) for row in records)}", f"Total mismatches found: {len(issues)}", f"Danger zones marked: {danger_count}", f"Level 5 projected values exceeding maximum: {projected_yes}", "", "Instrument types:"]
    lines += [f"  {key}: {value}" for key, value in sorted(types.items())]
    lines += ["", "Range-half distribution:"] + [f"  {key}: {value}" for key, value in sorted(relations.items())]
    lines += ["", "Question types:"] + [f"  {key}: {value}" for key, value in sorted(question_types.items())]
    lines += ["", "Issues:"] + ([f"  {issue}" for issue in issues] if issues else ["  None"])
    lines += ["", f"Summary: {'PASS' if not issues else 'FAIL'}"]
    report = "\n".join(lines) + "\n"
    (root/"validation_report.txt").write_text(report, encoding="utf-8")
    print(report)
    return len(issues)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    raise SystemExit(1 if validate(args.dataset) else 0)


if __name__ == "__main__":
    main()
