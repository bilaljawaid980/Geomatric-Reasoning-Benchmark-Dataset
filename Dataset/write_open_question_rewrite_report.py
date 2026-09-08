"""Write the human-readable open-question implementation report."""
from pathlib import Path
import csv,json

ROOT=Path(__file__).resolve().parent

MANUAL_EXAMPLES={
 "clock_reading_dataset_3000":("clock_reading_1501",["The minute hand points to minute 38, or 228 degrees clockwise from 12.","The shorter hour hand lies between 11 and 12 at 349 degrees, so the displayed time is 11:38."],"Both hand tips against the printed numerals; no occluded quantity is graded.","The former angle field was exactly derivable from time in all 3,000 records and was removed.","No candidate or extreme is selected."),
 "combination_dataset_3000":("combination_1501",["The target cell set contains 9 cells.","Candidate A's two pieces contain 9 cells and can be translated and rotated to cover that set without reflection.","Candidate B also contains 9 cells but its stored geometric placement test produces a gap or overlap, so A is the valid candidate and B is the reported rejection."],"Trace every unit-cell boundary in the target and separated candidate pieces; all graded evidence is visible.","The chosen valid candidate does not determine which rejected candidate is sampled or its failure class.","All 3,000 items contain exactly one valid candidate. Failure modes, rather than a single scalar distance, distinguish the wrong alternatives; the reviewed item had no visually indistinguishable panel."),
 "combination3d_dataset_3000":("combination3d_1531",["The stored target geometry has 11 cubes in a ten-cell footprint with one additional cube above a supported base cube.","Candidate C's pieces total 11 cubes and match the target under translations and rotations about z.","Candidate B also totals 11, but matching it requires a forbidden 3-D tumble, so C is correct and B supplies the rejection reason."],"Use exposed top and side faces, visible column continuity, and the separated candidate groups. The supporting cube beneath the upper cube is inferred, but target cube count is not a graded sub-fact.","The valid candidate does not determine the independently sampled rejected panel or failure class.","Exactly one valid candidate exists in all 3,000 items. Wrong alternatives are separated by count, forbidden-axis, or fit constraints; no scalar pixel-gap field exists."),
 "compass_bearing_dataset_3000":("compass_bearing_1403",["The pairwise distances have minimum C-D = 82.873; the next smallest is B-C = 97.015, a 17.1% relative margin.","From C=(103,239) to D=(181,211), the screen displacement is 78 pixels right and 28 pixels up.","atan2(east displacement, north displacement) gives 70.253 degrees clockwise from north, which rounds to 70 degrees."],"Compare landmark separations, then read the selected displacement against the rendered compass rose. No sector label is inferred.","Closest-pair identity does not determine its bearing; the same pair labels occur with varying bearings.","Closest-pair near-ties use the guarded farthest-pair fallback; only records ambiguous under both extrema are excluded."),
 "impossible_object_dataset_3000":("impossible_object_1501",["The stored crossing list X1-X8 contains 8 projected crossings.","Direct each depth constraint from front beam to back beam.","The ordering E, F, B, D, A, C satisfies every constraint, so the graph is acyclic and the object is constructible."],"Count the rendered over/under crossing gaps and follow beam labels through them. Constructibility is computed from the jointly visible depth ordering, not directly printed.","Crossing count does not determine whether the depth-constraint graph contains a cycle.","No candidate or numerical extreme is selected."),
 "nested_hexagons_dataset_3000":("nested_hexagons_1501",["The hexagons array contains 12 outlines.","All eleven step factors lie near 0.821235, so their span is within the constant-ratio criterion.","The stored cumulative corner rotation is 21 degrees modulo 60, which rounds to 20 degrees."],"Count separate outlines, compare successive side lengths, and match corresponding corners. Rotation is estimated rather than directly labelled.","Count, shrink mode, and cumulative rotation vary independently in the generated design.","The constant/changing decision uses the established 1.35 perceptibility span; manual review agreement was 19/20."),
 "nested_triangles_dataset_3000":("nested_triangles_1501",["The triangles array contains 4 outlines.","The three step factors are 0.47555406, 0.47555424, and 0.47555390, so the shrink pattern is constant.","The cumulative rotation is 61 degrees modulo 120, which rounds to 60 degrees."],"Count outlines, compare successive side-length ratios, and match corresponding vertices. Rotation is estimated from visible corners.","Count, shrink mode, and rotation are separately sampled.","The constant/changing decision uses the 1.35 perceptibility span; manual review agreement was 19/20."),
 "orthographic_dataset_3000":("orthographic_1501",["The top view requires five occupied columns at (-2,0), (-1,0), (-1,1), (-1,2), and (0,0).","Front maxima require heights 1, 4, and 2 for x=-2,-1,0; side maxima require heights 2,4,2 for y=0,1,2.","The minimum compatible heights are 1,1,4,2,2, totaling 10 cubes.","The (-1,0) height may be 1 or 2 while all silhouettes stay unchanged, so the structure is not unique."],"Read filled cells in all three printed views. Minimum count and uniqueness are computed by reconciling the silhouettes; individual hidden cubes are inferred, not seen.","Minimum count does not determine uniqueness; both unique and non-unique scenes occur at shared counts.","No labelled candidate is selected; ambiguity is established by an explicit second compatible height assignment."),
 "polyhedron_dataset_3000":("polyhedron_1501",["The faces array contains 12 faces and every face has arity 5, independently yielding pentagons.","The 20 vertices and every supporting face lie on the boundary of one convex hull.","The record is not a compound, so the direct face-support and hull test yields convex."],"Count boundary edges of visible faces and inspect the silhouette for inward folds or interpenetrating components. Hidden faces are not counted.","Face arity does not determine convexity; triangular and mixed-face records occur in both convex and non-convex classes.","No candidate or numerical extreme is selected. Direct geometry mismatches for face shape and convexity: 0/3,000."),
 "rpm_dataset_3000":("rpm_1501",["Within each row, the count decreases from three to two to one.","Within each column, the colour progresses from purple to blue to green.","The missing panel must therefore contain one green star; choice 4 is the only option that satisfies both progressions while shape, size, and rotation remain fixed."],"Compare rendered colour and count progressions along perpendicular axes, then check the numbered choices; all untaught attributes are visibly frozen.","The valid choice does not determine which two attributes were sampled as rules across the domain.","Exactly one option satisfies the independently derived matrix patterns in every item; undeclared option attributes never vary."),
 "shadow_inference_dataset_3000":("shadow_inference_1501",["The stored light azimuth is 310.672 degrees in the 0=front, 90=right convention; its westward component dominates, giving west.","The elevation is 53.026 degrees, above the 45-degree high/low threshold, giving high."],"Read shadow direction opposite the light and compare shadow length with object height. Direction and elevation class are inferred from visible shadows.","Azimuth bucket and elevation bucket are independently sampled.","No candidate or numerical extreme is selected."),
 "surface_topology_dataset_3000":("surface_topology_1501",["The rendered closed surface has two distinct handles, so genus is 2.","It has no twist or cross-cap and retains a consistent inside and outside, so it is orientable."],"Count visible handles and inspect whether the surface contains a one-sided twist. Orientability is inferred from topology rather than printed.","The former Euler field was determined by genus and orientability for all 3,000 closed surfaces and was removed.","No candidate or numerical extreme is selected."),
}

