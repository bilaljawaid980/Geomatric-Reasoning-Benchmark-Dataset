"""Independent geometry, question, table, and PNG validation for compass maps."""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter
from pathlib import Path
from PIL import Image,ImageStat
BACKGROUND=(253,250,244);LANDMARK=(182,66,60);PATH=(20,125,120)
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
def bearing(a,b):return math.degrees(math.atan2(b[0]-a[0],a[1]-b[1]))%360
def distance(a,b):return math.hypot(b[0]-a[0],b[1]-a[1])
def turn(first,second):
 cw=(second-first)%360
 if abs(cw-180)<1e-10:return 180.0,"either"
 return (cw,"clockwise") if cw<180 else (360-cw,"counterclockwise")
def project(origin,bearing_degrees,travel):
 angle=math.radians(bearing_degrees);return [origin[0]+travel*math.sin(angle),origin[1]-travel*math.cos(angle)]
def half_up(value):return int(math.floor(value+.5))
def rounded_bearing(value):return (half_up(value/10)*10)%360
def close(pixel,target,tol=12):return max(abs(pixel[i]-target[i]) for i in range(3))<=tol
def color_near(image,point,target,radius=6):
 x0,y0=(round(v) for v in point)
 return any(close(image.getpixel((x,y)),target) for y in range(max(0,y0-radius),min(image.height,y0+radius+1)) for x in range(max(0,x0-radius),min(image.width,x0+radius+1)))
def expected(row):
 lm=row["landmarks"];p2=row["level2_pair"];delta=lm[p2["Y"]][1]-lm[p2["X"]][1];relation="same latitude" if abs(delta)<=p2["same_latitude_tolerance_px"] else ("north" if delta<0 else "south")
 p3=row["level3_pair"];q3=f"{rounded_bearing(bearing(lm[p3['X']],lm[p3['Y']])):03d}"
 p4=row["level4_triple"];angle,direction=turn(bearing(lm[p4["X"]],lm[p4["Y"]]),bearing(lm[p4["X"]],lm[p4["Z"]]));q4=f"{half_up(angle)} degrees {direction}"
 p5=row["level5_projection"];origin=lm[p5["X"]];travel=distance(origin,lm[p5["Y"]]);endpoint=project(origin,p5["given_bearing"],travel);candidates=[label for label in lm if label!=p5["X"]];distances={label:distance(endpoint,lm[label]) for label in candidates};winner=min(candidates,key=lambda label:(distances[label],label));diff=abs((bearing(origin,lm[winner])-p5["given_bearing"]+180)%360-180);q5=f"{winner}; projected endpoint is closest to {winner} ({distances[winner]:.1f} map units away; bearing difference {diff:.1f} degrees)"
 return [("landmark_count",str(len(lm)),"integer"),("north_south_relation",relation,"north, south, or same latitude"),("rounded_compass_bearing",q3,"three-digit bearing in curly brackets"),("turn_angle_direction",q4,"integer degrees plus direction"),("counterfactual_bearing_projection",q5,"letter; endpoint distance and bearing difference")],(angle,direction),(endpoint,distances,winner,diff)
def cardinal_test():
 origin=[10,10];cases={"north":([10,0],0),"east":([20,10],90),"south":([10,20],180),"west":([0,10],270)};return {name:{"computed":bearing(origin,p),"expected":want,"pass":abs(bearing(origin,p)-want)<1e-12} for name,(p,want) in cases.items()}
def png_issues(image,row):
 issues=[];iid=row["id"]
 if image.size!=tuple(row["canvas_size"]):issues.append(f"{iid}: PNG size")
 if sum(ImageStat.Stat(image).var)<80:issues.append(f"{iid}: blank PNG")
 if not close(image.getpixel((3,3)),BACKGROUND,5):issues.append(f"{iid}: background")
 for label,point in row["landmarks"].items():
  if not color_near(image,point,LANDMARK,8):issues.append(f"{iid}: landmark {label} absent")
 if row["has_path"]:
  start=row["landmarks"][row["path_start"]];end=row["landmarks"][row["path_end"]];found=0
  for fraction in (.2,.3,.4,.5,.6,.7,.8):
   point=[start[0]+fraction*(end[0]-start[0]),start[1]+fraction*(end[1]-start[1])];found+=color_near(image,point,PATH,8)
  if found<2:issues.append(f"{iid}: dashed path absent/misaligned")
 return issues
