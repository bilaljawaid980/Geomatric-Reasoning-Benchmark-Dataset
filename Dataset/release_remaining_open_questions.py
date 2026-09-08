"""Apply version, manifest, README, and open-annotation metadata for the 34-domain rewrite."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import build_remaining_open_questions as builder

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
SOURCE_COMMIT=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()


def bumped(version,name):
    if version=="legacy-current":
        slug=name.rsplit("_dataset_",1)[0].replace("_","-")
        return f"{slug}-2.0.0"
    match=re.match(r"(.+)-(\d+)\.(\d+)\.(\d+)$",version)
    if not match:raise ValueError(f"Cannot bump {name}: {version}")
    return f"{match.group(1)}-{int(match.group(2))+1}.0.0"


def rewrite_jsonl_version(path,version):
    rows=[]
    with path.open(encoding="utf-8-sig") as h:
        for line in h:
            if line.strip():
                row=json.loads(line);row["dataset_version"]=version;rows.append(row)
    with path.open("w",encoding="utf-8",newline="\n") as h:
        for row in rows:h.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--domain",action="append",choices=sorted(builder.DERIVERS))
    args=parser.parse_args()
    release=json.loads((ROOT/"remaining_open_question_release_report.json").read_text(encoding="utf-8"))
    versions={}
    for name in args.domain or sorted(builder.DERIVERS):
        folder=ROOT/name; manifest_path=folder/"build_manifest.json";manifest=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        metrics=release["datasets"][name]
        old=str(manifest.get("dataset_version","legacy-current"));new=bumped(old,name);versions[name]={"before":old,"after":new}
        rewrite_jsonl_version(folder/"annotations.jsonl",new);rewrite_jsonl_version(folder/"open_annotations.jsonl",new)
        manifest["dataset_version"]=new
        manifest["open_questions"]=int(metrics["included_items"])
        manifest["open_excluded_items"]=int(metrics["excluded_items"])
        manifest["open_exclusion_counts"]=metrics["exclusion_counts"]
        manifest["open_question_files"]=["open_questions.csv","open_answer_key.csv","open_annotations.jsonl"]
        constraints=manifest.setdefault("constraint_set",{})
        constraints.update({
            "existing_five_level_questions_unchanged_except_approved_defect_repairs":True,
            "open_question_count_per_eligible_image":1,
            "open_exclusions_are_explicitly_reported":True,
            "open_public_fields_exact":["question_id","image","prompt"],
            "open_ground_truth_rederived_from_scene_metadata":True,
            "open_prompt_no_unrendered_coordinate_scheme":True,
            "open_no_deterministically_redundant_subfacts":True,
            "open_no_none_placeholders":True,
            "open_numeric_tolerances_stored_and_stated":True,
            "open_prompt_does_not_name_reasoning_trap":True,
            "open_png_recoverability_all_items":True,
            "open_quantity_recovery_signals_documented_per_subfact":True,
        })
        if name=="angle_estimation_dataset_3000":constraints.update({"open_triangle_vertex_label_subfact_removed_for_fixed_order_bias":True,"open_single_angle_class_removed_as_determined_by_rounded_size":True})
        elif name=="clock_reading_dataset_3000":constraints["open_time_derived_angle_subfact_removed"]=True
        elif name=="compass_bearing_dataset_3000":constraints.update({"open_bearing_numeric_tolerance_degrees":10,"open_closest_pair_minimum_relative_margin":0.05,"open_farthest_pair_fallback_minimum_relative_margin":0.05,"open_named_ab_fallback_for_dual_margin_failures":True,"open_sector_boundary_exclusion_removed":True})
        elif name=="coordinate_geometry_dataset_3000":constraints.update({"open_distance_relation_threshold_units":12,"open_farthest_pair_minimum_separation_units":1,"open_farthest_guard_fallback":"report all labelled point coordinates"})
        elif name=="cube_structure_dataset_3000":constraints.update({"open_visible_top_face_count_replaces_unrecoverable_base_layer_count":True,"open_cube_manual_visual_audit_items":20})
        elif name=="depth_height_dataset_3000":constraints.update({"open_stack_height_variant_covers_all_stack_scenes":True,"open_order_extrema_subfacts_removed_as_deterministic":True})
        elif name=="embedded_figures_dataset_3000":constraints["open_side_count_removed_as_determined_by_candidate_schedule"]=True
        elif name=="fbd_dataset_3000":constraints["open_arrow_count_and_weight_label_removed_as_determined_by_ranking"]=True
        elif name=="fold_punch_dataset_3000":constraints["open_hole_count_removed_as_determined_by_candidate_schedule"]=True
        elif name=="gear_train_dataset_3000":constraints["open_direction_target_relation_balanced"]=True
        elif name=="hex_pathfinding_dataset_3000":constraints.update({"open_hex_orientation":"pointy-top","open_axial_direction_vocabulary_verified":True,"open_boundary_and_neighbour_counts_removed_as_determined_by_hole_neighbourhood":True})
        elif name=="laser_mirror_dataset_3000":constraints.update({"open_zero_reflection_variant":True,"open_near_miss_definition":"mirror cell shares an edge with a traversed path cell without lying on the path"})
        elif name=="line_intersection_dataset_3000":constraints.update({"open_endpoint_parity_redundancy_removed":True,"open_independent_left_edge_colour_subfact":True})
        elif name=="overlap_circles_dataset_3000":constraints["open_isolated_circle_subfact_removed_for_sampling_bias"]=True
        elif name=="orthographic_dataset_3000":constraints.update({"rendered_axis_directions":{"top":"+x right; +y up","front":"+x right; +z up","side":"+y right; +z up"},"gravity_supported_minimum_compared_with_unconstrained_minimum":True})
        elif name=="projectile_motion_dataset_1000":constraints["open_peak_threshold_metres"]=13
        elif name=="surface_topology_dataset_3000":constraints["open_euler_subfact_removed_as_derivable_from_genus_and_orientability"]=True
        elif name=="rpm_dataset_3000":constraints.update({"rpm_exactly_one_option_satisfies_independently_derived_rules":True,"rpm_undeclared_option_attributes_frozen":True,"rpm_declared_rules_visibly_vary":True,"rpm_equal_area_shape_rendering":True,"rpm_spacing_depends_only_on_size_and_count":True})
        if name=="fold_punch_dataset_3000":constraints["approved_closed_repair"]="312 duplicated Level 5 rows replaced by additional-fold counterfactual"
        elif name=="overlap_circles_dataset_3000":constraints["approved_closed_repair"]="1034 leaked Level 3 field-name answers corrected to clustered or spread"
        manifest["generator_commit"]=SOURCE_COMMIT
        manifest["open_question_builder"]="../build_remaining_open_questions.py"
        manifest["open_question_validator"]="../validate_remaining_open_questions.py"
        manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        readme_path=folder/"README.md";text=readme_path.read_text(encoding="utf-8-sig")
        heading="### Supplementary open-ended questions"
        if heading in text:text=text.split(heading)[0].rstrip()+"\n"
        section=(
            f"\n{heading}\n\nVersion `{new}` replaces the supplementary free-response set with the exact approved domain template or scene-specific variant in `OPEN_QUESTION_SPEC.md`. It includes `{metrics['included_items']}` eligible items and excludes `{metrics['excluded_items']}` under `{json.dumps(metrics['exclusion_counts'],sort_keys=True)}`. Every prompt uses visible evidence, asks for justification, and ends with a confidence score from 0 to 1.\n\n"
            "- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.\n"
            "- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.\n"
            "- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.\n"
            "- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.\n\n"
            f"Scored fields at or above 60% after template revision: `{json.dumps(metrics['fields_at_or_above_60_percent'],sort_keys=True)}`. "
            f"Targeted fields: `{', '.join(metrics['subfacts'])}`. "
            "Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.\n"
        )
        readme_path.write_text(text.rstrip()+"\n"+section,encoding="utf-8")
    for name,change in versions.items():
        release["datasets"][name]["dataset_version_before"]=change["before"]
        release["datasets"][name]["dataset_version_after"]=change["after"]
    release["version_bumps"]=versions;release["source_commit_before_release"]=SOURCE_COMMIT
    (ROOT/"remaining_open_question_release_report.json").write_text(json.dumps(release,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(versions,indent=2))


if __name__=="__main__":main()
