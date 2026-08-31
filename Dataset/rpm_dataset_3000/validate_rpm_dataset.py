"""Independently validate RPM rules, answer choices, distractors, and questions."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


SHAPES = ("circle", "square", "triangle", "pentagon", "hexagon", "star")
SIZES = ("small", "medium", "large")
COLORS = ("#B23A2E", "#C65D00", "#8A6800", "#147A68", "#246EB9", "#7040A0")
ROTATIONS = (0, 45, 90, 135, 180, 225, 270, 315)
COUNTS = (1, 2, 3)
ATTRS = ("shape", "size", "color", "rotation", "count")
DOMAINS = {"shape": SHAPES, "size": SIZES, "color": COLORS, "rotation": ROTATIONS, "count": COUNTS}


def add_counts(left, right):
    return ((left + right - 1) % 3) + 1


def grid(record):
    return {(p["row"] - 1, p["column"] - 1): p["attributes"] for p in record["grid_panels"]}


def sequence_cells(orientation, group, matrix):
    return [matrix[(group, p)] for p in range(3)] if orientation == "row" else [matrix[(p, group)] for p in range(3)]


def independently_infer_missing(record):
    matrix = grid(record)
    missing = dict(record["background_constants"])
    for rule in record["active_rules"]:
        attr = rule["attribute"]
        kind = rule["rule_type"]
        orientation = rule["applies_to"]
        seq = sequence_cells(orientation, 2, matrix)
        if kind in {"shape_progression", "constant"}:
            expected = seq[0][attr]
        elif kind == "xor_addition":
            expected = add_counts(seq[0][attr], seq[1][attr])
        else:
            domain = DOMAINS[attr]
            first, second = domain.index(seq[0][attr]), domain.index(seq[1][attr])
            step = (second - first) % len(domain)
            if step == len(domain) - 1:
                step = -1
            expected = domain[(second + step) % len(domain)]
        missing[attr] = expected
    return missing


def expected_from_rule(rule, group, position):
    kind, attr, details = rule["rule_type"], rule["attribute"], rule["details"]
    domain = DOMAINS[attr]
    if kind == "shape_progression":
        return domain[(details["start_index"] + details["step"] * group) % len(domain)]
    if kind in {"size_progression", "count_progression", "color_progression", "rotation_progression"}:
        return domain[(details["start_index"] + details["step"] * position) % len(domain)]
    if kind == "xor_addition":
        values = [details["left"], details["middle"]]
        while len(values) <= position:
            values.append(add_counts(values[-2], values[-1]))
        return values[position]
    if kind == "constant":
        return details["value"]
    raise KeyError(kind)


def extrapolate(rule):
    if rule["attribute"] == "count":
        details = rule["details"]
        if rule["rule_type"] == "count_progression":
            # Independent, unbounded arithmetic continuation: 1,2,3 -> 4
            # and 3,2,1 -> 0. Do not reuse the generator's cyclic domain.
            return COUNTS[details["start_index"]] + details["step"] * 3
        if rule["rule_type"] == "xor_addition":
            third = add_counts(details["left"], details["middle"])
            return third + (third - details["middle"])
    return expected_from_rule(rule, 2, 3)


def classify(correct, candidate):
    if candidate["shape"] == correct["shape"] and candidate["color"] != correct["color"]:
        return "correct shape but wrong color"
    if candidate["color"] == correct["color"] and candidate["shape"] != correct["shape"]:
        return "correct color but wrong shape"
    return "wrong in some other way"


def answer(question, record, inferred):
    kind = question["question_type"]
    matrix = grid(record)
    choices = record["answer_choices"]
    if kind == "top_left_shape_count":
        return str(matrix[(0, 0)]["count"])
    if kind == "correct_choice":
        winners = [c["choice_index"] for c in choices if c["attributes"] == inferred]
        return str(winners[0]) if len(winners) == 1 else "AMBIGUOUS"
    if kind == "consistent_attribute":
        return question["reference_attribute"]
    if kind == "distractor_classification":
        candidate = next(c for c in choices if c["choice_index"] == question["reference_choice"])
        return classify(inferred, candidate["attributes"])
    if kind == "combined_rule_attributes":
        return " and ".join(r["attribute"] for r in record["active_rules"])
    if kind == "rule_extrapolation":
        rule = next(r for r in record["active_rules"] if r["rule_type"] == question["reference_rule_type"] and r["attribute"] == question["reference_attribute"])
        return str(extrapolate(rule))
    if kind == "choices_matching_correct_shape":
        return str(sum(c["attributes"]["shape"] == inferred["shape"] for c in choices))
    if kind == "add_same_shape_distractor":
        return str(sum(c["attributes"]["shape"] == inferred["shape"] for c in choices) + 1)
    raise KeyError(kind)


def validate(root: Path):
    issues = []
    checked = 0
    tiers = Counter()
    orientations = Counter()
    rule_counts = Counter()
    question_counts = Counter()
    for line in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        checked += 1
        iid = record["id"]
        tiers[record["difficulty_tier"]] += 1
        orientations[record["orientation"]] += 1
        for rule in record["active_rules"]:
            rule_counts[rule["rule_type"]] += 1
        if record["num_active_rules"] != len(record["active_rules"]) or len(record["active_rules"]) not in (1, 2):
            issues.append(f"{iid}: active-rule count mismatch")
        if len({r["attribute"] for r in record["active_rules"]}) != len(record["active_rules"]):
            issues.append(f"{iid}: active rules target the same attribute")
        matrix = grid(record)
        if len(matrix) != 9 or any((r, c) not in matrix for r in range(3) for c in range(3)):
            issues.append(f"{iid}: incomplete grid")
            continue
        active_attrs = {r["attribute"] for r in record["active_rules"]}
        for attr in ATTRS:
            if attr not in active_attrs:
                expected = record["background_constants"].get(attr)
                if expected is None or any(panel[attr] != expected for panel in matrix.values()):
                    issues.append(f"{iid}: background constant {attr} mismatch")
        for rule in record["active_rules"]:
            for row in range(3):
                for col in range(3):
                    group, position = (row, col) if rule["applies_to"] == "row" else (col, row)
                    actual = matrix[(row, col)][rule["attribute"]]
                    expected = expected_from_rule(rule, group, position)
                    if actual != expected:
                        issues.append(f"{iid}: {rule['rule_type']} fails at ({row + 1},{col + 1})")
        inferred = independently_infer_missing(record)
        stored_correct = matrix[(2, 2)]
        if record.get("dataset_version") != "rpm-2.0.0":
            issues.append(f"{iid}: dataset version mismatch")
        if any(stored_correct == panel for position, panel in matrix.items() if position != (2, 2)):
            issues.append(f"{iid}: missing panel is directly copyable")
        matrix_rows = [[matrix[(r, c)] for c in range(3)] for r in range(3)]
        if len({json.dumps(row, sort_keys=True) for row in matrix_rows}) != 3:
            issues.append(f"{iid}: matrix contains identical rows")
        if inferred != stored_correct:
            issues.append(f"{iid}: inferred missing panel != stored correct panel")
        choices = record["answer_choices"]
        if len(choices) != 8 or sorted(c["choice_index"] for c in choices) != list(range(1, 9)):
            issues.append(f"{iid}: invalid choices")
        exact = [c for c in choices if c["attributes"] == inferred]
        if len(exact) != 1:
            issues.append(f"{iid}: expected one valid choice, found {len(exact)}")
        elif exact[0]["choice_index"] != record["correct_answer_index"]:
            issues.append(f"{iid}: correct answer index mismatch")
        violation_map = {v["choice_index"]: v for v in record["distractor_violations"]}
        for choice in choices:
            if choice["attributes"] == inferred:
                if not choice["is_correct"]:
                    issues.append(f"{iid}/{choice['choice_index']}: correct choice flag false")
                continue
            diffs = [a for a in ATTRS if choice["attributes"][a] != inferred[a]]
            claim = violation_map.get(choice["choice_index"])
            if not claim:
                issues.append(f"{iid}/{choice['choice_index']}: missing violation claim")
                continue
            if sorted(diffs) != sorted(claim["violated_attributes"]):
                issues.append(f"{iid}/{choice['choice_index']}: violated attributes claim wrong")
            if claim["violation_type"] in {"single_attribute", "wrong_progression"} and len(diffs) != 1:
                issues.append(f"{iid}/{choice['choice_index']}: claimed single violation has {len(diffs)} diffs")
            if claim["violation_type"] == "random" and len(diffs) < 2:
                issues.append(f"{iid}/{choice['choice_index']}: random distractor too close")
        image = root / record["image_path"]
        if not image.is_file():
            issues.append(f"{iid}: missing image")
        else:
            with Image.open(image) as im:
                if im.size != tuple(record["canvas_size"]):
                    issues.append(f"{iid}: PNG size mismatch")
        questions = record["questions"]
        if len(questions) != 5 or [q["difficulty_level"] for q in questions] != [1, 2, 3, 4, 5]:
            issues.append(f"{iid}: invalid question levels")
        for q in questions:
            question_counts[q["question_type"]] += 1
            try:
                actual = answer(q, record, inferred)
            except Exception as exc:
                issues.append(f"{iid}/{q.get('question_id')}: derivation error {exc}")
                continue
            if actual != q["ground_truth"]:
                issues.append(f"{iid}/{q['question_id']}: stored={q['ground_truth']!r}, actual={actual!r}")
    if checked:
        if tiers != Counter({"combined_rules": checked}):
            issues.append(f"dataset: anti-copy build must use two rules, got {tiers}")
    return checked, tiers, orientations, rule_counts, question_counts, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, nargs="?", default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    checked, tiers, orientations, rules, questions, issues = validate(args.dataset)
    lines = [
        f"Total images checked: {checked}",
        f"Difficulty tiers: {json.dumps(dict(tiers), sort_keys=True)}",
        f"Orientations: {json.dumps(dict(orientations), sort_keys=True)}",
        f"Rule distribution: {json.dumps(dict(sorted(rules.items())), sort_keys=True)}",
        f"Question types: {json.dumps(dict(sorted(questions.items())), sort_keys=True)}",
        f"Total mismatches found: {len(issues)}",
        f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    lines.extend(issues)
    report = args.dataset / "validation_report.txt"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report.read_text(encoding="utf-8"))
    raise SystemExit(bool(issues))


if __name__ == "__main__":
    main()
