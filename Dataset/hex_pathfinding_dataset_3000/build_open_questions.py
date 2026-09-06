"""Build one deterministic open-ended HOME-neighborhood question per image."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRECTIONS = [
    ("upper-left", (0, -1)),
    ("upper-right", (1, -1)),
    ("left", (-1, 0)),
    ("right", (1, 0)),
    ("lower-left", (-1, 1)),
    ("lower-right", (0, 1)),
]
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
ANSWER_COLUMNS = [
    "question_id", "image", "target", "home_on_boundary", "neighbour_count",
    "holes_touching", "walkable_touching", "hole_directions",
]
PROMPT = (
    "Look closely at the green HOME hex and everything that immediately surrounds it: state whether it sits on "
    "the outer boundary of the hexagonal field or fully inside it, count how many hexes lie directly against it, "
    "and say how many of those are grey holes and how many are walkable. Name the position of any hole touching it "
    "using these six direction names only: upper-left, upper-right, left, right, lower-left, lower-right. Justify "
    "your answer by describing exactly what you see around it, and end with a confidence score from 0 to 1."
)


def read_records() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]


def derive(record: dict) -> tuple[dict, dict, dict]:
    tiles = {tuple(tile["coordinate"]): tile["color"] for tile in record["all_tiles"]}
    home = tuple(record["home_coordinate"])
    neighbours = []
    for name, (dq, dr) in DIRECTIONS:
        coordinate = (home[0] + dq, home[1] + dr)
        if coordinate in tiles:
            neighbours.append({"direction": name, "coordinate": list(coordinate), "color": tiles[coordinate]})
    holes = [item for item in neighbours if item["color"] == "grey"]
    hole_directions = [name for name, _ in DIRECTIONS if any(item["direction"] == name for item in holes)]
    question_id = f"{record['id']}_open_q1"
    public = {"question_id": question_id, "image": Path(record["image_path"]).name, "prompt": PROMPT}
    answer = {
        "question_id": question_id,
        "image": Path(record["image_path"]).name,
        "target": "HOME",
        "home_on_boundary": len(neighbours) < 6,
        "neighbour_count": len(neighbours),
        "holes_touching": len(holes),
        "walkable_touching": len(neighbours) - len(holes),
        "hole_directions": json.dumps(hole_directions, separators=(",", ":")),
    }
    annotation = {
        **public,
        **{key: value for key, value in answer.items() if key not in {"question_id", "image"}},
        "dataset_version": record.get("dataset_version"),
        "scoring": {
            "separate_exact_match_fields": [
                "home_on_boundary", "neighbour_count", "holes_touching", "walkable_touching", "hole_directions"
            ],
            "confidence_range": [0, 1],
        },
        "derivation": {
            "home_coordinate": list(home),
            "direction_vocabulary": [name for name, _ in DIRECTIONS],
            "in_grid_neighbours": neighbours,
            "walkable_definition": "any in-grid neighbor whose stored color is not grey",
        },
    }
    return public, answer, annotation


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
    print(f"Wrote {len(public_rows)} hex open questions")


if __name__ == "__main__":
    main()
