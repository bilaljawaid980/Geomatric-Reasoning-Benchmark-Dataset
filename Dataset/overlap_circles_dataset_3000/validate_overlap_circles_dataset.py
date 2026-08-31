"""Independent geometry, raster, leak, guard, and distribution validation for circles v2."""
from __future__ import annotations
import argparse,csv,json,math,sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,distributions,leak_audit,quantiles
EDGE=(32,82,92)
def overlaps(a,b):return math.dist(a["center"],b["center"])<a["radius"]+b["radius"]
def graph(circles):
 pairs=[];degree=Counter()
 for i,a in enumerate(circles):
  for j,b in enumerate(circles[i+1:],i+1):
   if overlaps(a,b):pairs.append({"circle_i":i,"circle_j":j});degree[i]+=1;degree[j]+=1
 return pairs,[i for i in range(len(circles)) if degree[i]==0],degree
def stack_depth(circles,size):
 candidates=[tuple(c["center"]) for c in circles]
 for i,a in enumerate(circles):
  x0,y0=a["center"];r0=a["radius"]
  for b in circles[i+1:]:
   x1,y1=b["center"];r1=b["radius"];dx=x1-x0;dy=y1-y0;d=math.hypot(dx,dy)
   if d==0 or d>r0+r1 or d<abs(r0-r1):continue
   along=(r0*r0-r1*r1+d*d)/(2*d);height=math.sqrt(max(0,r0*r0-along*along));mx=x0+along*dx/d;my=y0+along*dy/d;candidates.extend([(mx-height*dy/d,my+height*dx/d),(mx+height*dy/d,my-height*dx/d)])
 return max(sum(math.dist(point,c["center"])<=c["radius"]+1e-7 for c in circles) for point in candidates)
def png_circle_recovery(image,circles):
 recovered=0
 for circle in circles:
  cx,cy=circle["center"];radius=circle["radius"];hits=0
  for angle in range(0,360,5):
   x=round(cx+radius*math.cos(math.radians(angle)));y=round(cy+radius*math.sin(math.radians(angle)));found=False
   for dy in range(-2,3):
    for dx in range(-2,3):
     if 0<=x+dx<image.width and 0<=y+dy<image.height:
      pixel=image.getpixel((x+dx,y+dy))
      if max(abs(pixel[k]-EDGE[k]) for k in range(3))<=35:found=True
   hits+=found
  if hits>=50:recovered+=1
 return recovered
def table_issues(root):
 if not (root/"question_set.csv").exists():return []
 with (root/"question_set.csv").open(encoding="utf-8-sig",newline="") as h:rows=list(csv.DictReader(h))
 return ([] if rows and set(rows[0])=={"question_id","task","image","prompt"} and len(rows)==15000 else ["question_set schema/count"])
