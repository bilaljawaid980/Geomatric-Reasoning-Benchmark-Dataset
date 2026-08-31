"""Independent validation for the GRIP projectile-motion dataset."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

G = 9.8
ROOT = Path(__file__).resolve().parent


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


def validate():
    items = [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues = []
    obstacle_counts = Counter()
    question_counts = Counter()
    for item in items:
        item_id = item["id"]
        image = ROOT / item["image_path"]
        if not image.is_file(): issues.append(f"{item_id}: missing image")
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
    report = [
        "Projectile Motion Dataset Validation Report",
        "============================================",
        f"Dataset version: projectile-motion-1.0.0",
        f"Total images checked: {len(items)}",
        f"Total questions checked: {len(items) * 5}",
        f"Total mismatches found: {len(issues)}",
        f"Obstacle distribution: {dict(obstacle_counts)}",
        f"Question types: {dict(question_counts)}",
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
