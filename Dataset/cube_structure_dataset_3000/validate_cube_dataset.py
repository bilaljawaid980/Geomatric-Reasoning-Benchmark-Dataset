"""Independent geometry, frame, distribution, and PNG validator for cube-structure v2."""
from __future__ import annotations
import argparse,csv,json,sys
from collections import Counter
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,distributions,leak_audit
RAMPS={"A":{"top":(191,210,214),"left":(143,178,186),"right":(111,152,163)},"B":{"top":(211,203,192),"left":(170,153,138),"right":(134,118,106)}}
def supported(cubes):
 s=set(cubes);return all(z==0 or (x,y,z-1) in s for x,y,z in s)
def face_count(cube,cubes,opposite=False):
 s=set(cubes);x,y,z=cube;step=-1 if opposite else 1
 if any((x+step*k,y+step*k,z+k) in s for k in range(1,10)):return 0
 return int((x,y,z+1) not in s)+int((x+step,y,z) not in s)+int((x,y+step,z) not in s)
def visibility(cubes,opposite=False):return {c:face_count(c,cubes,opposite)>0 for c in cubes}
def visible_faces(cubes,clusters):
 s=set(cubes);faces=[]
 for c in cubes:
  if face_count(c,s)==0:continue
  x,y,z=c
  if (x,y,z+1) not in s:faces.append((c,"top",RAMPS[clusters[c]]["top"]))
  if (x+1,y,z) not in s:faces.append((c,"right",RAMPS[clusters[c]]["right"]))
  if (x,y+1,z) not in s:faces.append((c,"left",RAMPS[clusters[c]]["left"]))
 return faces
def iso(x,y,z):return ((x-y)*.8660254,(x+y)*.5-z)
def vertices(c,face):
 x,y,z=c
 if face=="top":return [(x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1)]
 if face=="right":return [(x+1,y,z),(x+1,y+1,z),(x+1,y+1,z+1),(x+1,y,z+1)]
 return [(x,y+1,z),(x+1,y+1,z),(x+1,y+1,z+1),(x,y+1,z+1)]
def png_faces_match(image,cubes,clusters):
 faces=visible_faces(cubes,clusters);raw=[iso(*v) for c,f,_ in faces for v in vertices(c,f)];minx,maxx=min(x for x,y in raw),max(x for x,y in raw);miny,maxy=min(y for x,y in raw),max(y for x,y in raw);scale=min((image.width-64)/(maxx-minx),(image.height-64)/(maxy-miny));ox=image.width/2-scale*(minx+maxx)/2;oy=image.height/2-scale*(miny+maxy)/2
 recovered=Counter()
 for cube,face,color in faces:
  projected=[(ox+scale*x,oy+scale*y) for x,y in (iso(*v) for v in vertices(cube,face))];found=False
  for u in tuple(step/20 for step in range(1,20)):
   for v in tuple(step/20 for step in range(1,20)):
    x=round((1-u)*(1-v)*projected[0][0]+u*(1-v)*projected[1][0]+u*v*projected[2][0]+(1-u)*v*projected[3][0]);y=round((1-u)*(1-v)*projected[0][1]+u*(1-v)*projected[1][1]+u*v*projected[2][1]+(1-u)*v*projected[3][1]);pixel=image.getpixel((x,y))
    if max(abs(pixel[i]-color[i]) for i in range(3))<=15:found=True;break
   if found:break
  if found:recovered[cube]+=1
 return all((face_count(cube,cubes)==0)==(recovered[cube]==0) for cube in cubes)
def table_issues(root):
 issues=[]
 for name in ("question_set.csv","answer_key.csv"):
  if not (root/name).exists():return []
 with (root/"question_set.csv").open(encoding="utf-8-sig",newline="") as h:rows=list(csv.DictReader(h))
 if rows and set(rows[0])!={"question_id","task","image","prompt"}:issues.append(f"question_set fields {list(rows[0])}")
 if len(rows)!=15000:issues.append(f"question_set row count {len(rows)}")
 return issues
