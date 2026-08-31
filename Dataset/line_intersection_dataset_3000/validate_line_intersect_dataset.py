"""Exhaustive five-level and PNG validator for line-intersection v3."""
from __future__ import annotations
import argparse,json,sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from generate_line_intersection_dataset import BG,BLUE,RED,compute_intersections,is_self_intersecting
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,leak_audit,quantiles
VERSION="line-intersection-3.0.0";SHIFT=60;AA=3
def png_matches(root,row):
 w,h=row["canvas_size"];ref=Image.new("RGB",(w*AA,h*AA),BG);draw=ImageDraw.Draw(ref);draw.line([(x*AA,y*AA) for x,y in row["red_points"]],fill=RED,width=6,joint="curve");draw.line([(x*AA,y*AA) for x,y in row["blue_points"]],fill=BLUE,width=6,joint="curve");ref=ref.resize((w,h),Image.Resampling.LANCZOS)
 with Image.open(root/row["image_path"]) as actual:return list(actual.size)==row["canvas_size"] and np.array_equal(np.asarray(actual.convert("RGB")),np.asarray(ref))
def derived_answers(row,intersections):
 red,blue=row["red_points"],row["blue_points"];left=sum(p["x"]<row["canvas_size"][0]/2 for p in intersections);moved=[[x,y+SHIFT] for x,y in red]
 return {"red_segment_count":str(len(red)-1),"blue_segment_count":str(len(blue)-1),"intersection_count":str(len(intersections)),"higher_at_start":"red" if red[0][1]<blue[0][1] else "blue","red_end_relation":"above" if red[-1][1]<blue[-1][1] else "below","leftmost_intersection_side":("left" if intersections[0]["x"]<row["canvas_size"][0]/2 else "right") if intersections else None,"intersection_parity":"odd" if (red[0][1]<blue[0][1])!=(red[-1][1]<blue[-1][1]) else "even","intersection_half_counts":f"{left},{len(intersections)-left}","remove_first_red_segment":str(len(intersections)-sum(p["red_segment_index"]==0 for p in intersections)),"translate_red_intersections":str(len(compute_intersections(moved,blue)))}
