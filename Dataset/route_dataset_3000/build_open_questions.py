"""Build one deterministic open-ended route-tracing question per image."""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
ANSWER_COLUMNS = [
    "question_id", "image", "target", "target_position", "target_degree",
    "lines_at_target", "colors", "reached", "unreached", "answer",
]


def read_records() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]


def assign_endpoints(num_endpoints: int, canvas_size: list[int]) -> dict[str, dict]:
    width, height = canvas_size
    margin = 64
    inner_width, inner_height = width - 2 * margin, height - 2 * margin
    perimeter = 2 * (inner_width + inner_height)
    start = inner_width / 2
    result = {}
    for index in range(num_endpoints):
        distance = (start + index * perimeter / num_endpoints) % perimeter
        letter = chr(65 + index)
        if distance < inner_width:
            point, side = (margin + distance, margin), "top"
        elif distance < inner_width + inner_height:
            point, side = (width - margin, margin + distance - inner_width), "right"
        elif distance < 2 * inner_width + inner_height:
            point, side = (width - margin - (distance - inner_width - inner_height), height - margin), "bottom"
        else:
            point, side = (margin, height - margin - (distance - 2 * inner_width - inner_height)), "left"
        result[letter] = {"anchor": [round(point[0]), round(point[1])], "side": side}
    return result


def position_phrase(endpoint: dict, canvas_size: list[int]) -> str:
    x, y = endpoint["anchor"]
    width, height = canvas_size
    side = endpoint["side"]
    if side in {"top", "bottom"}:
        horizontal = " left" if x < width * 0.38 else (" right" if x > width * 0.62 else "")
        return f"at the {side}{horizontal}"
    vertical = "upper " if y < height * 0.38 else ("lower " if y > height * 0.62 else "")
    return f"on the {vertical}{side}" if vertical else f"on the {side}"


def incident_routes(record: dict, target: str) -> list[dict]:
    result = []
    for index, route in enumerate(record["routes"]):
        if target not in (route["start"], route["end"]):
            continue
        far_end = route["end"] if route["start"] == target else route["start"]
        result.append({
            "route_index": index,
            "color": route["color"],
            "start": route["start"],
            "end": route["end"],
            "far_end": far_end,
            "num_bends": route["num_bends"],
            "points": route["points"],
        })
    return result


def select_target(record: dict) -> tuple[str, dict[str, int], list[str], str]:
    degrees = {
        letter: sum(letter in (route["start"], route["end"]) for route in record["routes"])
        for letter in record["endpoint_letters"]
    }
    preferred = [letter for letter in record["endpoint_letters"] if degrees[letter] in (2, 3)]
    if preferred:
        candidates, rule = preferred, "seeded choice among degree-2-or-3 labels"
    else:
        positive = [value for value in degrees.values() if value >= 1]
        if not positive:
            raise ValueError(f"{record['id']}: no label has degree >= 1")
        minimum = min(positive)
        candidates = [letter for letter in record["endpoint_letters"] if degrees[letter] == minimum]
        rule = "seeded choice among lowest non-zero-degree labels"
    target = random.Random(int(record["seed"])).choice(candidates)
    return target, degrees, candidates, rule


def derive(record: dict) -> tuple[dict, dict, dict]:
    target, degrees, candidates, selection_rule = select_target(record)
    endpoints = assign_endpoints(record["num_endpoints"], record["canvas_size"])
    position = position_phrase(endpoints[target], record["canvas_size"])
    incident = incident_routes(record, target)
    colors = [route["color"] for route in incident]
    reached = sorted({route["far_end"] for route in incident if route["far_end"] != target})
    unreached = sorted(set(record["endpoint_letters"]) - {target} - set(reached))
    answer = "connected to every other labelled side" if not unreached else "some labelled sides remain unreached"
    other_count = len(record["endpoint_letters"]) - 1
    prompt = (
        f"Trace the coloured lines that touch the label {target} {position} of the frame and follow each one through "
        f"its bends to wherever it terminates: decide whether {target} is connected to every one of the other "
        f"{other_count} labelled sides or whether some remain unreached from it, and name the label at the far end "
        f"of each line that begins at {target}. State your conclusion, justify it by describing the paths you "
        "followed and how you distinguished each line by colour where they overlap, and end with a confidence "
        "score from 0 to 1 for your conclusion."
    )
    question_id = f"{record['id']}_open_q1"
    public = {"question_id": question_id, "image": Path(record["image_path"]).name, "prompt": prompt}
    answer_row = {
        "question_id": question_id,
        "image": Path(record["image_path"]).name,
        "target": target,
        "target_position": position,
        "target_degree": len(incident),
        "lines_at_target": len(incident),
        "colors": json.dumps(colors, separators=(",", ":")),
        "reached": json.dumps(reached, separators=(",", ":")),
        "unreached": json.dumps(unreached, separators=(",", ":")),
        "answer": answer,
    }
    connected_pairs = sorted({"".join(sorted((route["start"], route["end"]))) for route in record["routes"] if route["start"] != route["end"]})
    annotation = {
        **public,
        **{key: value for key, value in answer_row.items() if key not in {"question_id", "image"}},
        "dataset_version": record.get("dataset_version"),
        "scoring": {
            "conclusion_requires_exact_reached_set": True,
            "partial_match_fields": ["lines_at_target", "colors", "reached", "unreached"],
            "confidence_range": [0, 1],
        },
        "derivation": {
            "degrees": degrees,
            "qualifying_targets": candidates,
            "selection_rule": selection_rule,
            "endpoint_layout": endpoints,
            "incident_routes": incident,
            "connected_label_pairs": connected_pairs,
            "connected_pairs_out_of_canonical_15": len(connected_pairs),
        },
    }
    return public, answer_row, annotation


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    public_rows, answer_rows, annotations = [], [], []
    for record in read_records():
        public, answer, annotation = derive(record)
        public_rows.append(public)
        answer_rows.append(answer)
        annotations.append(annotation)
    if len(public_rows) != 3000:
        raise RuntimeError(f"Expected 3,000 records, found {len(public_rows)}")
    write_csv(ROOT / "open_questions.csv", PUBLIC_COLUMNS, public_rows)
    write_csv(ROOT / "open_answer_key.csv", ANSWER_COLUMNS, answer_rows)
    with (ROOT / "open_annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in annotations:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"Wrote {len(public_rows)} route open questions")


if __name__ == "__main__":
    main()