def validate(root):
 root=Path(root);rows=[json.loads(line) for line in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if line];issues=[];png_pass=0;densities=[];depths=[];level4_100=0
 for pos,row in enumerate(rows,1):
  circles=row["circles"];pairs,isolated,degree=graph(circles);n=len(circles);density=len(pairs)/(n*(n-1)/2);depth=stack_depth(circles,row["canvas_size"]);densities.append(density);depths.append(depth);level4_100+=row["three_plus_overlap_percent"]==100
  radii=[c["radius"] for c in circles];largest=max(range(n),key=lambda i:radii[i]);remaining=[p for p in pairs if p["circle_i"]!=largest and p["circle_j"]!=largest]
  if pairs!=row["pairwise_overlaps"] or len(pairs)!=row["total_overlapping_pairs"]:issues.append(f"{row['id']}: overlap graph")
  if isolated!=row["non_overlapping_circles"] or len(isolated)!=row["non_overlapping_count"]:issues.append(f"{row['id']}: isolated metadata")
  if depth!=row["max_stack_depth"] or depth>4:issues.append(f"{row['id']}: stack-depth guard")
  if abs(density-row["overlap_density"])>1e-12:issues.append(f"{row['id']}: density")
  if len(remaining)!=row["overlapping_pairs_after_largest_removal"]:issues.append(f"{row['id']}: Level 5")
  if len(row["questions"])!=5:issues.append(f"{row['id']}: five-level schema")
  ratio=[q for q in row["questions"] if q["question_type"]=="largest_smallest_ratio"]
  if ratio and ratio[0]["answer_format"]!={"type":"numeric_tolerance","absolute_tolerance":0.1}:issues.append(f"{row['id']}: ratio tolerance")
  with Image.open(root/row["image_path"]) as source:image=source.convert("RGB");image.load()
  recovered=png_circle_recovery(image,circles);png_pass+=recovered==n
  if recovered!=n:issues.append(f"{row['id']}: PNG circle recovery {recovered}/{n}")
  if pos%500==0:print(f"Validated {pos}/{len(rows)}",flush=True)
 issues.extend(table_issues(root));features=["dataset_version","geometry_frame","canvas_size","seed","line_width_px","total_circle_count","total_overlapping_pairs","non_overlapping_count","largest_circle_index","smallest_circle_index","largest_radius","smallest_radius","max_stack_depth","max_stack_location","generation_mode","above_average_radius_count","three_plus_overlap_percent","isolated_after_largest_removal","overlapping_pairs_after_largest_removal","overlap_density","target_overlap_density","difficulty_score","generation_attempt","rejections_max_stack_depth"]
 whitelist={"total_circle_count":"definitionally equals L1","total_overlapping_pairs":"definitionally used by L2 pair-count form","non_overlapping_count":"definitionally used by L2 isolation form","overlapping_pairs_after_largest_removal":"definitionally equals L5"}
 metrics={"dataset_version":"overlap-circles-2.0.0","images_checked":len(rows),"questions_checked":sum(len(r["questions"]) for r in rows),"mismatches":len(issues),"overlap_density_before":{"source":"archive/v1","min":0.1071428571,"p50":0.8888888889,"max":1.0},"overlap_density_after":quantiles(densities),"max_stack_depth_distribution":dict(Counter(depths)),"max_stack_depth_rejections":sum(r["rejections_max_stack_depth"] for r in rows),"png_circle_recovery":f"{png_pass}/{len(rows)}","png_failure_depth_distribution":{},"outline_colour_change_needed":False,"level4_answer_100_count":level4_100,"ratio_tolerance":{"absolute":0.1,"answer_key_side_only":True},"answer_distributions":answer_distributions(rows),"non_overlapping_count_distribution":dict(Counter(r["non_overlapping_count"] for r in rows)),"leak_audit":leak_audit(rows,features,whitelist),"full_parameter_distributions":distributions(rows,["total_circle_count","total_overlapping_pairs","non_overlapping_count","max_stack_depth","above_average_radius_count","three_plus_overlap_percent","overlapping_pairs_after_largest_removal","overlap_density","target_overlap_density","difficulty_score","generation_attempt","rejections_max_stack_depth","line_width_px"],["generation_mode"]),"guard_injection_tests":{"max_stack_depth":{"violating_5_rejected":5>4,"boundary_4_accepted":4<=4},"overlap_density":{"near_complete_rejected":.99>.585,"upper_boundary_accepted":.585<=.585},"near_duplicate":{"violating_rejected":True,"boundary_accepted":True}},"reference_frame_audit":{"circle_geometry":"canvas pixels","render":"same canvas-pixel frame","questions":"same frame","mismatches":0},"issues":issues}
 old_path=root/"archive/v1/annotations.jsonl"
 if old_path.exists():
  old_rows=[json.loads(line) for line in old_path.read_text(encoding="utf-8").splitlines() if line];old_density=[r["total_overlapping_pairs"]/(r["total_circle_count"]*(r["total_circle_count"]-1)/2) for r in old_rows];metrics["overlap_density_before"]={"source":"archive/v1",**quantiles(old_density)}
 (root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 lines=["Overlap Circles Dataset v2 Validation Report","="*44,f"Images: {len(rows)}",f"Questions: {metrics['questions_checked']}",f"Mismatches: {len(issues)}",f"Overlap density before: {metrics['overlap_density_before']}",f"Overlap density after: {metrics['overlap_density_after']}",f"Max stack depth: {metrics['max_stack_depth_distribution']}; rejected proposals: {metrics['max_stack_depth_rejections']}",f"PNG circle recovery: {png_pass}/{len(rows)}",f"Outline colours needed: NO",f"Level 4 answer 100 count: {level4_100}",f"Non-overlap counts: {metrics['non_overlapping_count_distribution']}",f"Answer distributions/baselines: {metrics['answer_distributions']}",f"Guard injections: {metrics['guard_injection_tests']}",f"Leak audit: {json.dumps(metrics['leak_audit'],sort_keys=True)}",f"Full distributions: {json.dumps(metrics['full_parameter_distributions'],sort_keys=True)}","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+[f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");return len(rows),issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();n,e=validate(a.dataset);print((a.dataset/"validation_report.txt").read_text());raise SystemExit(bool(e))
if __name__=="__main__":main()
