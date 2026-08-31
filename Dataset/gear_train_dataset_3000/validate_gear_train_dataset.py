"""Independent physics and artifact validator for the gear-train dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, deque
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageStat


def flip(direction):
    return "CCW" if direction == "CW" else "CW"


def fresh_graph(row):
    labels = [gear["label"] for gear in row["gears"]]
    graph = {label: [] for label in labels}
    for a, b in row["mesh_edges"]:
        graph[a].append(b); graph[b].append(a)
    return graph


def recompute(row, tooth_override=None):
    """Fresh BFS implementation, independent of the generator helper."""
    graph = fresh_graph(row)
    teeth = {gear["label"]: int(gear["tooth_count"]) for gear in row["gears"]}
    if tooth_override:
        teeth.update(tooth_override)
    driver = row["driver_label"]
    values = {driver: (row["driver_direction"], Fraction(row["driver_rpm"]))}
    queue = deque([driver])
    while queue:
        source = queue.popleft()
        source_direction, source_rpm = values[source]
        for target in graph[source]:
            candidate = (flip(source_direction), source_rpm * Fraction(teeth[source], teeth[target]))
            if target in values:
                if values[target] != candidate:
                    raise ValueError("inconsistent cycle")
            else:
                values[target] = candidate
                queue.append(target)
    if len(values) != len(teeth):
        raise ValueError("disconnected graph")
    return values


def expected_answer(row, question, values):
    kind = question["question_type"]
    if kind == "gear_count":
        return str(len(row["gears"]))
    if kind == "direct_mesh_direction":
        return "opposite"
    if kind == "most_teeth":
        return max(row["gears"], key=lambda gear: gear["tooth_count"])["label"]
    if kind == "fastest_gear":
        return max(values, key=lambda label: values[label][1])
    if kind == "multi_mesh_target_rpm":
        return f"{float(values[row['level4_target']][1]):.1f}"
    if kind == "double_teeth_counterfactual":
        scenario = row["level5_scenario"]
        changed = scenario["changed_gear"]
        target = scenario["target_gear"]
        original = next(g["tooth_count"] for g in row["gears"] if g["label"] == changed)
        modified = recompute(row, {changed: original * 2})
        before_rpm, after_rpm = values[target][1], modified[target][1]
        speed = "increase" if after_rpm > before_rpm else "decrease" if after_rpm < before_rpm else "stay the same"
        direction = "direction changes" if modified[target][0] != values[target][0] else "direction unchanged"
        return f"{speed}; {direction}"
    raise ValueError(f"unknown question type {kind}")


def row_count(path):
    if not path.exists(): return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def validate(root: Path):
    rows = [json.loads(line) for line in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    issues = []
    arrangement_counts = Counter()
    question_counts = Counter()
    cf_counts = Counter()
    for row in rows:
        iid = row.get("id", "<missing>")
        arrangement_counts[row["arrangement_type"]] += 1
        try:
            labels = [gear["label"] for gear in row["gears"]]
            if len(labels) != row["num_gears"] or len(set(labels)) != len(labels):
                issues.append(f"{iid}: gear count/labels mismatch")
            if len({gear["tooth_count"] for gear in row["gears"]}) != len(labels):
                issues.append(f"{iid}: tooth counts are not unique")
            if any(not 8 <= gear["tooth_count"] <= 40 for gear in row["gears"]):
                issues.append(f"{iid}: tooth count outside 8-40")
            graph = fresh_graph(row)
            if any(sorted(gear["mesh_partners"]) != sorted(graph[gear["label"]]) for gear in row["gears"]):
                issues.append(f"{iid}: mesh_partners disagree with mesh_edges")
            if len(row["mesh_edges"]) != len(labels) - 1:
                issues.append(f"{iid}: graph is not a tree")
            values = recompute(row)
            for a, b in row["mesh_edges"]:
                if values[a][0] == values[b][0]:
                    issues.append(f"{iid}: adjacent {a}-{b} rotate in same direction")
                expected_b = values[a][1] * Fraction(
                    next(g["tooth_count"] for g in row["gears"] if g["label"] == a),
                    next(g["tooth_count"] for g in row["gears"] if g["label"] == b),
                )
                if values[b][1] != expected_b:
                    issues.append(f"{iid}: adjacent RPM ratio wrong for {a}-{b}")
            if row["arrangement_type"] == "branching":
                branch_nodes = [label for label, partners in graph.items() if len(partners) == 3]
                if len(branch_nodes) != 1:
                    issues.append(f"{iid}: branching graph lacks exactly one degree-3 idler")
                else:
                    branch = branch_nodes[0]
                    children = [n for n in graph[branch] if len(graph[n]) == 1 and n != row["driver_label"]]
                    if len(children) >= 2 and values[children[0]][0] != values[children[1]][0]:
                        issues.append(f"{iid}: two outputs from idler differ in direction")
            for label, expected in values.items():
                stored = row["computed_rotation"][label]
                if stored["direction"] != expected[0] or Fraction(stored["rpm_fraction"]) != expected[1]:
                    issues.append(f"{iid}: stored rotation mismatch for {label}")
            questions = row.get("questions", [])
            if len(questions) != 5 or [q.get("difficulty_level") for q in questions] != [1, 2, 3, 4, 5]:
                issues.append(f"{iid}: expected five ordered difficulty levels")
            else:
                for question in questions:
                    question_counts[question["question_type"]] += 1
                    expected = expected_answer(row, question, values)
                    if str(question["ground_truth"]) != expected:
                        issues.append(f"{iid}: {question['question_type']} {question['ground_truth']!r} != {expected!r}")
                cf_counts[questions[4]["ground_truth"].split(";")[0]] += 1
        except Exception as exc:
            issues.append(f"{iid}: validation exception ({exc})")

        image_path = root / row["image_path"]
        if not image_path.exists():
            issues.append(f"{iid}: missing PNG")
        else:
            try:
                with Image.open(image_path) as image:
                    image.load()
                    if image.size != (600, 600) or image.mode != "RGB":
                        issues.append(f"{iid}: expected 600x600 RGB PNG")
                    if sum(ImageStat.Stat(image).var) < 100:
                        issues.append(f"{iid}: PNG appears blank")
            except Exception as exc:
                issues.append(f"{iid}: unreadable PNG ({exc})")

    if len(rows) >= 3000:
        branch_fraction = arrangement_counts["branching"] / len(rows)
        if not 0.28 <= branch_fraction <= 0.32:
            issues.append(f"dataset: branching fraction {branch_fraction:.3f} outside 0.28-0.32")
        for outcome in ("increase", "decrease", "stay the same"):
            if cf_counts[outcome] < 500:
                issues.append(f"dataset: counterfactual outcome {outcome!r} underrepresented ({cf_counts[outcome]})")
        for filename in ("dataset_final.csv", "question_set.csv", "answer_key.csv"):
            count = row_count(root / filename)
            if count != 15000:
                issues.append(f"dataset: {filename} has {count} rows, expected 15000")

    report = [
        "Gear Train Dataset Validation Report",
        "====================================",
        f"Total images checked: {len(rows)}",
        f"Total questions checked: {sum(question_counts.values())}",
        f"Total mismatches found: {len(issues)}",
        "",
        "Arrangement distribution:",
        *[f"  {key}: {value}" for key, value in sorted(arrangement_counts.items())],
        "",
        "Level 5 outcome distribution:",
        *[f"  {key}: {value}" for key, value in sorted(cf_counts.items())],
        "",
        "Question-type distribution:",
        *[f"  {key}: {value}" for key, value in sorted(question_counts.items())],
        "",
        "Issues:",
        *(issues if issues else ["  None"]),
        "",
        "Summary: " + ("PASS" if not issues else "FAIL"),
    ]
    text = "\n".join(report) + "\n"
    (root / "validation_report.txt").write_text(text, encoding="utf-8")
    print(text)
    return not issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    raise SystemExit(0 if validate(args.dataset) else 1)


if __name__ == "__main__":
    main()
