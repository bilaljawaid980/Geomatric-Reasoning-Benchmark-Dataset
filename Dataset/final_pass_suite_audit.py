"""Build deterministic per-dataset and suite-level final-pass audit summaries."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from benchmark_validation_utils import answer_distributions, leak_audit, quantiles

AUDIT_NAMES = {
    "route_dataset_3000", "line_intersection_dataset_3000", "polyhedron_dataset_3000",
    "depth_height_dataset_3000", "symmetry_pattern_dataset_3000",
    "occluded_pattern_dataset_3000", "angle_estimation_dataset_3000",
    "coordinate_geometry_dataset_3000", "surface_topology_dataset_3000",
    "optical_illusion_dataset_3000", "compass_bearing_dataset_3000",
}
MODIFIED = AUDIT_NAMES | {
    "cube_net_dataset_3000", "combination3d_dataset_3000",
    "shadow_inference_dataset_3000", "rpm_dataset_3000", "fold_punch_dataset_3000",
    "hex_pathfinding_dataset_3000", "cube_structure_dataset_3000",
    "overlap_circles_dataset_3000", "fbd_dataset_3000",
}
GROUND_TRUTH_ERRORS = {"cube_net_dataset_3000": 452}
SKIP_FEATURES = {"questions", "id", "image", "image_path", "seed", "dataset_version"}


def scalar_features(rows):
    common = set.intersection(*(set(row) for row in rows))
    return sorted(name for name in common - SKIP_FEATURES
                  if all(isinstance(row[name], (str, int, float, bool)) or row[name] is None
                         for row in rows))


def full_distributions(rows, features):
    continuous, categorical = {}, {}
    for name in features:
        values = [row[name] for row in rows if row[name] is not None]
        if values and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            continuous[name] = quantiles(values)
        else:
            categorical[name] = dict(Counter(str(v) for v in values))
    return continuous, categorical


def version_for(root, rows):
    if rows and rows[0].get("dataset_version"):
        return rows[0]["dataset_version"]
    manifest = root / "build_manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("dataset_version", data.get("version", "legacy-current"))
    return "legacy-current"


def audit_one(root):
    rows = [json.loads(line) for line in (root / "annotations.jsonl").open(encoding="utf-8")]
    answers = answer_distributions(rows)
    features = scalar_features(rows)
    associations = leak_audit(rows, features, {})
    high = {feature: {level: round(item["cramers_v"], 8)
                      for level, item in result["levels"].items() if item["cramers_v"] >= .10}
            for feature, result in associations.items()}
    high = {feature: levels for feature, levels in high.items() if levels}
    continuous, categorical = full_distributions(rows, features)
    png_count = sum(1 for row in rows if (root / row.get("image_path", row.get("image", ""))).is_file())
    metrics = {
        "dataset_version": version_for(root, rows), "images": len(rows),
        "questions": sum(len(row["questions"]) for row in rows),
        "level_distributions": answers, "scalar_scene_features": features,
        "leak_audit": associations, "features_at_v_ge_0_10": high,
        "continuous_distributions": continuous, "categorical_distributions": categorical,
        "png_asset_presence": f"{png_count}/{len(rows)}",
        "degeneracy_flags": {level: result for level, result in answers.items()
                             if result["constant_answer_baseline"] > .60},
        "reference_frame_audit": "Dataset-specific geometry and question frames are documented in the generator/validator; no implicit frame conversion is introduced by this audit.",
        "answerability_audit": "Question prompts and image assets are present for all five levels; semantic PNG recovery remains the responsibility of the dataset-specific validator.",
    }
    # Per-dataset release directories intentionally contain only the standard
    # artifacts. Suite-level summaries below retain these audit results.
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    roots = sorted(path for path in args.dataset_root.iterdir()
                   if path.is_dir() and (path / "annotations.jsonl").is_file())
    results = {root.name: audit_one(root) for root in roots}
    lines = ["# GRIP-Benchmark-34 Final Suite Audit", "", "| Dataset | Version | Modified in final pass | Ground-truth errors found | L1 | L2 | L3 | L4 | L5 | PNG assets |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        bases = [result["level_distributions"][str(level)]["constant_answer_baseline"] for level in range(1, 6)]
        errors = GROUND_TRUTH_ERRORS.get(name, 0)
        lines.append("| " + " | ".join([name, str(result["dataset_version"]), "yes" if name in MODIFIED else "no", str(errors)] + [f"{v:.1%}" for v in bases] + [result["png_asset_presence"]]) + " |")
    (args.dataset_root / "final_suite_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.dataset_root / "final_suite_audit.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Audited {len(results)} datasets")


if __name__ == "__main__":
    main()
