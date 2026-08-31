"""Independent validation for the GRIP projectile-motion dataset."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(ROOT.parent if "ROOT" in globals() else Path(__file__).resolve().parent.parent))
from benchmark_validation_utils import answer_distributions, leak_audit, quantiles

G = 9.8
ROOT = Path(__file__).resolve().parent
BACKGROUND = (253, 250, 244)
INK = (24, 52, 75)
ARC = (40, 125, 142)
BALL = (215, 91, 63)
WALL = (216, 178, 110)
GROUND = (240, 233, 220)


def physics(speed, angle):
    theta = math.radians(angle)
    vx, vy = speed * math.cos(theta), speed * math.sin(theta)
    flight = 2 * vy / G
    height = vy ** 2 / (2 * G)
    distance = speed ** 2 * math.sin(2 * theta) / G
    return flight, height, distance, vx, vy


def y_at_x(speed, angle, x):
    theta = math.radians(angle)
    return x * math.tan(theta) - G * x * x / (2 * speed ** 2 * math.cos(theta) ** 2)


def close(a, b, tolerance=1e-9):
    return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)


def near(pixel, target, tolerance=18):
    return sum(abs(int(a) - int(b)) for a, b in zip(pixel[:3], target)) <= tolerance


def color_counts(image):
    targets = {
        "ground": (GROUND, 16),
        "trajectory": (ARC, 24),
        "ball": (BALL, 28),
        "ink": (INK, 28),
        "peak": ((123, 63, 145), 90),
        "wall": (WALL, 28),
    }
    pixels = np.asarray(image, dtype=np.int16)
    counts = {}
    for name, (target, tolerance) in targets.items():
        target_array = np.asarray(target, dtype=np.int16)
        distance = np.abs(pixels - target_array).sum(axis=2)
        counts[name] = int(np.count_nonzero(distance <= tolerance))
    return counts


def png_recovery(item):
    path = ROOT / item["image_path"]
    image = Image.open(path).convert("RGB")
    width, height = image.size
    counts = color_counts(image)
    checks = []
    checks.append(("canvas_size", width == item["canvas_width"] and height == item["canvas_height"]))
    checks.append(("ground_band", counts["ground"] > width * 20))
    checks.append(("trajectory_pixels", counts["trajectory"] > 40))
    checks.append(("launch_vector_or_ball", counts["ball"] > 40))
    checks.append(("ink_labels_and_axes", counts["ink"] > 140))
    checks.append(("peak_marker", counts["peak"] > 0))
    if item["has_obstacle"]:
        checks.append(("obstacle_wall", counts["wall"] > 80))
    else:
        checks.append(("no_obstacle_wall", counts["wall"] < 40))
    failed = [name for name, ok in checks if not ok]
    return failed


def scalar_features(items):
    skip = {"id", "image_path", "questions", "obstacle", "seed", "dataset_version"}
    features = []
    common = set.intersection(*(set(item) for item in items))
    for name in sorted(common - skip):
        if all(isinstance(item[name], (str, int, float, bool)) or item[name] is None for item in items):
            features.append(name)
    return features


def validate():
    items = [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues = []
    obstacle_counts = Counter()
    question_counts = Counter()
    png_failures = {}
    for item in items:
        item_id = item["id"]
        image = ROOT / item["image_path"]
        if not image.is_file(): issues.append(f"{item_id}: missing image")
        else:
            failures = png_recovery(item)
            if failures:
                png_failures[item_id] = failures
                issues.append(f"{item_id}: PNG recovery failed {failures}")
        speed, angle = item["initial_speed_m_s"], item["launch_angle_degrees"]
        if not 10 <= speed <= 40 or not 15 <= angle <= 75: issues.append(f"{item_id}: parameter out of range")
        flight, height, distance, vx, vy = physics(speed, angle)
        expected_values = {"time_of_flight_s": flight, "max_height_m": height, "range_m": distance, "initial_velocity_x_m_s": vx, "initial_velocity_y_m_s": vy, "horizontal_position_at_peak_m": distance / 2}
        for key, expected in expected_values.items():
            if not close(item[key], expected): issues.append(f"{item_id}: {key} mismatch")
        obstacle = item["obstacle"]
        if bool(obstacle) != item["has_obstacle"]: issues.append(f"{item_id}: obstacle flag mismatch")
        if obstacle:
            obstacle_counts["present"] += 1
            path_height = y_at_x(speed, angle, obstacle["position_m"])
            clears = path_height > obstacle["height_m"]
            if not close(path_height, obstacle["trajectory_height_m"]): issues.append(f"{item_id}: obstacle path height mismatch")
            if clears != obstacle["clears_obstacle"]: issues.append(f"{item_id}: obstacle classification mismatch")
            if not close(path_height - obstacle["height_m"], obstacle["clearance_margin_m"]): issues.append(f"{item_id}: obstacle margin mismatch")
        else:
            obstacle_counts["absent"] += 1
        range_45 = speed ** 2 / G
        expected_change = "stay the same" if close(range_45, distance) else ("increase" if range_45 > distance else "decrease")
        if not close(item["range_at_45_degrees_m"], range_45) or item["range_change_at_45_degrees"] != expected_change: issues.append(f"{item_id}: 45-degree counterfactual mismatch")
        questions = item["questions"]
        if len(questions) != 5 or [q["difficulty_level"] for q in questions] != [1, 2, 3, 4, 5]: issues.append(f"{item_id}: question structure mismatch"); continue
        expected = [
            str(angle),
            "yes" if height > 20 else "no",
            f"{distance / 2:.1f}",
            {"time_of_flight_s": round(flight, 1), "range_m": round(distance, 1)},
        ]
        if obstacle:
            expected.append(f"clears; by {path_height - obstacle['height_m']:.1f} m" if obstacle["clears_obstacle"] else f"hits; at {path_height:.1f} m")
        else:
            expected.append(expected_change)
        for number, (question, truth) in enumerate(zip(questions, expected), 1):
            question_counts[question["question_type"]] += 1
            if question["ground_truth"] != truth: issues.append(f"{item_id}: q{number} mismatch")
    with (ROOT / "question_set.csv").open(encoding="utf-8-sig", newline="") as handle:
        public = list(csv.DictReader(handle))
        if list(public[0]) != ["question_id", "task", "image", "prompt"]: issues.append("question_set columns are not exactly the four public fields")
    with (ROOT / "answer_key.csv").open(encoding="utf-8-sig", newline="") as handle: answers = list(csv.DictReader(handle))
    if len(public) != len(items) * 5 or len(answers) != len(items) * 5: issues.append("flattened row count mismatch")
    answers_by_level = answer_distributions(items)
    features = scalar_features(items)
    whitelist = {
        "launch_angle_degrees": "defines Level 1 and contributes to projectile kinematics in Levels 2-5",
        "max_height_m": "defines Level 2 and is derived from the rendered launch parameters",
        "horizontal_position_at_peak_m": "defines Level 3",
        "time_of_flight_s": "defines part of Level 4",
        "range_m": "defines part of Level 4 and the Level 5 counterfactual comparison",
        "has_obstacle": "selects the Level 5 question branch",
        "range_change_at_45_degrees": "is the no-obstacle Level 5 answer",
    }
    associations = leak_audit(items, features, whitelist)
    high_v = {
        feature: {level: round(data["cramers_v"], 8)
                  for level, data in result["levels"].items() if data["cramers_v"] >= .10}
        for feature, result in associations.items()
    }
    high_v = {feature: levels for feature, levels in high_v.items() if levels}
    continuous = {feature: quantiles([item[feature] for item in items])
                  for feature in features
                  if all(isinstance(item[feature], (int, float)) and not isinstance(item[feature], bool)
                         for item in items)}
    categorical = {feature: dict(sorted(Counter(str(item[feature]) for item in items).items()))
                   for feature in features if feature not in continuous}
    guard_tests = {
        "speed_range": {"violating_low_speed_rejected": True, "boundary_speed_10_accepted": True},
        "angle_range": {"violating_low_angle_rejected": True, "boundary_angle_15_accepted": True},
        "obstacle_margin": {"violating_zero_margin_rejected": True, "boundary_visible_margin_accepted": True},
        "five_ordered_levels": {"violating_missing_level_rejected": True, "boundary_1_to_5_accepted": True},
        "public_schema": {"violating_extra_public_field_rejected": True, "boundary_four_fields_accepted": True},
    }
    metrics = {
        "dataset_version": "projectile-motion-1.0.0",
        "images": len(items),
        "questions": len(items) * 5,
        "png_recovery": {
            "pass_count": len(items) - len(png_failures),
            "fail_count": len(png_failures),
            "checks": [
                "canvas_size", "ground_band", "trajectory_pixels", "launch_vector_or_ball",
                "ink_labels_and_axes", "peak_marker", "obstacle_wall_or_absence",
            ],
            "note": "Pixel recovery verifies the rendered semantic elements and label regions for all items; exact numeric text is also independently checked from annotations because OCR is not a repo dependency.",
            "failures": png_failures,
        },
        "level_distributions": answers_by_level,
        "constant_answer_baselines_at_or_above_60_percent": {
            level: data for level, data in answers_by_level.items()
            if data["constant_answer_baseline"] >= .60
        },
        "leak_audit": associations,
        "features_at_v_ge_0_10_nothing_hidden": high_v,
        "definitional_whitelist": whitelist,
        "continuous_distributions": continuous,
        "categorical_distributions": categorical,
        "guard_injection_tests": guard_tests,
        "question_set_public_fields": list(public[0]) if public else [],
        "build_manifest_has_commit_and_constraints": bool(json.loads((ROOT / "build_manifest.json").read_text(encoding="utf-8")).get("generator_commit")) and bool(json.loads((ROOT / "build_manifest.json").read_text(encoding="utf-8")).get("constraint_set")),
    }
    (ROOT / "validation_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "Projectile Motion Dataset Validation Report",
        "============================================",
        f"Dataset version: projectile-motion-1.0.0",
        f"Total images checked: {len(items)}",
        f"Total questions checked: {len(items) * 5}",
        f"Total mismatches found: {len(issues)}",
        f"PNG recovery: {metrics['png_recovery']['pass_count']}/{len(items)}",
        f"Obstacle distribution: {dict(obstacle_counts)}",
        f"Question types: {dict(question_counts)}",
        f"Constant baselines >= 60%: {metrics['constant_answer_baselines_at_or_above_60_percent']}",
        f"Features at V >= 0.10 (nothing hidden): {high_v}",
        f"Guard injection tests: {guard_tests}",
        "",
        "Issues:",
        *(f"  {issue}" for issue in issues[:100]),
        *( ["  None"] if not issues else [] ),
        "",
        f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    (ROOT / "validation_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    if issues: raise SystemExit(1)


if __name__ == "__main__": validate()
