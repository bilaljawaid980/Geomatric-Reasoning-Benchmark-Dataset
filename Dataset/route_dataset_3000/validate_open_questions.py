"""Independently validate route open questions, answers, derivations, and PNG evidence."""
from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
ANSWER_COLUMNS = [
    "question_id", "image", "target", "target_position", "target_degree",
    "lines_at_target", "colors", "reached", "unreached", "answer",
]
COLOR_HEX = {
    "teal": "#009E9A", "orange": "#F05A17", "blue": "#0878BD", "green": "#149B43",
    "red": "#D7192D", "purple": "#9256C2", "brown": "#7A4938", "amber": "#C77A00",
    "magenta": "#D51A78", "cyan": "#00A8C2", "olive": "#799514", "gray-blue": "#557383",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def endpoints(record: dict) -> dict[str, dict]:
    width, height = record["canvas_size"]
    margin = 64
    inner_width, inner_height = width - 2 * margin, height - 2 * margin
    perimeter = 2 * (inner_width + inner_height)
    result = {}
    for index, letter in enumerate(record["endpoint_letters"]):
        distance = (inner_width / 2 + index * perimeter / record["num_endpoints"]) % perimeter
        if distance < inner_width:
            anchor, side = [round(margin + distance), margin], "top"
        elif distance < inner_width + inner_height:
            anchor, side = [width - margin, round(margin + distance - inner_width)], "right"
        elif distance < 2 * inner_width + inner_height:
            anchor, side = [round(width - margin - (distance - inner_width - inner_height)), height - margin], "bottom"
        else:
            anchor, side = [margin, round(height - margin - (distance - 2 * inner_width - inner_height))], "left"
        result[letter] = {"anchor": anchor, "side": side}
    return result


def position_phrase(endpoint: dict, canvas: list[int]) -> str:
    x, y = endpoint["anchor"]
    width, height = canvas
    side = endpoint["side"]
    if side in {"top", "bottom"}:
        horizontal = " left" if x < width * .38 else (" right" if x > width * .62 else "")
        return f"at the {side}{horizontal}"
    vertical = "upper " if y < height * .38 else ("lower " if y > height * .62 else "")
    return f"on the {vertical}{side}" if vertical else f"on the {side}"


def derive(record: dict) -> dict:
    degrees = {
        letter: sum(letter in (route["start"], route["end"]) for route in record["routes"])
        for letter in record["endpoint_letters"]
    }
    candidates = [letter for letter in record["endpoint_letters"] if degrees[letter] in (2, 3)]
    if not candidates:
        positive = [value for value in degrees.values() if value >= 1]
        if not positive:
            raise ValueError("no positive-degree target")
        minimum = min(positive)
        candidates = [letter for letter in record["endpoint_letters"] if degrees[letter] == minimum]
    target = random.Random(int(record["seed"])).choice(candidates)
    incident = [route for route in record["routes"] if target in (route["start"], route["end"])]
    far_ends = [route["end"] if route["start"] == target else route["start"] for route in incident]
    reached = sorted(set(far_ends) - {target})
    unreached = sorted(set(record["endpoint_letters"]) - {target} - set(reached))
    return {
        "target": target,
        "target_position": position_phrase(endpoints(record)[target], record["canvas_size"]),
        "target_degree": len(incident),
        "lines_at_target": len(incident),
        "colors": [route["color"] for route in incident],
        "reached": reached,
        "unreached": unreached,
        "answer": "connected to every other labelled side" if not unreached else "some labelled sides remain unreached",
        "incident": incident,
        "degrees": degrees,
    }


def rgb(hex_value: str) -> tuple[int, int, int]:
    value = hex_value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def close(pixel: tuple[int, ...], target: tuple[int, int, int], tolerance: int = 85) -> bool:
    return max(abs(pixel[index] - target[index]) for index in range(3)) <= tolerance


def color_near(image: Image.Image, point: list[int], target: tuple[int, int, int], radius: int = 4) -> bool:
    x0, y0 = point
    return any(
        close(image.getpixel((x, y)), target)
        for y in range(max(0, y0 - radius), min(image.height, y0 + radius + 1))
        for x in range(max(0, x0 - radius), min(image.width, x0 + radius + 1))
    )


def endpoint_segment_visible(image: Image.Image, points: list[list[int]], target: tuple[int, int, int], at_start: bool) -> bool:
    endpoint, inward = (points[0], points[1]) if at_start else (points[-1], points[-2])
    dx, dy = inward[0] - endpoint[0], inward[1] - endpoint[1]
    length = max(1.0, math.hypot(dx, dy))
    probes = [
        [round(endpoint[0] + dx * distance / length), round(endpoint[1] + dy * distance / length)]
        for distance in (0, 2, 5, 10, 16, 24, 35)
    ]
    return any(color_near(image, point, target, 6) for point in probes)


def label_center(endpoint: dict) -> tuple[int, int]:
    x, y = endpoint["anchor"]
    side = endpoint["side"]
    if side == "top":
        return x, y - 39
    if side == "bottom":
        return x, y + 38
    if side == "left":
        return x - 39, y
    return x + 39, y


def label_visible(image: Image.Image, endpoint: dict) -> bool:
    x0, y0 = label_center(endpoint)
    ink = (16, 23, 25)
    return any(
        close(image.getpixel((x, y)), ink, 55)
        for y in range(max(0, y0 - 25), min(image.height, y0 + 26))
        for x in range(max(0, x0 - 25), min(image.width, x0 + 26))
    )


def distribution(values) -> dict[str, int]:
    return dict(sorted(Counter(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (list, dict)) else str(value) for value in values).items()))


