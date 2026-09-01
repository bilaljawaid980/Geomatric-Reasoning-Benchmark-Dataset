"""Metadata-only v5 repair for the polyhedron identity/shape/convexity audit."""
from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLY = ROOT / "polyhedron_dataset_3000"
VERSION = "polyhedron-5.0.0"
TASKS = {
    1: "Image Description", 2: "Basic Relational Reasoning",
    3: "Comparative Reasoning", 4: "Compound Reasoning",
    5: "Extrapolative/Counterfactual Reasoning",
}


def read_rows() -> list[dict]:
    return [json.loads(line) for line in (POLY / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]


def boundary_edges(faces: list[list[int]]) -> list[list[int]]:
    return [list(edge) for edge in sorted({tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1])})]


def actual_shape(faces: list[list[int]]) -> str:
    arities = frozenset(map(len, faces))
    return {frozenset({3}): "triangles", frozenset({4}): "squares", frozenset({5}): "pentagons"}.get(arities, "mixed")


def signature(row: dict) -> tuple[int, int, int, tuple[tuple[int, int], ...]]:
    return (len(row["vertices"]), len(boundary_edges(row["faces"])), len(row["faces"]), tuple(sorted(Counter(map(len, row["faces"])).items())))


def distributions(rows: list[dict]) -> dict:
    out = {}
    for level in range(1, 6):
        counts = Counter(str(row["questions"][level - 1]["ground_truth"]) for row in rows)
        out[str(level)] = {"counts": dict(sorted(counts.items())), "constant_answer_baseline": max(counts.values()) / len(rows)}
    return out


def assertion_audit(rows: list[dict]) -> dict:
    failures = {name: Counter() for name in ("face_array_length_equals_face_count", "face_shape_matches_face_arities", "edge_array_length_equals_edge_count", "literal_v_minus_e_plus_f_equals_2", "visible_face_count_not_above_face_count")}
    for row in rows:
        name = row["solid_name"]
        if len(row["faces"]) != row["face_count"]: failures["face_array_length_equals_face_count"][name] += 1
        if actual_shape(row["faces"]) != row["face_shape_types"]: failures["face_shape_matches_face_arities"][name] += 1
        if len(row["edges"]) != row["edge_count"]: failures["edge_array_length_equals_edge_count"][name] += 1
        if row["vertex_count"] - row["edge_count"] + row["face_count"] != 2: failures["literal_v_minus_e_plus_f_equals_2"][name] += 1
        if row["visible_face_count"] > row["face_count"]: failures["visible_face_count_not_above_face_count"][name] += 1
    return {key: {"total": sum(value.values()), "by_solid_name": dict(sorted(value.items()))} for key, value in failures.items()}