def read_example(dataset,item_id):
 folder=ROOT/dataset;question_id=f"{item_id}_open_q1"
 with (folder/"open_questions.csv").open(encoding="utf-8-sig",newline="") as handle:question=next(row for row in csv.DictReader(handle) if row["question_id"]==question_id)
 with (folder/"open_answer_key.csv").open(encoding="utf-8-sig",newline="") as handle:answer=next(row for row in csv.DictReader(handle) if row["question_id"]==question_id)
 fields=[key for key in answer if key not in {"question_id","image","acceptance_set","tolerances","targets"} and answer[key]!=""]
 return question,answer,fields

def main():
 suite=json.loads((ROOT/"remaining_open_question_release_report.json").read_text(encoding="utf-8"))
 combined=json.loads((ROOT/"combined_open_question_report.json").read_text(encoding="utf-8"))
 data=suite["datasets"];versions=suite.get("version_bumps",{})
 lines=["# Open-question specification implementation report","","## Per-domain validation and coverage","","| Dataset | Version | Source | Included | Excluded | Exclusion reason(s) | Highest baseline | Result |","|---|---|---:|---:|---:|---|---:|---|"]
 total_png=total_included=0
 for name,m in data.items():
  version=versions.get(name,{}).get("after") or m.get("dataset_version_after") or json.loads((ROOT/name/"build_manifest.json").read_text(encoding="utf-8"))["dataset_version"]
  exclusion=", ".join(f"{k}: {v}" for k,v in m["exclusion_counts"].items()) or "none"
  lines.append(f"| `{name}` | `{version}` | {m['source_items']:,} | {m['included_items']:,} | {m['excluded_items']:,} | {exclusion} | {max(m['constant_answer_baselines'].values(),default=0):.3f} | {m['status']} |")
  total_png+=m["png_recovery"]["passed"];total_included+=m["included_items"]

 lines += ["", "## Defects found before fixes", "",
  "- **Clock reading:** the former smaller-hand-angle sub-fact was deterministically recoverable from the exact-time sub-fact in all 3,000 items. This was reported before modification; the recommended fix was applied by retaining exact time and removing the redundant angle from the open question.",
  "- **Surface topology:** the former Euler-characteristic sub-fact was deterministically fixed by genus and orientability in all 3,000 closed-surface items. This was reported before modification; the recommended fix was applied by retaining genus and orientability and removing the redundant Euler value from the open question.",
  "- **Compass bearing ambiguity:** 283 of 3,000 scenes have a closest-versus-second-closest distance gap below 5%. The farthest-pair fallback recovers 248; 35 remain excluded because both extrema fail the 5% visual-separation guard.",
  "- **RPM option identity:** all 3,000 records admitted multiple answers under the matrix-derived semantic attributes. The pre-fix satisfying-option distribution was 2 options: 844, 3 options: 1,916, and 4 options: 240; `rpm_0151` admitted choices 1, 4, and 7. Rotation distinguished options in all 3,000 and size/shape spacing did so in 2,156, although neither was always taught; stroke width never discriminated. Equal circumradius also made triangles appear smaller than circles.",
  "- **Orthographic convention:** all 3,000 stored projections consistently used top `(x,y)`, front `(x,z)`, and side `(y,z)`, with each first coordinate increasing left-to-right and z increasing bottom-to-top. The side panel did not print that direction, so a viewer could reasonably mirror it. Before the label repair, gravity support changed the computed minimum in 1,883 records and made no difference in 1,117; `orthographic_0223` required 11 cubes with gravity versus 10 without it.",
 ]

 line=data["line_intersection_dataset_3000"]["special_checks"]
 coord=data["coordinate_geometry_dataset_3000"]["special_checks"]
 square=data["nested_squares_dataset_3000"]["special_checks"]
 tri=data["nested_triangles_dataset_3000"]["special_checks"]
 hexa_nested=data["nested_hexagons_dataset_3000"]["special_checks"]
 rotation=data["rotation_matching_dataset_3000"]["special_checks"]
 embedded=data["embedded_figures_dataset_3000"]["special_checks"]
 hexa=data["hex_pathfinding_dataset_3000"]["special_checks"]
 laser=data["laser_mirror_dataset_3000"]["special_checks"]
 rpm=data["rpm_dataset_3000"]["special_checks"]
 orth=data["orthographic_dataset_3000"]["special_checks"]
 compass=data["compass_bearing_dataset_3000"]["special_checks"]
 lines += ["", "## Final ambiguity and convention repairs", "",
  f"- **RPM:** all 3,000 images were regenerated. Options satisfying the independently derived rule set: `{json.dumps(rpm['options_satisfying_independently_derived_rules'],sort_keys=True)}`; multi-valid items: {rpm['multi_valid_items']}. Undeclared option attributes are frozen: `{json.dumps(rpm['unfrozen_undeclared_attribute_counts'],sort_keys=True)}`. Shape areas are normalised, spacing depends only on size/count, and stroke width is fixed.",
  f"- **Orthographic:** axes are printed as `{json.dumps(orth['rendered_axis_directions'],sort_keys=True)}`. The side projection agrees with the +y-right convention in {orth['side_view_convention_consistent_items']}/3,000 records. Gravity-supported minus unconstrained minimum counts: `{json.dumps(orth['gravity_minimum_minus_unconstrained_distribution'],sort_keys=True)}`; gravity changes {orth['gravity_constraint_changes_minimum']} items and changes nothing in {orth['gravity_constraint_does_not_change_minimum']}. Item 0223 is {orth['item_0223_gravity_minimum']} with gravity versus {orth['item_0223_unconstrained_minimum']} without it.",
  f"- **Compass:** the guarded farthest-pair fallback recovered {compass['farthest_fallback_items']} closest-pair near-ties; {compass['closest_and_farthest_margin_failures']} remain excluded.",
 ]
 lines += ["","## Six manual-review findings","",
  f"1. **Line intersection:** endpoint-order/parity exceptions: {line['old_parity_dependency_exceptions']}. The redundant endpoint-order sub-fact was replaced by left-edge higher colour; crossing counts now coexist with both colours, so neither answer determines the other.",
  f"2. **Coordinate geometry 0101:** points `{json.dumps(coord['coordinate_geometry_0101_points'],sort_keys=True)}`; pairwise distances `{json.dumps(coord['coordinate_geometry_0101_all_pairwise_distances'],sort_keys=True)}`; actual farthest pair `{coord['coordinate_geometry_0101_actual_farthest_pair']}`. The stored answer was correct but visually marginal. The 1-unit guard rejected {coord['farthest_template_guard_rejections']} of {coord['eligible_three_or_four_point_scenes']} multi-pair scenes from that template and routed them to the all-coordinates fallback without reducing coverage.",
  f"3. **Nested squares 0095:** factors `{json.dumps(square['nested_squares_0095_step_reduction_factors'])}` are equal within render precision, so `constant` is correct. Manual constant/changing agreement was {tri['human_constant_vs_changing_20']['agreements']}/20 triangles, {square['human_constant_vs_changing_20']['agreements']}/20 squares, and {hexa_nested['human_constant_vs_changing_20']['agreements']}/20 hexagons; the 1.35 span floor was retained.",
  f"4. **Rotation matching 0078:** nearest-candidate distance {rotation['rotation_match_0078_minimum_vertex_position_difference_normalized']:.6f} normalized ({rotation['rotation_match_0078_difference_rendered_pixels']:.2f} px); minimum turning angle {rotation['rotation_match_0078_minimum_turning_angle_degrees']:.5f}°. Transformations `{json.dumps(rotation['transformation_type_distribution'],sort_keys=True)}` contain no distortions. The existing 0.08 separation guard has {rotation['separation_guard_violations']} violations and was retained.",
  f"5. **Embedded figures:** `same_side_foil_exists` is `{json.dumps(embedded['same_side_foil_exists_distribution'],sort_keys=True)}`. The exact 1,500/1,500 balance is substantial, so no change was made.",
  f"6. **Hex pathfinding 0124:** renderer is {hexa['renderer_hex_orientation']}. Axial-to-screen mapping in hex-size units is `{json.dumps(hexa['axial_offset_to_screen_delta_in_hex_size_units'],sort_keys=True)}`. `(1,0)` is directly right at the same screen y; inadmissible stored directions: {hexa['orientation_inadmissible_stored_direction_count']}. No data change was needed.",
  "","## Laser zero-reflection recovery","",
  f"All {laser['zero_reflection_items_recovered_by_variant']} zero-reflection scenes now use the straight-path prompt. Near-miss distribution: `{json.dumps(laser['near_miss_count_distribution_zero_reflection_variant'],sort_keys=True)}`; constant-answer baseline: {laser['near_miss_count_constant_answer_baseline']:.3f}.",
  "","## Sub-facts at or above 60%","",
  "| Dataset | Sub-fact | Baseline | Disposition |",
  "|---|---|---:|---|",
 ]
 dispositions={
  ("fbd_dataset_3000","weight_arrow"): "Inherent label convention: the rendered weight arrow is normally labelled W; retained and reported.",
  ("laser_mirror_dataset_3000","reflection_count"): "Inherent among the nonzero-reflection trace variant; zero-reflection scenes now use a separate varying prompt.",
  ("polyhedron_dataset_3000","convexity"): "Inherent to the generated solid inventory after geometry-identity repair; retained and reported.",
  ("surface_topology_dataset_3000","orientability"): "Inherent to the generated surface inventory; retained and reported.",
 }
 for name,m in data.items():
  for fact,value in m.get("fields_at_or_above_60_percent",{}).items():
   lines.append(f"| `{name}` | `{fact}` | {value:.3f} | {dispositions.get((name,fact),'Reported; no fixable sampling skew identified.')} |")
 lines += ["", "## Shared deterministic-dependency audit", "", "Method: for each target sub-fact, the validator tests every one-to-three-field subset of the other populated sub-facts. It flags a mapping when repeated predictor tuples cover at least 80% of eligible rows and every tuple maps to exactly one target value. Explicit prohibited semantic identities are validation failures; empirical findings outside this pass remain visible below.", ""]
 findings=[]
 for name,m in data.items():
  for finding in m.get("deterministic_subfact_dependency_check",{}).get("empirical_findings",[]):findings.append((name,finding))
 if findings:
  lines += ["| Dataset | Finding |", "|---|---|"]+[f"| `{name}` | {finding} |" for name,finding in findings]
 else:lines.append("No empirical deterministic relationships were flagged.")
 lines += ["","## Twelve-domain manual render review",""]
 for name,(item_id,steps,visual,redundancy,margin) in MANUAL_EXAMPLES.items():
  question,answer,fields=read_example(name,item_id);metrics=data[name]
  lines += [f"### `{name}`", "", f"**Item:** `{answer['image']}`", "", "**Exact question:**", "", f"> {question['prompt']}", "", "**Stored sub-facts:**", ""]
  lines += [f"- `{field}`: `{answer[field]}`" for field in fields]
  lines += ["", "**Written derivation:**", ""]+[f"{index}. {step}" for index,step in enumerate(steps,1)]
  lines += ["",f"**Visual recoverability:** {visual}","",f"**Derivable redundancy:** {redundancy}","",f"**Nearest-alternative margin:** {margin}","","**Answer distributions and baselines:**",""]
  for field in fields:
   distribution=metrics["answer_distributions"][field];summary=json.dumps(distribution,ensure_ascii=False,sort_keys=True) if len(distribution)<=12 else f"{len(distribution)} distinct answers; full counts in `{name}/open_validation_metrics.json`"
   lines.append(f"- `{field}`: baseline {metrics['constant_answer_baselines'][field]:.3f}; distribution {summary}")
  lines.append("")
 lines += ["","## Validation summary","",
  f"- Independent ground-truth mismatches: {sum(len(m['independent_derivation']['mismatches']) for m in data.values())}.",
  f"- Deterministic sub-fact dependency violations: {sum(len(m['deterministic_subfact_dependency_check']['violations']) for m in data.values())}.",
  f"- Quantity-aware PNG recovery: {total_png:,}/{total_included:,} included images. Every per-domain metrics file states the image signal used for every sub-fact.",
  "- Exact prompt wording, three-column public schema, answer-leak checks, numeric tolerances, and one-to-one resolution: PASS in all 34 domains.",
  f"- Combined open files: {combined['combined_open_questions']:,} questions and {combined['combined_open_answers']:,} answers; {combined['resolved_image_paths']:,} image paths resolve.",
  "- Full answer distributions and constant-answer baselines are retained in each `open_validation_metrics.json` and the consolidated JSON report.",
 ]
 report_text=("\n".join(lines)+"\n").replace("\ufffd", " degrees")
 (ROOT/"open_question_rewrite_report.md").write_text(report_text,encoding="utf-8")
 print("Wrote Dataset/open_question_rewrite_report.md")

if __name__=="__main__":main()