def baseline(counts: dict[str, int]) -> float:
    return max(counts.values()) / sum(counts.values()) if counts else 0.0


def main() -> None:
    records = [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    public = read_csv(ROOT / "open_questions.csv")
    answers = read_csv(ROOT / "open_answer_key.csv")
    annotations = [json.loads(line) for line in (ROOT / "open_annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    issues, derivation_mismatches = [], []
    png_pass = 0
    selected_degrees, targets, connected_pairs = Counter(), Counter(), Counter()
    values = {key: [] for key in ["target", "target_degree", "lines_at_target", "colors", "reached", "unreached", "answer"]}
    if len(records) != len(public) or len(public) != len(answers) or len(answers) != len(annotations):
        issues.append("row-count mismatch among source/open files")
    if public and list(public[0]) != PUBLIC_COLUMNS:
        issues.append(f"public columns {list(public[0])} != {PUBLIC_COLUMNS}")
    if answers and list(answers[0]) != ANSWER_COLUMNS:
        issues.append(f"answer columns {list(answers[0])} != {ANSWER_COLUMNS}")
    for position, (record, question, answer, annotation) in enumerate(zip(records, public, answers, annotations), 1):
        expected = derive(record)
        qid = f"{record['id']}_open_q1"
        parsed = {
            "target": answer["target"], "target_position": answer["target_position"],
            "target_degree": int(answer["target_degree"]), "lines_at_target": int(answer["lines_at_target"]),
            "colors": json.loads(answer["colors"]), "reached": json.loads(answer["reached"]),
            "unreached": json.loads(answer["unreached"]), "answer": answer["answer"],
        }
        for key in parsed:
            if parsed[key] != expected[key]:
                derivation_mismatches.append(f"{record['id']}/{key}")
        if question["question_id"] != qid or answer["question_id"] != qid or annotation["question_id"] != qid:
            issues.append(f"{record['id']}: question_id mismatch")
        if question["image"] != Path(record["image_path"]).name or answer["image"] != question["image"]:
            issues.append(f"{record['id']}: image mismatch")
        prompt = question["prompt"]
        if re.search(r"\(\s*-?\d+\s*,\s*-?\d+\s*\)", prompt) or "coordinate" in prompt.lower() or "axis" in prompt.lower():
            issues.append(f"{record['id']}: prompt contains coordinates")
        named_colors = {name for name in COLOR_HEX if re.search(rf"\b{re.escape(name)}\b", prompt.lower())}
        if not named_colors <= set(record["colors_used"]):
            issues.append(f"{record['id']}: prompt names absent color")
        if any(prompt.strip() == old["question_text"].strip() for old in record["questions"]):
            issues.append(f"{record['id']}: exact existing-question paraphrase")
        if not all(fragment in prompt.lower() for fragment in ["far end", "distinguished each line by colour", "confidence score"]):
            issues.append(f"{record['id']}: open task lacks required multi-part reasoning")
        if "most routes" in prompt.lower() or "maximum endpoint degree" in prompt.lower():
            issues.append(f"{record['id']}: reduces to degree-ranking task")
        leaked_color = any(re.search(rf"\b{re.escape(color)}\b", prompt.lower()) for color in expected["colors"])
        leaked_label = any(
            re.search(rf"\b{re.escape(label)}\b", prompt)
            for label in set(expected["reached"] + expected["unreached"]) - {expected["target"]}
        )
        if leaked_color or leaked_label:
            issues.append(f"{record['id']}: prompt leaks an answer-specific color/label")
        if annotation.get("target") != expected["target"] or annotation.get("derivation", {}).get("degrees") != expected["degrees"]:
            issues.append(f"{record['id']}: annotation derivation mismatch")
        selected_degrees[expected["target_degree"]] += 1
        targets[expected["target"]] += 1
        pairs = {"".join(sorted((route["start"], route["end"]))) for route in record["routes"] if route["start"] != route["end"]}
        connected_pairs[len(pairs)] += 1
        for key in values:
            values[key].append(expected[key])
        image_path = ROOT / record["image_path"]
        with Image.open(image_path) as source:
            image = source.convert("RGB")
            image.load()
        layout = endpoints(record)
        png_ok = image.size == tuple(record["canvas_size"]) and all(label_visible(image, layout[label]) for label in record["endpoint_letters"])
        for route in expected["incident"]:
            target_color = rgb(route.get("hex") or COLOR_HEX[route["color"]])
            if not endpoint_segment_visible(image, route["points"], target_color, True) or not endpoint_segment_visible(image, route["points"], target_color, False):
                png_ok = False
        if png_ok:
            png_pass += 1
        else:
            issues.append(f"{record['id']}: PNG target/path/endpoint recovery")
        if position % 500 == 0:
            print(f"Validated {position}/{len(records)}", flush=True)
    if derivation_mismatches:
        issues.append(f"independent derivation mismatches: {len(derivation_mismatches)}")
    distributions = {key: distribution(field_values) for key, field_values in values.items()}
    baselines = {key: baseline(counts) for key, counts in distributions.items()}
    metrics = {
        "question_count": len(public),
        "selection_distribution": {"target": dict(sorted(targets.items())), "target_degree": dict(sorted(selected_degrees.items()))},
        "preferred_degree_2_or_3": sum(selected_degrees[value] for value in (2, 3)),
        "fallback_count": len(records) - sum(selected_degrees[value] for value in (2, 3)),
        "connected_label_pairs_out_of_canonical_15": dict(sorted(connected_pairs.items())),
        "answer_distributions": distributions,
        "constant_answer_baselines": baselines,
        "fields_over_60_percent": {key: value for key, value in baselines.items() if value > .60},
        "derivation_mismatches": derivation_mismatches,
        "png_recoverability": {"passed": png_pass, "total": len(records)},
        "public_columns": PUBLIC_COLUMNS,
        "no_coordinate_prompts": not any("prompt contains coordinates" in issue for issue in issues),
        "no_answer_leakage": not any("prompt leaks" in issue for issue in issues),
        "no_existing_question_paraphrase": not any("paraphrase" in issue or "degree-ranking" in issue for issue in issues),
        "issues": issues,
    }
    (ROOT / "open_validation_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "ROUTE OPEN-QUESTION VALIDATION REPORT", "=" * 37,
        f"Questions: {len(public)}", f"Derivation mismatches: {len(derivation_mismatches)}",
        f"PNG-recoverable items: {png_pass}/{len(records)}", f"Selected target degrees: {dict(sorted(selected_degrees.items()))}",
        f"Connected-pair diagnostic (of canonical 15): {dict(sorted(connected_pairs.items()))}",
        f"Constant baselines: {baselines}", f"Fields over 60%: {metrics['fields_over_60_percent']}",
        f"Issues: {len(issues)}", *(issues if issues else ["None"]), f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    (ROOT / "open_validation_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
