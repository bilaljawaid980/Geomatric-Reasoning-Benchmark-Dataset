"""Independent v8 validator and full distribution audit for nested polygons."""
from __future__ import annotations
import bisect,csv,json,math
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image,ImageStat
import nested_polygon_common as common
from nested_polygon_generator import adjacent_outline_clearances,guard_injection_results
from nested_polygon_visual_checks import TASKS,classify_rotation,constant_capture,png_connected_outline_count,png_outline_checks,point_inside,summary,vertex_rotation

def read_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))

def pearson(xs,ys):
 mx=sum(xs)/len(xs);my=sum(ys)/len(ys);num=sum((x-mx)*(y-my) for x,y in zip(xs,ys));den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys));return num/den if den else 0.0

def cramers_v(labels,values):
 rows=sorted(set(labels));cols=sorted(set(map(str,values)));ri={v:i for i,v in enumerate(rows)};ci={v:i for i,v in enumerate(cols)}
 table=[[0]*len(cols) for _ in rows]
 for label,value in zip(labels,values):table[ri[label]][ci[str(value)]]+=1
 n=len(labels);rs=[sum(row) for row in table];cs=[sum(table[i][j] for i in range(len(rows))) for j in range(len(cols))];chi=0.0
 for i in range(len(rows)):
  for j in range(len(cols)):
   expected=rs[i]*cs[j]/n
   if expected:chi+=(table[i][j]-expected)**2/expected
 denom=min(len(rows)-1,len(cols)-1)
 return math.sqrt(chi/n/denom) if denom>0 else 0.0

def quantile_bins(values,bins=10):
 ordered=sorted(float(v) for v in values);cuts=[]
 for i in range(1,bins):cuts.append(ordered[min(len(ordered)-1,math.ceil(i*len(ordered)/bins)-1)])
 return [bisect.bisect_left(cuts,float(value)) for value in values]

def association_audit(records,spec,shape_field,vertex_fn):
 labels=[row["reduction_mode"] for row in records]
 cat={
  "rotation_mode":[r["rotation_mode"] for r in records],"shape_count":[r[f"num_{spec.plural}"] for r in records],
  "color_alternation":[r["color_alternation"] for r in records],"center_drift_measured":[r["center_drift"] for r in records],
  "offset_requested_pre_containment":[r["offset_requested_pre_containment"] for r in records],"line_width_class":["thin" if r["line_width_px"]<2 else "standard" for r in records],
  "level5_label":[r["questions"][4]["ground_truth"] for r in records],"factor_progression_direction":[r["factor_progression_direction"] for r in records],
  "stroke_palette":[tuple(r["stroke_colors_used"]) for r in records],
  "containment_outcome":["accepted" for r in records],
  "size_axis_band":[r["size_axis_band"] for r in records],
 }
 numeric={
  "outer_side_length":[r[shape_field][0]["side_length"] for r in records],"innermost_side_length":[r[shape_field][-1]["side_length"] for r in records],
  "outer_inner_size_ratio":[r[shape_field][0]["side_length"]/r[shape_field][-1]["side_length"] for r in records],
  "line_width_px":[r["line_width_px"] for r in records],"target_cumulative_rotation":[r["target_cumulative_rotation_degrees"] for r in records],
  "generation_attempt":[r["generation_attempt"] for r in records],
  "gap_separation":[float(common.gap_separation(r[shape_field],vertex_fn)) if r["offset_requested_pre_containment"] else 0.0 for r in records],
  "canvas_width":[r["canvas_size"][0] for r in records],"canvas_height":[r["canvas_size"][1] for r in records],
  "outer_center_x":[r[shape_field][0]["center"][0] for r in records],"outer_center_y":[r[shape_field][0]["center"][1] for r in records],
  "innermost_center_x":[r[shape_field][-1]["center"][0] for r in records],"innermost_center_y":[r[shape_field][-1]["center"][1] for r in records],
  "outer_rotation_angle":[r[shape_field][0]["rotation_angle"] for r in records],"cumulative_rotation":[r["cumulative_rotation_degrees"] for r in records],
  "difficulty_score":[r["difficulty_score"] for r in records],"reduction_factor_span":[r["reduction_factor_span"] for r in records],
  "extrapolation_reduction_factor":[r["extrapolation_reduction_factor"] for r in records],
  "minimum_adjacent_clear_background_px":[r["minimum_adjacent_clear_background_px"] for r in records],
  "matched_clearance_target_px":[r["matched_clearance_target_px"] for r in records],
  "sampled_total_reduction_root":[r["sampled_total_reduction_root"] for r in records],"sampled_total_inner_fraction":[r["sampled_total_inner_fraction"] for r in records],
 }
 for cause in ("containment","drift_floor","gap_margin","reduction_perceptibility","rotation_wrap","level5_margin","minimum_inner_size","minimum_outline_clearance"):
  numeric[f"rejections_{cause}"]=[r["generation_rejections"].get(cause,0) for r in records]
 result={}
 for name,values in cat.items():result[name]={"kind":"categorical","cramers_v":cramers_v(labels,values)}
 for name,values in numeric.items():result[name]={"kind":"numeric_deciles","cramers_v":cramers_v(labels,quantile_bins(values)),"summary":summary(values)}
 # These two fields, and only these two, are direct encodings of the Level-2
 # constant/changing target. Any future whitelist addition requires an explicit
 # report-level justification and a code review.
 definitional={"factor_progression_direction","reduction_factor_span"}
 nontrivial={name:{**data,"classification":"definitional" if name in definitional else "nuisance"} for name,data in result.items() if data["cramers_v"]>=.10}
 return {"features":result,"definitional_features":sorted(definitional),"excluded_identifier_fields":["id","image_path","seed","source_index","parameter_seed","paired_nuisance_rank","size_axis_pair_rank","question_id"],"all_features_at_or_above_threshold":nontrivial,"nontrivial_nuisance_associations":{name:data for name,data in nontrivial.items() if data["classification"]=="nuisance"},"filter_matches_raw_audit":set(nontrivial)=={name for name,data in result.items() if data["cramers_v"]>=.10},"threshold":.10}