def read_csv(path):
 with path.open("r",encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def table_issues(root,records):
 paths=[root/"question_set.csv",root/"answer_key.csv",root/"dataset_final.csv"]
 if not all(p.exists() for p in paths):return ["flattened tables missing"]
 public,private,final=map(read_csv,paths);pairs=[(row,q) for row in records for q in row["questions"]];issues=[]
 if not len(public)==len(private)==len(final)==len(pairs):return ["table row count"]
 if "groundtruth" in public[0] or "answer_format" in public[0]:issues.append("public leakage")
 for i,((row,q),pub,priv,flat) in enumerate(zip(pairs,public,private,final),1):
  base={"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"]}
  if any(pub.get(k)!=v for k,v in base.items()):issues.append(f"public row {i}")
  if any(priv.get(k)!=v for k,v in base.items()) or priv.get("groundtruth")!=str(q["ground_truth"]) or priv.get("answer_format")!=q["answer_format"]:issues.append(f"answer row {i}")
  if flat.get("groundtruth")!=str(q["ground_truth"]):issues.append(f"final row {i}")
 return issues
def validate(root):
 root=Path(root);records=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];issues=[];landmark_counts=Counter();paths=Counter();relations=Counter();cardinal=cardinal_test()
 if not all(value["pass"] for value in cardinal.values()):issues.append("cardinal convention test")
 for position,row in enumerate(records,1):
  iid=row["id"];lm=row["landmarks"];landmark_counts[len(lm)]+=1;paths[row["has_path"]]+=1
  try:
   for a in lm:
    for b in lm:
     if a==b:continue
     calculated=bearing(lm[a],lm[b]);stored=row["all_pairwise_bearings"][f"{a}-to-{b}"]
     if abs(calculated-stored)>1e-7:issues.append(f"{iid}: bearing {a}-{b}")
     reverse=bearing(lm[b],lm[a]);if_difference=abs(((reverse-calculated)%360)-180)
     if if_difference>1e-9:issues.append(f"{iid}: reverse bearing {a}-{b}")
   labels=sorted(lm)
   for i,a in enumerate(labels):
    for b in labels[i+1:]:
     if abs(distance(lm[a],lm[b])-row["all_pairwise_distances"][f"{a}-{b}"])>1e-7:issues.append(f"{iid}: distance {a}-{b}")
   if row["has_path"]:
    calculated=bearing(lm[row["path_start"]],lm[row["path_end"]])
    if abs(calculated-row["path_bearing"])>1e-7:issues.append(f"{iid}: path bearing")
   wants,turn_data,projection_data=expected(row);angle,direction=turn_data;endpoint,projected_distances,winner,bearing_diff=projection_data;p4=row["level4_triple"];p5=row["level5_projection"]
   if abs(angle-p4["turn_angle"])>1e-7 or direction!=p4["turn_direction"]:issues.append(f"{iid}: Level 4 derivation")
   if any(abs(a-b)>1e-7 for a,b in zip(endpoint,p5["projected_point"])) or winner!=p5["nearest_landmark"]:issues.append(f"{iid}: Level 5 endpoint/winner")
   if any(abs(projected_distances[k]-p5["candidate_distances"][k])>1e-7 for k in projected_distances) or abs(bearing_diff-p5["winner_bearing_difference"])>1e-7:issues.append(f"{iid}: Level 5 distances")
   ordered=sorted(projected_distances.values())
   if ordered[1]-ordered[0]<18-1e-7:issues.append(f"{iid}: Level 5 nearest margin")
   if len(row["questions"])!=5 or [q["difficulty_level"] for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: question schema")
   else:
    for q,want in zip(row["questions"],wants):
     if (q["question_type"],str(q["ground_truth"]),q["answer_format"])!=want:issues.append(f"{q['question_id']}: ground truth")
   relations[wants[1][1]]+=1
  except Exception as exc:issues.append(f"{iid}: exception {exc}")
  path=root/row["image_path"]
  if not path.exists():issues.append(f"{iid}: missing PNG")
  else:
   with Image.open(path) as source:image=source.convert("RGB");image.load()
   issues.extend(png_issues(image,row))
  if position%500==0:print(f"Validated {position}/{len(records)}",flush=True)
 if len(records)==3000:
  if landmark_counts!={3:1500,4:1500}:issues.append(f"landmark distribution {dict(landmark_counts)}")
  if paths!={True:1500,False:1500}:issues.append(f"path distribution {dict(paths)}")
 issues.extend(table_issues(root,records));metrics={"images_checked":len(records),"questions_checked":sum(len(r["questions"]) for r in records),"mismatches":len(issues),"cardinal_convention_tests":cardinal,"landmark_distribution":dict(landmark_counts),"path_distribution":{str(k).lower():v for k,v in paths.items()},"level2_relations":dict(relations),"issues":issues};(root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 lines=["Compass Bearing Dataset Validation Report","="*42,f"Total images checked: {len(records)}",f"Total questions checked: {metrics['questions_checked']}",f"Total mismatches found: {len(issues)}","",f"Cardinal convention tests: {cardinal}",f"Landmark counts: {dict(landmark_counts)}",f"Path presence: {dict(paths)}",f"Level 2 relations: {dict(relations)}","","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"];(root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines));return len(issues)
def main():
 p=argparse.ArgumentParser();p.add_argument("root",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();raise SystemExit(1 if validate(a.root) else 0)
if __name__=="__main__":main()