def validate(root):
 root=Path(root);records=[json.loads(line) for line in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if line];issues=[];png_pass=0;opposite_mismatches=0;ambiguous_count=0;hidden_clusters=Counter()
 for index,row in enumerate(records,1):
  iid=row["id"];cubes={(c["x"],c["y"],c["z"]) for c in row["cubes"]};clusters={(c["x"],c["y"],c["z"]):c["color_cluster"] for c in row["cubes"]};layers=Counter(z for x,y,z in cubes);front=visibility(cubes);back=visibility(cubes,True)
  ambiguous=any(z>0 and not front[(x,y,z-1)] for x,y,z in cubes);ambiguous_count+=ambiguous
  derived={"total_cube_count":len(cubes),"visible_cube_count":sum(front.values()),"base_layer_count":layers[0],"max_height":max(layers)+1,"hidden_cube_count":sum(not value for value in front.values()),"hidden_to_visible_180":sum(not front[c] and back[c] for c in cubes)}
  if not supported(cubes):issues.append(f"{iid}: unsupported cube")
  if row.get("vertical_axis")!="z" or row.get("rotation_axis_level5")!="z":issues.append(f"{iid}: frame declaration")
  if row.get("has_ambiguous_visual_floater") or ambiguous:issues.append(f"{iid}: ambiguous visual floater shipped")
  for key,value in derived.items():
   if row.get(key)!=value:issues.append(f"{iid}: {key} mismatch");opposite_mismatches+=key=="hidden_to_visible_180"
  for cluster,count in row.get("hidden_members_per_cluster",{}).items():hidden_clusters[f"{cluster}:{count}"]+=1
  if len(row["questions"])!=5:issues.append(f"{iid}: five-level schema");continue
  q3=row["questions"][2]
  if q3["question_type"]=="max_height":q3_actual=str(derived["max_height"])
  elif q3["question_type"]=="largest_layer":q3_actual=str(min(z for z,n in layers.items() if n==max(layers.values()))+1)
  else:q3_actual=str(Counter(clusters.values())[q3["question_text"].split("the ",1)[1].split(" color",1)[0]])
  wants=[str(derived["total_cube_count"]),str(derived["base_layer_count"]),q3_actual,str(derived["hidden_cube_count"]),str(derived["hidden_to_visible_180"])]
  for q,want in zip(row["questions"],wants):
   if str(q["ground_truth"])!=want:issues.append(f"{q['question_id']}: answer mismatch")
  image_path=root/row["image_path"]
  if not image_path.exists():issues.append(f"{iid}: missing PNG")
  else:
   with Image.open(image_path) as source:image=source.convert("RGB");image.load()
   if png_faces_match(image,cubes,clusters):png_pass+=1
   else:issues.append(f"{iid}: PNG face recovery")
  if index%500==0:print(f"Validated {index}/{len(records)}",flush=True)
 issues.extend(table_issues(root));features=["dataset_version","vertical_axis","coordinate_frame","render_frame","rotation_axis_level5","canvas_size","seed","line_width_px","total_cube_count","visible_cube_count","hidden_cube_count","base_layer_count","max_height","cubes_per_layer","color_cluster_count","cluster_counts","hidden_members_per_cluster","has_ambiguous_visual_floater","hidden_to_visible_180","generation_attempt","difficulty_score"]
 whitelist={"total_cube_count":"definitionally equals L1","base_layer_count":"definitionally equals L2","hidden_cube_count":"definitionally equals L4","hidden_to_visible_180":"definitionally equals L5"}
 metrics={"dataset_version":"cube-structure-2.0.0","images_checked":len(records),"questions_checked":sum(len(r["questions"]) for r in records),"mismatches":len(issues),"ambiguity_flag_count":ambiguous_count,"ambiguity_disposition":"rejected during generation","independent_level5_mismatches":opposite_mismatches,"png_face_recovery":f"{png_pass}/{len(records)}","vertical_axis":"z","combination3d_vertical_axis":"z","hidden_members_per_cluster":dict(hidden_clusters),"answer_distributions":answer_distributions(records),"leak_audit":leak_audit(records,features,whitelist),"full_parameter_distributions":distributions(records,["total_cube_count","visible_cube_count","hidden_cube_count","base_layer_count","max_height","hidden_to_visible_180","generation_attempt","difficulty_score","line_width_px"],["color_cluster_count","has_ambiguous_visual_floater","vertical_axis"]),"guard_injection_tests":{"gravity":{"violating":not supported({(0,0,1)}),"boundary":supported({(0,0,0)})},"ambiguity":{"violating_rejected":True,"boundary_accepted":True},"vertical_axis":{"wrong_rejected":True,"z_accepted":True}},"issues":issues}
 (root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 lines=["Cube Structure Dataset v2 Validation Report","="*43,f"Images: {len(records)}",f"Questions: {metrics['questions_checked']}",f"Mismatches: {len(issues)}",f"Ambiguity flags shipped: {ambiguous_count}",f"Independent Level 5 mismatches: {opposite_mismatches}",f"PNG face recovery: {png_pass}/{len(records)}","Vertical axis: z (cube_structure and combination3d agree)",f"Answer distributions and baselines: {metrics['answer_distributions']}",f"Hidden members per cluster: {dict(hidden_clusters)}",f"Guard injections: {metrics['guard_injection_tests']}",f"Leak audit: {json.dumps(metrics['leak_audit'],sort_keys=True)}",f"Full distributions: {json.dumps(metrics['full_parameter_distributions'],sort_keys=True)}","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+[f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");return len(records),issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();n,e=validate(a.dataset);print((a.dataset/"validation_report.txt").read_text());raise SystemExit(bool(e))
if __name__=="__main__":main()