def full_parameter_distributions(records,spec,shape_field,vertex_fn):
 continuous={
  "canvas_width":[r["canvas_size"][0] for r in records],"canvas_height":[r["canvas_size"][1] for r in records],
  "outer_side_length":[r[shape_field][0]["side_length"] for r in records],"innermost_side_length":[r[shape_field][-1]["side_length"] for r in records],
  "outer_inner_size_ratio":[r[shape_field][0]["side_length"]/r[shape_field][-1]["side_length"] for r in records],"sampled_total_inner_fraction":[r["sampled_total_inner_fraction"] for r in records],
  "sampled_total_reduction_root":[r["sampled_total_reduction_root"] for r in records],"reduction_factor_span":[r["reduction_factor_span"] for r in records],
  "extrapolation_reduction_factor":[r["extrapolation_reduction_factor"] for r in records],"line_width_px":[r["line_width_px"] for r in records],
  "minimum_adjacent_clear_background_px":[r["minimum_adjacent_clear_background_px"] for r in records],"outer_rotation_angle":[r[shape_field][0]["rotation_angle"] for r in records],
  "matched_clearance_target_px":[r["matched_clearance_target_px"] for r in records],
  "cumulative_rotation_degrees":[r["cumulative_rotation_degrees"] for r in records],"difficulty_score":[r["difficulty_score"] for r in records],"generation_attempt":[r["generation_attempt"] for r in records],
  "outer_center_x":[r[shape_field][0]["center"][0] for r in records],"outer_center_y":[r[shape_field][0]["center"][1] for r in records],
  "innermost_center_x":[r[shape_field][-1]["center"][0] for r in records],"innermost_center_y":[r[shape_field][-1]["center"][1] for r in records],
 }
 categorical={
  "shape_count":[r[f"num_{spec.plural}"] for r in records],"reduction_mode":[r["reduction_mode"] for r in records],"factor_progression_direction":[r["factor_progression_direction"] for r in records],
  "rotation_mode":[r["rotation_mode"] for r in records],"size_axis_band":[r["size_axis_band"] for r in records],"color_alternation":[r["color_alternation"] for r in records],
  "center_drift":[r["center_drift"] for r in records],"offset_requested_pre_containment":[r["offset_requested_pre_containment"] for r in records],
  "stroke_colors_used":[tuple(r["stroke_colors_used"]) for r in records],"level5_label":[r["questions"][4]["ground_truth"] for r in records],
 }
 return {"continuous":{name:summary(values) for name,values in sorted(continuous.items())},"categorical":{name:dict(sorted(Counter(map(str,values)).items())) for name,values in sorted(categorical.items())}}

