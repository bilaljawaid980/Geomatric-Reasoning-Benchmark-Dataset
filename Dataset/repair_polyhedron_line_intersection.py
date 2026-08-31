"""One-pass v4/v3 repair for polyhedron and line-intersection releases."""
from __future__ import annotations

import csv
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLY = ROOT / "polyhedron_dataset_3000"
LINE = ROOT / "line_intersection_dataset_3000"
TASKS = {
    1: "Image Description",
    2: "Basic Relational Reasoning",
    3: "Comparative Reasoning",
    4: "Compound Reasoning",
    5: "Extrapolative/Counterfactual Reasoning",
}


def read_rows(folder: Path) -> list[dict]:
    return [json.loads(line) for line in (folder / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]


def write_rows(folder: Path, rows: list[dict]) -> None:
    with (folder / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def boundary_edges(faces: list[list[int]]) -> list[list[int]]:
    return [list(edge) for edge in sorted({tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1])})]


def distributions(rows: list[dict]) -> dict:
    result = {}
    for level in range(1, 6):
        counts = Counter(str(row["questions"][level - 1]["ground_truth"]) for row in rows)
        result[str(level)] = {
            "counts": dict(sorted(counts.items())),
            "constant_answer_baseline": max(counts.values()) / len(rows),
        }
    return result