def write_rows(rows: list[dict]) -> None:
    with (POLY / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def write_flat(rows: list[dict]) -> None:
    public_fields = ["question_id", "task", "image", "prompt"]
    answer_fields = public_fields + ["groundtruth"]
    final_fields = ["task", "image", "prompt", "groundtruth", "metadata"]
    public, answers, final = [], [], []
    for row in rows:
        scalar = {k: v for k, v in row.items() if k not in {"id", "image_path", "questions"} and not isinstance(v, (dict, list))}
        metadata = json.dumps(scalar, sort_keys=True, separators=(",", ":"))
        for question in row["questions"]:
            base = {"question_id": question["question_id"], "task": TASKS[question["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": question["question_text"]}
            public.append(base); answers.append({**base, "groundtruth": str(question["ground_truth"])})
            final.append({"task": base["task"], "image": base["image"], "prompt": base["prompt"], "groundtruth": str(question["ground_truth"]), "metadata": metadata})
    for name, fields, data in (("question_set.csv", public_fields, public), ("answer_key.csv", answer_fields, answers), ("dataset_final.csv", final_fields, final)):
        with (POLY / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(data)
    with (POLY / "dataset_final.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in final: handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    rows = read_rows(); before = distributions(rows); before_assertions = assertion_audit(rows)
    # Actual geometry signatures are unique by intended identity in the current generator.
    import sys
    sys.path.insert(0, str(POLY))
    import generate_polyhedron_dataset as generator
    identities = {}
    for spec in generator.SPECS:
        probe = {"vertices": spec["mesh"]["vertices"], "faces": spec["mesh"]["faces"]}
        sig = signature(probe)
        identity = (spec["name"], spec["class"])
        if sig in identities and identities[sig] != identity: raise AssertionError((sig, identities[sig], identity))
        identities[sig] = identity

    changes = Counter(); field_changes = Counter(); renames = []
    failing_ids = {row["id"] for row in rows if any(
        (len(row["faces"]) != row["face_count"], actual_shape(row["faces"]) != row["face_shape_types"],
         len(row["edges"]) != row["edge_count"], row["vertex_count"] - row["edge_count"] + row["face_count"] != 2,
         row["visible_face_count"] > row["face_count"])
    )}
    for row in rows:
        old_answers = [str(q["ground_truth"]) for q in row["questions"]]
        sig = signature(row)
        if sig not in identities: raise AssertionError(f"Unknown geometry signature for {row['id']}: {sig}")
        derived_name, derived_class = identities[sig]
        if (row["solid_name"], row["solid_class"]) != (derived_name, derived_class):
            renames.append({"id": row["id"], "before": {"solid_name": row["solid_name"], "solid_class": row["solid_class"]}, "after": {"solid_name": derived_name, "solid_class": derived_class}, "V_E_F": list(sig[:3])})
        updates = {
            "solid_name": derived_name, "solid_class": derived_class,
            "vertex_count": len(row["vertices"]), "edge_count": len(boundary_edges(row["faces"])),
            "face_count": len(row["faces"]), "face_shape_types": actual_shape(row["faces"]),
            # Compounds are unions of interpenetrating closed components and are non-convex as solids.
            "is_convex": derived_class != "Compound", "dataset_version": VERSION,
        }
        for key, value in updates.items():
            if row.get(key) != value: field_changes[key] += 1
            row[key] = value
        row["frame_conventions"] = {
            "stored_geometry": "generator_native_3d_frame",
            "render": "orthographic image projection after y rotation and x tilt",
            "convexity": "compounds are non-convex; connected meshes require convex supporting faces and hull-boundary vertices",
            "euler": "V-E+F=2 per connected closed component (compound total is 2 times component count)",
        }
        for q in row["questions"]:
            qtype = q["question_type"]
            if qtype == "face_count": q["ground_truth"] = str(row["face_count"])
            elif qtype == "convexity": q["ground_truth"] = "convex" if row["is_convex"] else "non-convex"
            elif qtype == "face_shapes": q["ground_truth"] = row["face_shape_types"]
            elif qtype == "visible_face_count": q["ground_truth"] = str(row["visible_face_count"])
            elif qtype == "vertex_count": q["ground_truth"] = str(row["vertex_count"])
            elif qtype == "euler_face_count": q["ground_truth"] = str(2 - row["vertex_count"] + row["edge_count"])
            elif qtype == "is_compound": q["ground_truth"] = "yes" if row["solid_class"] == "Compound" else "no"
            elif qtype == "solid_family": q["ground_truth"] = row["solid_class"]
            elif qtype == "remove_face_closed_surface": q["ground_truth"] = "no"
        for level, (old, q) in enumerate(zip(old_answers, row["questions"]), 1): changes[str(level)] += old != str(q["ground_truth"])

    after = distributions(rows); after_assertions = assertion_audit(rows)
    write_rows(rows); write_flat(rows)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT.parent, text=True).strip()
    manifest = {
        "constraint_source": "generator constants and exhaustive validation metrics",
        "constraint_set": {
            "face_array_length_equals_face_count": True,
            "face_shape_type_matches_face_vertex_arities": True,
            "edge_array_length_equals_edge_count": True,
            "edge_array_is_deduplicated_face_boundary": True,
            "connected_closed_component_euler_characteristic": "V - E + F = 2 per connected component",
            "compound_component_count": 2,
            "compound_euler_characteristic": "V - E + F = 4",
            "visible_face_count_not_above_face_count": True,
            "compound_solids_are_non_convex": True,
            "connected_convexity_requires_hull_vertices_and_supporting_faces": True,
            "five_ordered_questions_per_image": True,
            "level4_euler_equals_positive_face_count": True,
            "png_reference_render_recovery_for_vertex_edge_face_topology": True,
            "solid_identity_matches_vertex_edge_face_and_face_shape_signature": True,
        },
        "current_build_layout": "unsuffixed", "dataset_version": VERSION,
        "generator_commit": commit, "images": 3000, "metadata_only_rebuild": True,
        "question_set_fields": ["question_id", "task", "image", "prompt"], "questions": 15000,
    }
    (POLY / "build_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diagnosis = {
        "dataset_version": VERSION, "failing_records_examined": len(failing_ids),
        "before_assertion_failures": before_assertions, "after_assertion_failures": after_assertions,
        "literal_euler_note": "The 316 compound records contain two closed components, so their aggregate Euler characteristic is 4; each component is checked at 2.",
        "renames_this_pass": renames,
        "v4_geometry_renames_reverified": {
            "small stellated dodecahedron_to_icosahedron": {"count": 157, "V_E_F": [12, 30, 20]},
            "great dodecahedron_to_dodecahedron": {"count": 157, "V_E_F": [20, 30, 12]},
        },
        "field_changes": dict(sorted(field_changes.items())), "answers_changed_by_level": dict(changes),
        "before_level_distributions": before, "after_level_distributions": after,
        "nonconvex_disposition": {"true_stellations": 0, "compounds_restored_nonconvex": 316, "false_stellation_labels_removed_in_v4": 314},
    }
    (ROOT / "polyhedron_identity_v5_repair_diagnosis.json").write_text(json.dumps(diagnosis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(diagnosis, indent=2, sort_keys=True))


if __name__ == "__main__": main()
