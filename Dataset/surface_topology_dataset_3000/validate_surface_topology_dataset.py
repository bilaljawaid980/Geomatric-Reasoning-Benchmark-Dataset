"""Independent validator for the surface-topology dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


def expected_invariants(row):
    variant = row["surface_variant"]
    if variant.startswith("genus_") or variant == "torus":
        return True, 0, 2 - 2 * row["genus"]
    if variant == "cylindrical_band":
        return True, 2, 0
    if variant == "mobius_strip":
        # Non-orientable genus k=1 and one boundary component:
        # chi = 2 - k - b = 2 - 1 - 1 = 0.
        return False, 1, 0
    if variant == "klein_bottle":
        # Closed non-orientable genus k=2: chi = 2 - k = 0.
        return False, 0, 0
    raise ValueError(f"unknown surface variant: {variant}")


def recompute_mesh(row):
    vertices = [tuple(v) for v in row["mesh_vertices"]]
    faces = row["mesh_faces"]
    face_edges = {
        tuple(sorted((a, b)))
        for face in faces
        for a, b in zip(face, face[1:] + face[:1])
    }
    stored_edges = {tuple(e) for e in row["mesh_edges"]}
    return len(vertices), len(face_edges), len(faces), face_edges == stored_edges


def expected_question(row, question):
    kind = question["question_type"]
    if kind == "genus_count":
        return str(row["genus"])
    if kind == "orientability":
        return "orientable" if row["is_orientable"] else "non-orientable"
    if kind == "euler_characteristic":
        return str(row["euler_characteristic"])
    if kind == "mesh_vertex_count":
        return str(row["vertex_count"])
    if kind == "derive_genus":
        if not row["is_orientable"] or row["boundary_count"]:
            raise ValueError("orientable closed-surface formula used on an invalid surface")
        return str((2 - row["euler_characteristic"]) // 2)
    if kind == "derive_face_count":
        return str(row["euler_characteristic"] - row["vertex_count"] + row["edge_count"])
    if kind == "euler_well_defined":
        return "yes"
    if kind == "combined_euler_orientability":
        orientation = "orientable" if row["is_orientable"] else "non-orientable"
        return f"{row['euler_characteristic']}; {orientation}"
    if kind == "remove_disk_euler_characteristic":
        # Removing an open disk adds one boundary component. For orientable
        # chi=2-2g-b and non-orientable chi=2-k-b, so chi decreases by one.
        orientable, boundary_count, original_chi = expected_invariants(row)
        del orientable, boundary_count
        return str(original_chi - 1)
    raise ValueError(f"unknown question type: {kind}")


def validate(root: Path):
    annotation_path = root / "annotations.jsonl"
    rows = [json.loads(line) for line in annotation_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    issues = []
    type_counts = Counter()
    variant_counts = Counter()
    genus_counts = Counter()
    question_counts = Counter()

    for row in rows:
        iid = row.get("id", "<missing-id>")
        type_counts[row["surface_type"]] += 1
        variant_counts[row["surface_variant"]] += 1
        genus_counts[row["genus"]] += 1
        path = root / row["image_path"]
        if not path.exists():
            issues.append(f"{iid}: missing image {row['image_path']}")
        else:
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    if list(image.size) != row["canvas_size"]:
                        issues.append(f"{iid}: canvas size mismatch")
                    if image.mode != "RGB":
                        issues.append(f"{iid}: expected RGB PNG, got {image.mode}")
            except Exception as exc:
                issues.append(f"{iid}: unreadable PNG ({exc})")

        try:
            orientable, boundary_count, chi = expected_invariants(row)
            if row["is_orientable"] != orientable:
                issues.append(f"{iid}: orientability mismatch")
            if row["boundary_count"] != boundary_count:
                issues.append(f"{iid}: boundary-count mismatch")
            if row["euler_characteristic"] != chi:
                issues.append(f"{iid}: Euler-characteristic mismatch")
        except Exception as exc:
            issues.append(f"{iid}: invariant validation error ({exc})")

        if row["surface_type"] == "polyhedral_mesh":
            try:
                v, e, f, exact_edges = recompute_mesh(row)
                if not exact_edges:
                    issues.append(f"{iid}: stored edge list differs from face-derived edges")
                if (v, e, f) != (row["vertex_count"], row["edge_count"], row["face_count"]):
                    issues.append(f"{iid}: V/E/F count mismatch")
                if v - e + f != row["euler_characteristic"]:
                    issues.append(f"{iid}: V-E+F does not equal claimed Euler characteristic")
            except Exception as exc:
                issues.append(f"{iid}: mesh validation error ({exc})")
        elif any(key in row for key in ("mesh_vertices", "mesh_edges", "mesh_faces")):
            issues.append(f"{iid}: non-mesh row contains mesh arrays")

        questions = row.get("questions", [])
        if len(questions) != 5 or [q.get("difficulty_level") for q in questions] != [1, 2, 3, 4, 5]:
            issues.append(f"{iid}: expected exactly five ordered difficulty levels")
            continue
        if len({q.get("question_id") for q in questions}) != 5:
            issues.append(f"{iid}: duplicate question IDs")
        for question in questions:
            question_counts[question["question_type"]] += 1
            try:
                expected = expected_question(row, question)
                if question["ground_truth"] != expected:
                    issues.append(f"{iid}: {question['question_type']} ground truth {question['ground_truth']!r} != {expected!r}")
            except Exception as exc:
                issues.append(f"{iid}: {question.get('question_type')} validation error ({exc})")

    if len(rows) >= 3000:
        expected_types = {"sphere_handles", "polyhedral_mesh", "mobius_vs_cylinder", "klein_vs_torus"}
        if set(type_counts) != expected_types:
            issues.append(f"dataset: surface-type set mismatch: {sorted(type_counts)}")
        for key in expected_types:
            if not 700 <= type_counts[key] <= 800:
                issues.append(f"dataset: {key} distribution outside 700-800 ({type_counts[key]})")
        if set(genus_counts) != {0, 1, 2, 3}:
            issues.append(f"dataset: genus set mismatch: {sorted(genus_counts)}")
        for genus in range(4):
            if not 600 <= genus_counts[genus] <= 900:
                issues.append(f"dataset: genus {genus} distribution outside 600-900 ({genus_counts[genus]})")

    report = [
        "Surface Topology Dataset Validation Report",
        "==========================================",
        f"Total images checked: {len(rows)}",
        f"Total questions checked: {sum(question_counts.values())}",
        f"Total mismatches found: {len(issues)}",
        "",
        "Surface-type distribution:",
        *[f"  {key}: {value}" for key, value in sorted(type_counts.items())],
        "",
        "Variant distribution:",
        *[f"  {key}: {value}" for key, value in sorted(variant_counts.items())],
        "",
        "Genus distribution:",
        *[f"  {key}: {value}" for key, value in sorted(genus_counts.items())],
        "",
        "Question-template distribution:",
        *[f"  {key}: {value}" for key, value in sorted(question_counts.items())],
        "",
        f"Summary: {'PASS' if not issues else 'FAIL'}",
    ]
    if issues:
        report += ["", "Mismatches:", *[f"  {issue}" for issue in issues]]
    text = "\n".join(report) + "\n"
    (root / "validation_report.txt").write_text(text, encoding="utf-8")
    print(text)
    return rows, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    _, issues = validate(args.dataset)
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