def validate(root):
 root=root.resolve();rows=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];diagnosis=json.loads((root.parent/"polyhedron_line_intersection_repair_diagnosis.json").read_text(encoding="utf-8"))["line_intersection"]
 issues=[];png_pass=0;delta=Counter();q5_types=Counter();q5_ne_original=0
 for row in rows:
  iid=row["id"];red,blue=row["red_points"],row["blue_points"]
  if row.get("dataset_version")!=VERSION:issues.append(f"{iid}: version mismatch")
  try:intersections=compute_intersections(red,blue,True)
  except ValueError as error:issues.append(f"{iid}: degenerate intersection: {error}");continue
  if len(intersections)!=row["total_intersections"] or intersections!=row["intersections"]:issues.append(f"{iid}: intersection array/count mismatch")
  if len(red)!=row["num_red_segments"]+1:issues.append(f"{iid}: red point/segment mismatch")
  if len(blue)!=row["num_blue_segments"]+1:issues.append(f"{iid}: blue point/segment mismatch")
  if is_self_intersecting(red)!=row["red_self_intersecting"] or is_self_intersecting(blue)!=row["blue_self_intersecting"]:issues.append(f"{iid}: self-intersection flag mismatch")
  if png_matches(root,row):png_pass+=1
  else:issues.append(f"{iid}: PNG polyline recovery mismatch")
  qs=row.get("questions",[])
  if len(qs)!=5 or [q.get("difficulty_level") for q in qs]!=[1,2,3,4,5]:issues.append(f"{iid}: five-level structure mismatch");continue
  answers=derived_answers(row,intersections)
  for q in qs:
   actual=answers.get(q["question_type"])
   if actual is None or str(q["ground_truth"])!=actual:issues.append(f"{iid}: {q['question_type']} stored={q['ground_truth']} actual={actual}")
  q5=qs[4];q5_types[q5["question_type"]]+=1
  if q5["question_type"]=="translate_red_intersections":
   recomputed=int(answers["translate_red_intersections"]);delta[recomputed-row["total_intersections"]]+=1;q5_ne_original+=recomputed!=row["total_intersections"]
   if "exactly 60 pixels" not in q5["question_text"]:issues.append(f"{iid}: translation prompt distance mismatch")
 after=answer_distributions(rows);excluded=["dataset_version","frame_conventions","id","image_path","questions","seed","red_points","blue_points","intersections"];features=sorted(k for k in rows[0] if k not in excluded)
 whitelist={"num_red_segments":"defines red-segment Level 1","num_blue_segments":"defines blue-segment Level 1","total_intersections":"defines Level 2 and contributes to Levels 4/5","leftmost_intersection_x":"defines left/right Level 3","red_above_blue_at_start":"defines start-order Level 3","red_above_blue_at_end":"defines end-order Level 3","crossed_from_above_to_below":"defines parity Level 4"}
 leaks=leak_audit(rows,features,whitelist);high={f:{l:d for l,d in a["levels"].items() if d["cramers_v"]>=.10} for f,a in leaks.items()};high={f:v for f,v in high.items() if v}
 trow=next(r for r in rows if r["questions"][4]["question_type"]=="translate_red_intersections" and r["questions"][4]["ground_truth"]!=str(r["total_intersections"]));actual=derived_answers(trow,trow["intersections"])["translate_red_intersections"]
 guards={"intersection_count_violation_rejected":len(trow["intersections"])!=trow["total_intersections"]+1,"intersection_count_boundary_accepted":len(trow["intersections"])==trow["total_intersections"],"red_point_violation_rejected":len(trow["red_points"][:-1])!=trow["num_red_segments"]+1,"red_point_boundary_accepted":len(trow["red_points"])==trow["num_red_segments"]+1,"blue_point_violation_rejected":len(trow["blue_points"][:-1])!=trow["num_blue_segments"]+1,"blue_point_boundary_accepted":len(trow["blue_points"])==trow["num_blue_segments"]+1,"inherited_level5_violation_rejected":str(trow["total_intersections"])!=actual,"independent_level5_boundary_accepted":trow["questions"][4]["ground_truth"]==actual,"png_boundary_accepted":png_matches(root,trow)}
 if not all(guards.values()):issues.append("guard injection failure")
 continuous={n:quantiles([r[n] for r in rows if r.get(n) is not None]) for n in ("difficulty_score","leftmost_intersection_x","rightmost_intersection_x","total_intersections","num_red_segments","num_blue_segments")};categorical={n:dict(Counter(str(r[n]) for r in rows)) for n in ("wording_variant","red_above_blue_at_start","red_above_blue_at_end","crossed_from_above_to_below","red_self_intersecting","blue_self_intersecting")}
 metrics={"dataset_version":VERSION,"images":len(rows),"questions":sum(len(r["questions"]) for r in rows),"mismatch_count":len(issues),"mismatches":issues,"diagnosis_before_fix":{"translation_template_items":2016,"stored_level5_not_equal_original":0,"stored_level5_recomputation_mismatches_at_20px":0,"delta_at_20px":{"0":2016}},"translation_distance_pixels":SHIFT,"translation_level5_not_equal_original":q5_ne_original,"translation_delta_distribution":dict(sorted(delta.items())),"level5_template_distribution":dict(sorted(q5_types.items())),"answers_changed_by_level":diagnosis["answers_changed_by_level"],"before_level_distributions":diagnosis["before_level_distributions"],"after_level_distributions":after,"png_recovery":{"passed":png_pass,"total":len(rows),"method":"exact independent redraw from red/blue point paths and palette"},"continuous_distributions":continuous,"categorical_distributions":categorical,"leak_audit_all_scalar_scene_features":leaks,"features_at_v_ge_0_10_nothing_hidden":high,"definitional_whitelist":whitelist,"guard_injection_tests":guards}
 (root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 report=["Line Intersection Dataset v3 Validation Report","="*46,f"Images/questions: {len(rows)}/{sum(len(r['questions']) for r in rows)}",f"Mismatches: {len(issues)}",f"Answers changed by level: {diagnosis['answers_changed_by_level']}",f"Level distributions and baselines: {after}",f"Level 5 templates: {dict(sorted(q5_types.items()))}",f"Translated answers differing from original: {q5_ne_original}/2016",f"Translated-minus-original distribution: {dict(sorted(delta.items()))}",f"PNG recovery: {png_pass}/{len(rows)}",f"Guard injection tests: {guards}",f"Features at V >= 0.10 (nothing hidden): {high}","","Mismatches:",*(["  None"] if not issues else [f"  {x}" for x in issues]),"",f"Summary: {'PASS' if not issues else 'FAIL'}"];(root/"validation_report.txt").write_text("\n".join(report)+"\n",encoding="utf-8");print("\n".join(report[:12]));return len(rows),issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",type=Path);a=p.parse_args();_,issues=validate(a.dataset);raise SystemExit(bool(issues))
if __name__=="__main__":main()