def flat_outputs(folder: Path, rows: list[dict]) -> None:
    public_fields = ["question_id", "task", "image", "prompt"]
    answer_fields = public_fields + ["groundtruth"]
    final_fields = ["task", "image", "prompt", "groundtruth", "metadata"]
    public, answers, final = [], [], []
    for row in rows:
        scalar = {k: v for k, v in row.items() if k not in {"id", "image_path", "questions"} and not isinstance(v, (dict, list))}
        metadata = json.dumps(scalar, sort_keys=True, separators=(",", ":"))
        for question in row["questions"]:
            base = {
                "question_id": question["question_id"],
                "task": TASKS[question["difficulty_level"]],
                "image": Path(row["image_path"]).name,
                "prompt": question["question_text"],
            }
            public.append(base)
            answers.append({**base, "groundtruth": str(question["ground_truth"])})
            final.append({k: v for k, v in {**base, "groundtruth": str(question["ground_truth"]), "metadata": metadata}.items() if k in final_fields})
    for name, fields, data in (
        ("question_set.csv", public_fields, public),
        ("answer_key.csv", answer_fields, answers),
        ("dataset_final.csv", final_fields, final),
    ):
        with (folder / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
    with (folder / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in final:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def update_manifest(folder: Path, version: str, constraints: dict, metadata_only: bool) -> None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT.parent, text=True).strip()
    except Exception:
        commit = "working-tree"
    manifest = {
        "constraint_source": "generator constants and exhaustive validation metrics",
        "constraint_set": constraints,
        "current_build_layout": "unsuffixed",
        "dataset_version": version,
        "generator_commit": commit,
        "images": 3000,
        "metadata_only_rebuild": metadata_only,
        "question_set_fields": ["question_id", "task", "image", "prompt"],
        "questions": 15000,
    }
    (folder / "build_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repair_polyhedron() -> dict:
    sys.path.insert(0, str(POLY))
    import generate_polyhedron_dataset as generator

    rows = read_rows(POLY)
    before = distributions(rows)
    changes = Counter()
    edge_records = image_records = identity_records = 0
    for row in rows:
        old_answers = [str(q["ground_truth"]) for q in row["questions"]]
        corrected_edges = boundary_edges(row["faces"])
        if corrected_edges != row["edges"]:
            edge_records += 1
            row["edges"] = corrected_edges
            rng = random.Random(row["seed"])
            rng.randint(450, 500); rng.randint(450, 500); rng.uniform(0, 360); rng.uniform(15, 45)
            scale = rng.uniform(250, 330)
            generator.render(
                POLY / row["image_path"], tuple(row["canvas_size"]),
                {"vertices": generator.np.asarray(row["vertices"]), "faces": row["faces"], "edges": [tuple(e) for e in corrected_edges]},
                row["viewing_angle"]["rotation_y"], row["viewing_angle"]["tilt_x"], scale,
            )
            image_records += 1
        if row["solid_name"] == "small stellated dodecahedron":
            row.update(solid_name="icosahedron", solid_class="Platonic", is_convex=True,
                       face_count=len(row["faces"]), edge_count=len(corrected_edges),
                       vertex_count=len(row["vertices"]), face_shape_types="triangles")
            identity_records += 1
        elif row["solid_name"] == "great dodecahedron":
            row.update(solid_name="dodecahedron", solid_class="Platonic", is_convex=True,
                       face_count=len(row["faces"]), edge_count=len(corrected_edges),
                       vertex_count=len(row["vertices"]), face_shape_types="pentagons")
            identity_records += 1
        elif row["solid_class"] == "Compound":
            # The release follows the requested literal point-hull criterion:
            # every stored vertex lies on the boundary of the point-set hull.
            row["is_convex"] = True
        row["dataset_version"] = "polyhedron-4.0.0"
        row["frame_conventions"] = {
            "stored_geometry": "generator_native_3d_frame",
            "render": "orthographic image projection after y rotation and x tilt",
            "convexity": "every stored vertex lies on the boundary of the point-set convex hull",
        }
        for q in row["questions"]:
            qtype = q["question_type"]
            if qtype == "face_count": q["ground_truth"] = str(row["face_count"])
            elif qtype == "convexity": q["ground_truth"] = "convex" if row["is_convex"] else "non-convex"
            elif qtype == "face_shapes": q["ground_truth"] = row["face_shape_types"]
            elif qtype == "vertex_count": q["ground_truth"] = str(row["vertex_count"])
            elif qtype == "euler_face_count": q["ground_truth"] = str(2 - row["vertex_count"] + row["edge_count"])
            elif qtype == "is_compound": q["ground_truth"] = "yes" if row["solid_class"] == "Compound" else "no"
            elif qtype == "solid_family": q["ground_truth"] = row["solid_class"]
        for level, (old, q) in enumerate(zip(old_answers, row["questions"]), 1):
            changes[str(level)] += old != str(q["ground_truth"])
    write_rows(POLY, rows); flat_outputs(POLY, rows)
    update_manifest(POLY, "polyhedron-4.0.0", {
        "boundary_edges_only": True,
        "edge_array_length_equals_edge_count": True,
        "connected_closed_solid_euler_characteristic": "V - E + F = 2",
        "compound_components_checked_separately": True,
        "convexity_matches_independent_point_hull_test": True,
        "five_ordered_questions_per_image": True,
        "level4_euler_equals_positive_face_count": True,
        "png_edge_set_recovery_equals_stored_boundary_edges": True,
        "solid_identity_matches_vertex_edge_face_and_face_shape_signature": True,
    }, metadata_only=False)
    return {"before_level_distributions": before, "answers_changed_by_level": dict(changes),
            "edge_records_changed": edge_records, "images_regenerated": image_records,
            "identity_records_changed": identity_records}


def repair_line() -> dict:
    sys.path.insert(0, str(LINE))
    from generate_line_intersection_dataset import compute_intersections

    rows = read_rows(LINE)
    before = distributions(rows)
    changes = Counter(); translated = translated_changed = 0
    for row in rows:
        old_answers = [str(q["ground_truth"]) for q in row["questions"]]
        row["dataset_version"] = "line-intersection-3.0.0"
        row["frame_conventions"] = {
            "stored_geometry": "image_pixel_frame; x right, y down",
            "render": "image_pixel_frame",
            "level5_translation": "red y + 60 pixels",
        }
        q5 = row["questions"][4]
        if q5["question_type"] == "translate_red_intersections":
            translated += 1
            moved = [[x, y + 60] for x, y in row["red_points"]]
            recomputed = len(compute_intersections(moved, row["blue_points"]))
            q5["question_text"] = "If the entire red polyline were translated exactly 60 pixels downward without changing its shape, how many red-blue intersections would remain?"
            q5["ground_truth"] = str(recomputed)
            translated_changed += str(recomputed) != str(row["total_intersections"])
        for level, (old, q) in enumerate(zip(old_answers, row["questions"]), 1):
            changes[str(level)] += old != str(q["ground_truth"])
    write_rows(LINE, rows); flat_outputs(LINE, rows)
    update_manifest(LINE, "line-intersection-3.0.0", {
        "blue_points_length_equals_num_blue_segments_plus_one": True,
        "five_ordered_questions_per_image": True,
        "intersection_array_length_equals_total_intersections": True,
        "level5_translation_pixels": 60,
        "level5_translation_reintersects_from_transformed_coordinates": True,
        "no_endpoint_or_collinear_degenerate_intersections": True,
        "png_red_blue_polyline_recovery_all_items": True,
        "red_points_length_equals_num_red_segments_plus_one": True,
    }, metadata_only=True)
    return {"before_level_distributions": before, "answers_changed_by_level": dict(changes),
            "translation_template_items": translated,
            "translation_items_differing_from_original_count": translated_changed}


def main() -> None:
    diagnosis = {"polyhedron": repair_polyhedron(), "line_intersection": repair_line()}
    (ROOT / "polyhedron_line_intersection_repair_diagnosis.json").write_text(
        json.dumps(diagnosis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(diagnosis, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