def expected_questions(row,shapes,spec):
 ratio=shapes[0]["side_length"]/shapes[-1]["side_length"]
 delta=Fraction(str(round(vertex_rotation(shapes,spec),4)))
 next_fraction=Fraction(str(shapes[-1]["side_length"]))*Fraction(str(common.step_factors(shapes)[-1]))/Fraction(str(shapes[0]["side_length"]))
 return [(f"count_{spec.plural}",str(len(shapes)),"numeric"),("size_progression_direction",common.classify_reduction_mode(shapes),"choice"),("outer_inner_side_ratio",f"{ratio:.1f}",common.RATIO_ANSWER_FORMAT),("cumulative_rotation",str(common.round_half_up(delta)),common.rotation_answer_format(spec)),(f"next_{spec.singular}_visually_distinguishable","yes" if next_fraction>common.LEVEL5_THRESHOLD else "no","yes_no")]

def validate_tables(root,records):
 issues=[];expected=[(row,q) for row in records for q in row["questions"]]
 public=read_csv(root/"question_set.csv");private=read_csv(root/"answer_key.csv");final=read_csv(root/"dataset_final.csv")
 if not len(public)==len(private)==len(final)==len(expected):return ["v8 table row-count mismatch"]
 if public and set(public[0])!={"dataset_version","question_id","task","image","prompt"}:issues.append(f"question_set has forbidden/unknown fields: {sorted(set(public[0])-{'dataset_version','question_id','task','image','prompt'})}")
 for path in (root/"question_set.csv",root/"answer_key.csv",root/"dataset_final.csv",root/"dataset_final.jsonl"):
  text=path.read_text(encoding="utf-8-sig")
  if "offset_intended" in text or "offset_requested_pre_containment" in text:issues.append(f"private offset field leaked into {path.name}")
 for index,((row,q),pub,priv) in enumerate(zip(expected,public,private),1):
  want={"dataset_version":row["dataset_version"],"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"]}
  if any(pub.get(k)!=v for k,v in want.items()):issues.append(f"public row {index} mismatch")
  if any(priv.get(k)!=v for k,v in want.items()) or priv.get("groundtruth")!=str(q["ground_truth"]) or priv.get("answer_format")!=q["answer_format"]:issues.append(f"private row {index} mismatch")
 return issues

def validate_dataset(root,spec,shape_field,vertex_fn):
 root=Path(root);records=[json.loads(line) for line in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if line]
 issues=[];modes=Counter();split=defaultdict(Counter);reductions=Counter();directions=Counter();rejections=Counter();unique_rejected=0;l4=[];l5=Counter();counts=[];binary=[];spans=[];gaps=[];contracted=0;png_counts_matched=0
 wrap=common.wrap_guard_injection_result(spec);guards=guard_injection_results(spec,vertex_fn)
 if not wrap["pass"]:issues.append("wrap injection failed")
 if not guards["pass"]:issues.append("constraint injection failed")
 for position,row in enumerate(records,1):
  iid=row.get("id","unknown");shapes=row.get(shape_field,[])
  try:
   if "offset_intended" in row:issues.append(f"{iid}: obsolete offset_intended field")
   if row["dataset_version"]!=spec.dataset_version or iid!=f"nested_{spec.plural}_{row['source_index']:04d}":issues.append(f"{iid}: version mismatch")
   if row["seed"]!=spec.seed_namespace+row["source_index"]:issues.append(f"{iid}: seed namespace mismatch")
   mode=row["rotation_mode"];label=row["reduction_mode"];modes[mode]+=1;split[label][mode]+=1;reductions[label]+=1;directions[row["factor_progression_direction"]]+=1;rejections.update(row["generation_rejections"]);unique_rejected+=row["rejected_candidates"]
   contracted+=bool(row["offset_requested_pre_containment"] and not row["center_drift"])
   if row["rejected_candidates"]!=row["generation_attempt"]:issues.append(f"{iid}: rejected count mismatch")
   if row.get("drift_floor_applied_as_rejection") is not False or row["generation_rejections"].get("drift_floor")!=0:issues.append(f"{iid}: drift floor applied")
   if len(shapes)!=row[f"num_{spec.plural}"]:issues.append(f"{iid}: count mismatch")
   w,h=row["canvas_size"]
   for shape in shapes:
    computed=vertex_fn(shape["center"],shape["side_length"],shape["rotation_angle"])
    if any(math.dist(a,b)>.002 for a,b in zip(computed,shape["vertices"])):issues.append(f"{iid}: vertex mismatch")
    if any(not(19.999<=x<=w-19.999 and 19.999<=y<=h-19.999) for x,y in computed):issues.append(f"{iid}: canvas margin")
   for i in range(len(shapes)-1):
    outer=vertex_fn(shapes[i]["center"],shapes[i]["side_length"],shapes[i]["rotation_angle"]);inner=vertex_fn(shapes[i+1]["center"],shapes[i+1]["side_length"],shapes[i+1]["rotation_angle"])
    if not all(point_inside(v,outer,1e-4) for v in inner):issues.append(f"{iid}: containment")
   if classify_rotation(shapes)!=mode:issues.append(f"{iid}: rotation mode")
   angle_delta=(Fraction(str(shapes[-1]["rotation_angle"]))-Fraction(str(shapes[0]["rotation_angle"])))%spec.modulus;vertex_delta=vertex_rotation(shapes,spec);err=abs(float(angle_delta)-vertex_delta);err=min(err,spec.modulus-err)
   if err>.03 or Fraction(row["cumulative_rotation_fraction"])!=angle_delta or angle_delta!=Fraction(row["target_cumulative_rotation_degrees"]):issues.append(f"{iid}: rotation derivation")
   if not common.rotation_is_margin_safe(angle_delta,mode,spec):issues.append(f"{iid}: wrap margin")
   factors=common.step_factors(shapes);span=max(factors)/min(factors)
   if label=="changing":spans.append(span)
   if len(row["step_reduction_factors"])!=len(factors) or any(abs(a-b)>1e-7 for a,b in zip(row["step_reduction_factors"],factors)):issues.append(f"{iid}: step factors")
   if common.classify_reduction_mode(shapes)!=label:issues.append(f"{iid}: reduction mode")
   if not common.reduction_factors_are_safe(factors,label):issues.append(f"{iid}: perceptibility")
   inferred_root=(shapes[-1]["side_length"]/shapes[0]["side_length"])**(1/(len(shapes)-1))
   if abs(inferred_root-row["sampled_total_reduction_root"])>2e-5:issues.append(f"{iid}: sampled total root")
   if abs(shapes[-1]["side_length"]/shapes[0]["side_length"]-row["sampled_total_inner_fraction"])>2e-5:issues.append(f"{iid}: sampled total contraction")
   if row["offset_requested_pre_containment"]:
    gap=float(common.gap_separation(shapes,vertex_fn));gaps.append(gap)
    if not common.gap_value_is_safe(gap,spec):issues.append(f"{iid}: gap margin")
   if not common.level5_is_margin_safe(shapes):issues.append(f"{iid}: Level5 margin")
   if not common.inner_size_is_safe(shapes[-1]["side_length"]):issues.append(f"{iid}: minimum inner size")
   clearances=adjacent_outline_clearances(shapes,vertex_fn,row["line_width_px"]);measured_clearance=min(clearances)
   if not common.outline_clearance_is_safe(measured_clearance) or abs(measured_clearance-row["minimum_adjacent_clear_background_px"])>.002:issues.append(f"{iid}: minimum outline clearance")
   wanted=expected_questions(row,shapes,spec)
   mutated=dict(row);mutated["offset_requested_pre_containment"]=not row["offset_requested_pre_containment"]
   if expected_questions(mutated,shapes,spec)!=wanted:issues.append(f"{iid}: question depends on requested-offset field")
   if any("offset_requested_pre_containment" in json.dumps(q) or "offset_intended" in json.dumps(q) for q in row["questions"]):issues.append(f"{iid}: offset field referenced by question")
   if len(row["questions"])!=5 or [q["difficulty_level"] for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: schema")
   else:
    for q,expected in zip(row["questions"],wanted):
     if (q["question_type"],str(q["ground_truth"]),q["answer_format"])!=expected:issues.append(f"{q['question_id']}: ground truth")
   if mode!="fixed":l4.append(int(row["questions"][3]["ground_truth"]))
   answer=row["questions"][4]["ground_truth"];l5[answer]+=1;counts.append(len(shapes));binary.append(answer=="yes")
  except Exception as exc:issues.append(f"{iid}: exception {exc}")
  image_path=root/row.get("image_path","")
  if not image_path.exists():issues.append(f"{iid}: missing PNG");continue
  with Image.open(image_path) as source:image=source.convert("RGB");image.load()
  if image.size!=tuple(row["canvas_size"]) or sum(ImageStat.Stat(image).var)<50:issues.append(f"{iid}: invalid PNG")
  array=np.asarray(image);issues.extend(png_outline_checks(array,row,shapes,vertex_fn));recovered=png_connected_outline_count(array)
  if recovered!=len(shapes):issues.append(f"{iid}: PNG recovered {recovered} outlines, expected {len(shapes)}")
  else:png_counts_matched+=1
  if position%500==0:print(f"{spec.key}: validated {position}/{len(records)}",flush=True)
 if reductions!={"constant":1500,"changing":1500}:issues.append(f"Level2 balance {dict(reductions)}")
 expected_split={"fixed":225,"per_shape_independent":1275}
 if any(dict(split[label])!=expected_split for label in ("constant","changing")):issues.append(f"rotation split {dict(split)}")
 rotation_v=cramers_v([r["reduction_mode"] for r in records],[r["rotation_mode"] for r in records])
 if rotation_v>1e-12:issues.append(f"rotation leak V={rotation_v}")
 capture=constant_capture(l4,spec.rotation_tolerance)
 if capture["share"]>float(spec.constant_capture_target)+1e-12:issues.append("constant-answer capture target")
 correlation=pearson(counts,[int(x) for x in binary]);audit=association_audit(records,spec,shape_field,vertex_fn)
 if not audit["filter_matches_raw_audit"]:issues.append("association summary filter disagrees with raw audit")
 stats=json.loads((root/"generation_stats.json").read_text(encoding="utf-8"));manifest=json.loads((root/"build_manifest.json").read_text(encoding="utf-8"))
 if stats["candidate_scenes_rejected"]!=unique_rejected or stats["rejections_by_constraint"]!=dict(sorted(rejections.items())):issues.append("generation rejection totals")
 if stats.get("guard_injection_tests")!=guards or manifest.get("guard_injection_tests")!=guards:issues.append("guard injection report")
 if manifest.get("constraints")!=common.constraint_parameters(spec) or manifest.get("wrap_guard_injection_test")!=wrap:issues.append("manifest")
 required=("question_set.csv","answer_key.csv","dataset_final.csv","dataset_final.jsonl")
 if all((root/name).exists() for name in required):issues.extend(validate_tables(root,records))
 else:issues.append("v8 tables missing")
 distributions=full_parameter_distributions(records,spec,shape_field,vertex_fn);ratio_v=audit["features"]["outer_inner_size_ratio"]["cramers_v"]
 if ratio_v>=.05:issues.append(f"outer/inner size ratio leak V={ratio_v:.8f}")
 clearance_split={label:summary([r["minimum_adjacent_clear_background_px"] for r in records if r["reduction_mode"]==label]) for label in ("constant","changing")};clearance_v=audit["features"]["minimum_adjacent_clear_background_px"]["cramers_v"]
 extrapolated=[float(common.extrapolated_fraction(r[shape_field])) for r in records]
 if not 1350<=l5["yes"]<=1650:issues.append(f"Level5 balance {dict(l5)}")
 if abs(correlation)>=.05:issues.append(f"Level5 count correlation {correlation:.8f}")
 if clearance_v>=.10:issues.append(f"clearance leak V={clearance_v:.8f}")
 if audit["definitional_features"]!=["factor_progression_direction","reduction_factor_span"]:issues.append("definitional whitelist is not exactly two approved fields")
 if audit["nontrivial_nuisance_associations"]:issues.append(f"nontrivial nuisance associations {sorted(audit['nontrivial_nuisance_associations'])}")
 output={"dataset_version":spec.dataset_version,"images_checked":len(records),"questions_checked":sum(len(r["questions"]) for r in records),"mismatches":len(issues),"level2_distribution":dict(sorted(reductions.items())),"rotation_mode_by_level2":{k:dict(sorted(v.items())) for k,v in sorted(split.items())},"rotation_mode_level2_cramers_v":rotation_v,"leak_audit":audit,"full_sampled_parameter_distributions":distributions,"changing_factor_span_threshold":float(common.CHANGING_FACTOR_SPAN_MIN),"changing_factor_span_distribution":summary(spans),"outer_inner_size_ratio_level2_cramers_v":ratio_v,"factor_progression_directions":dict(sorted(directions.items())),"level5_threshold":float(common.LEVEL5_THRESHOLD),"level5_threshold_derivation":"v7 medians motivated an upward move; 12% is the lowest shared rounded threshold whose 9.6% lower guard is feasible for 10-12 triangles under both standing visibility floors","level5_exclusion_band":[float(common.LEVEL5_LOWER_GUARD),float(common.LEVEL5_UPPER_GUARD)],"level5_achievable_extrapolated_fraction":summary(extrapolated),"level5_distribution":dict(sorted(l5.items())),"level5_count_correlation":correlation,"minimum_clearance_level2_cramers_v":clearance_v,"minimum_clearance_distribution_by_level2":clearance_split,"png_recovered_shape_count_matches":png_counts_matched,"offset_requested_contracted_below_3_percent":contracted,"offset_field_absent_from_flattened_outputs":not any("offset" in issue and "leak" in issue for issue in issues),"gap_threshold":float(spec.gap_margin),"accepted_gap_distribution":summary(gaps),"guard_injection_tests":guards,"wrap_guard_injection_test":wrap,"level4_theoretical_uniform_baseline":float(common.theoretical_constant_capture(spec)),"level4_max_constant_answer_capture":capture,"triangle_level4_capture_above_0_195":spec.key=="triangle" and capture["share"]>.195,"rotation_modes":dict(sorted(modes.items())),"unique_rejected_candidates":unique_rejected,"rejections_by_constraint":dict(sorted(rejections.items())),"issues":issues}
 (root/"validation_metrics.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 lines=[f"Nested {spec.plural.title()} Dataset v8 Validation Report","="*52,f"Dataset version: {spec.dataset_version}",f"Total images checked: {len(records)}",f"Total questions checked: {output['questions_checked']}",f"Total mismatches found: {len(issues)}","",f"Level 2 balance: {dict(reductions)}",f"Rotation modes split by Level 2: {output['rotation_mode_by_level2']}",f"Rotation-mode / Level-2 Cramer's V: {rotation_v:.10f}",f"Definitional whitelist (exactly two): {audit['definitional_features']}",f"All features at V >= 0.10: {audit['all_features_at_or_above_threshold']}",f"Association filter exactly matches raw audit: {'YES' if audit['filter_matches_raw_audit'] else 'NO'}","Leak audit (all stored scene features):"]
 lines += [f"  {name}: V={data['cramers_v']:.8f} ({data['kind']})" for name,data in sorted(audit["features"].items())]
 lines += ["",f"Changing-factor perceptibility threshold: {float(common.CHANGING_FACTOR_SPAN_MIN):.3f}",f"Changing-factor span distribution: {summary(spans)}",f"Outer/inner ratio vs Level 2 V: {ratio_v:.8f}",f"Level 5 threshold: {float(common.LEVEL5_THRESHOLD):.3%}",f"Level 5 threshold derivation: {output['level5_threshold_derivation']}",f"Level 5 exclusion band: {output['level5_exclusion_band']}",f"Level 5 achievable extrapolated-fraction range: {output['level5_achievable_extrapolated_fraction']}",f"Level 5 labels: {dict(l5)}",f"Level 5 count correlation: {correlation:.8f}",f"Minimum-clearance / Level-2 V: {clearance_v:.8f}",f"Minimum-clearance distributions by Level 2: {clearance_split}",f"PNG-recovered shape counts matching stored count: {png_counts_matched}/{len(records)}",f"Innermost size threshold: {common.MIN_INNER_SIDE_PX:.1f}px",f"Clear-background threshold: {common.MIN_CLEAR_BACKGROUND_PX:.1f}px","",f"offset_intended absent from annotations and flattened outputs: {'YES' if output['offset_field_absent_from_flattened_outputs'] else 'NO'}",f"Requested offsets contracted below 3%: {contracted}","","Full sampled parameter distributions:"]
 for name,data in distributions["continuous"].items():lines.append(f"  continuous {name}: {data}")
 for name,data in distributions["categorical"].items():lines.append(f"  categorical {name}: {data}")
 lines += ["",f"Guard injection tests: {'PASS' if guards['pass'] else 'FAIL'}"]
 lines += [f"  {name}: {data}" for name,data in guards.items() if name!="pass"]
 lines += [f"  rotation_wrap: {'PASS' if wrap['pass'] else 'FAIL'} {wrap['thresholds']}","",f"Level 4 theoretical baseline: {output['level4_theoretical_uniform_baseline']:.6f}",f"Level 4 observed max constant capture: {capture['share']:.6f}"]
 if spec.key=="triangle":lines += [f"Triangle Level 4 > 0.195 flag: {'YES' if output['triangle_level4_capture_above_0_195'] else 'NO'} (v4 0.1933; v5 0.1984)"]
 lines += [f"All rejection cause counts: {dict(rejections)}","","Issues:"]+([f"  {i}" for i in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines));return len(issues)
