"""Independently rebuild and validate all hex-grid graphs, questions, tables, and PNGs."""
from __future__ import annotations
import argparse,csv,json,math,sys
from collections import Counter,deque
from pathlib import Path
from PIL import Image,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,cramers_v,distributions,leak_audit
DIRECTIONS=((1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1));COLORS={"black":(36,42,46),"grey":(157,163,168),"home":(74,155,99),"start":(210,74,67)};BACKGROUND=(253,250,244)
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
def neighbors(c):return [(c[0]+dq,c[1]+dr) for dq,dr in DIRECTIONS]
def hex_distance(a,b):return (abs(a[0]-b[0])+abs(a[1]-b[1])+abs((a[0]+a[1])-(b[0]+b[1])))//2
def all_coords(radius):return {(q,r) for q in range(-radius,radius+1) for r in range(-radius,radius+1) if abs(q+r)<=radius}
def fresh_bfs(traversable,start,goal):
 if start not in traversable or goal not in traversable:return None,[],0
 queue=deque([start]);dist={start:0};count={start:1};parent={}
 while queue:
  current=queue.popleft()
  for nxt in sorted(neighbors(current)):
   if nxt not in traversable:continue
   candidate=dist[current]+1
   if nxt not in dist:dist[nxt]=candidate;count[nxt]=count[current];parent[nxt]=current;queue.append(nxt)
   elif dist[nxt]==candidate:count[nxt]+=count[current]
 if goal not in dist:return None,[],0
 path=[];node=goal
 while True:
  path.append(node)
  if node==start:break
  node=parent[node]
 return dist[goal],list(reversed(path)),count[goal]
def expected(row):
 tiles={tuple(t["coordinate"]):t["color"] for t in row["all_tiles"]};holes={c for c,color in tiles.items() if color=="grey"};traversable=set(tiles)-holes;start=tuple(row["start_coordinate"]);home=tuple(row["home_coordinate"]);length,path,count=fresh_bfs(traversable,start,home);l2=tuple(row["level2_neighbor_coordinate"]);blocked=tuple(row["level5_blocked_coordinate"]);new_length,_new_path,_new_count=fresh_bfs(traversable-{blocked},start,home);l5="no valid path exists" if new_length is None else (f"stay the same ({length} moves)" if new_length==length else f"increase to {new_length} moves")
 return [("hole_tile_count",str(len(holes)),"integer"),("adjacent_neighbor_status","hole" if l2 in holes else "walkable","hole or walkable"),("shortest_path_length",str(length),"integer in curly brackets"),("shortest_path_uniqueness","unique" if count==1 else f"multiple ({count})","unique or multiple (count)"),("blocked_tile_replanning",l5,"stay the same (N moves), increase to N moves, or no valid path exists")],(tiles,holes,traversable,start,home,length,path,count,blocked,new_length)
def pixel_geometry(canvas,radius):return min((canvas-72)/(math.sqrt(3)*(2*radius+1)),(canvas-112)/(3*radius+2)),(canvas/2,canvas/2-22)
def to_pixel(coord,size,center):return center[0]+size*math.sqrt(3)*(coord[0]+coord[1]/2),center[1]+size*1.5*coord[1]
def close(pixel,target,tol=14):return max(abs(pixel[i]-target[i]) for i in range(3))<=tol
def color_near(image,point,target,radius):
 x0,y0=(round(v) for v in point)
 return any(close(image.getpixel((x,y)),target) for y in range(max(0,y0-radius),min(image.height,y0+radius+1)) for x in range(max(0,x0-radius),min(image.width,x0+radius+1)))
def recover_tile_class(image,coord,size,center):
 point=to_pixel(coord,size,center);x0,y0=(round(v) for v in point);palette={"white":(255,253,249),"black":COLORS["black"],"grey":COLORS["grey"],"home":COLORS["home"]}
 samples=[]
 # Probe an annulus that stays inside the fill while avoiding centre labels,
 # the purple X, and the blue question mark/ring.
 for angle in range(0,360,30):
  dx=.52*math.cos(math.radians(angle));dy=.52*math.sin(math.radians(angle))
  x=round(x0+dx*size);y=round(y0+dy*size);samples.append(image.getpixel((x,y)))
 votes=Counter(min(palette,key=lambda name:sum((pixel[i]-palette[name][i])**2 for i in range(3))) for pixel in samples)
 return votes.most_common(1)[0][0]
def level5_invariant(traversable,start,home,blocked,length,count,outcome,new_length):
 after_length,_path,_count=fresh_bfs(traversable-{blocked},start,home)
 if outcome=="no_path":return after_length is None
 if outcome=="same":return after_length==length
 if outcome=="increase":
  start_length,_p,start_count=fresh_bfs(traversable,start,blocked);end_length,_p,end_count=fresh_bfs(traversable,blocked,home)
  on_every=(start_length is not None and end_length is not None and start_length+end_length==length and start_count*end_count==count)
  return on_every and after_length==new_length and new_length>length
 return False
def png_issues(image,row,tiles):
 issues=[];iid=row["id"];canvas=row["canvas_size"][0];size,center=pixel_geometry(canvas,row["grid_radius"])
 if image.size!=(canvas,canvas):issues.append(f"{iid}: PNG size")
 if sum(ImageStat.Stat(image).var)<100:issues.append(f"{iid}: blank PNG")
 if not close(image.getpixel((3,3)),BACKGROUND,5):issues.append(f"{iid}: background")
 recovered={coord:recover_tile_class(image,coord,size,center) for coord in tiles}
 for coord,color in tiles.items():
  if color in COLORS:
   target=COLORS[color];radius=max(4,round(size*.3))
   if not color_near(image,to_pixel(coord,size,center),target,radius):issues.append(f"{iid}: PNG {color} tile {coord}")
 if sum(value=="grey" for value in recovered.values())!=row["num_hole_tiles"]:issues.append(f"{iid}: PNG hole-count recovery")
 for required in ("white","black","grey","home"):
  expected=sum(color==required for color in tiles.values())
  if expected and sum(value==required for value in recovered.values())==0:issues.append(f"{iid}: PNG missing recoverable class {required}")
 if not color_near(image,to_pixel(tuple(row["start_coordinate"]),size,center),COLORS["start"],max(4,round(size*.3))):issues.append(f"{iid}: PNG START marker")
 return issues,recovered
def read_csv(path):
 with path.open("r",encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def table_issues(root,records):
 paths=[root/"question_set.csv",root/"answer_key.csv",root/"dataset_final.csv"]
 if not all(p.exists() for p in paths):return ["flattened tables missing"]
 public,private,final=map(read_csv,paths);pairs=[(r,q) for r in records for q in r["questions"]];issues=[]
 if not len(public)==len(private)==len(final)==len(pairs):return ["table row count"]
 if "groundtruth" in public[0] or "answer_format" in public[0]:issues.append("public leakage")
 for i,((row,q),pub,priv,flat) in enumerate(zip(pairs,public,private,final),1):
  base={"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"]}
  if any(pub.get(k)!=v for k,v in base.items()):issues.append(f"public row {i}")
  if any(priv.get(k)!=v for k,v in base.items()) or priv.get("groundtruth")!=str(q["ground_truth"]) or priv.get("answer_format")!=q["answer_format"]:issues.append(f"answer row {i}")
  if flat.get("groundtruth")!=str(q["ground_truth"]):issues.append(f"final row {i}")
 return issues
def validate(root):
 root=Path(root);records=[json.loads(x) for x in (root/"annotations.jsonl").read_text().splitlines() if x];issues=[];radii=Counter();l2_answers=Counter();l5_outcomes=Counter();densities=[];png_recovered=0;invariants=Counter()
 for position,row in enumerate(records,1):
  iid=row["id"];radii[row["grid_radius"]]+=1;densities.append(row["hole_density"])
  try:
   wants,data=expected(row);tiles,holes,traversable,start,home,length,path,count,blocked,new_length=data;l2_answers[wants[1][1]]+=1
   actual_outcome="no_path" if new_length is None else ("increase" if new_length>length else "same");l5_outcomes[actual_outcome]+=1
   if set(tiles)!=all_coords(row["grid_radius"]):issues.append(f"{iid}: grid coordinates")
   if Counter(tiles.values())["start"]!=1 or Counter(tiles.values())["home"]!=1 or tiles[start]!="start" or tiles[home]!="home":issues.append(f"{iid}: start/home colors")
   if len(holes)!=row["num_hole_tiles"] or abs(len(holes)/len(tiles)-row["hole_density"])>1e-6:issues.append(f"{iid}: hole metadata")
   if length is None:issues.append(f"{iid}: no original path")
   if length!=row["shortest_path_length"] or count!=row["num_alternate_shortest_paths"]:issues.append(f"{iid}: BFS ground truth")
   stored_path=[tuple(c) for c in row["shortest_path_sequence"]]
   if stored_path[0]!=start or stored_path[-1]!=home or len(stored_path)-1!=length or any(hex_distance(a,b)!=1 for a,b in zip(stored_path,stored_path[1:])) or any(c not in traversable for c in stored_path):issues.append(f"{iid}: stored path sequence")
   l2=tuple(row["level2_neighbor_coordinate"])
   if hex_distance(start,l2)!=1 or hex_distance(l2,home)!=min(hex_distance(n,home) for n in neighbors(start) if n in tiles):issues.append(f"{iid}: Level 2 direction")
   if blocked not in traversable-{start,home} or min(hex_distance(blocked,p) for p in path)>1:issues.append(f"{iid}: Level 5 tile scope")
   if row["level5_new_shortest_path_length"]!=new_length or row["level5_outcome"]!=actual_outcome:issues.append(f"{iid}: Level 5 metadata")
   invariant_ok=level5_invariant(traversable,start,home,blocked,length,count,actual_outcome,new_length);invariants[actual_outcome+":"+("pass" if invariant_ok else "fail")]+=1
   if not invariant_ok:issues.append(f"{iid}: Level 5 graph invariant")
   if len(row["questions"])!=5 or [q["difficulty_level"] for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: schema")
   else:
    for q,want in zip(row["questions"],wants):
     if (q["question_type"],str(q["ground_truth"]),q["answer_format"])!=want:issues.append(f"{q['question_id']}: answer")
  except Exception as exc:issues.append(f"{iid}: exception {exc}")
  image_path=root/row["image_path"]
  if not image_path.exists():issues.append(f"{iid}: missing PNG")
  else:
   with Image.open(image_path) as source:image=source.convert("RGB");image.load()
   png_findings,recovered=png_issues(image,row,tiles);issues.extend(png_findings)
   if not png_findings:png_recovered+=1
  if position%500==0:print(f"Validated {position}/{len(records)}",flush=True)
 if len(records)==3000:
  if radii!={3:1000,4:1000,5:1000}:issues.append(f"radius balance {dict(radii)}")
  if l2_answers!={"walkable":1500,"hole":1500}:issues.append(f"Level 2 balance {dict(l2_answers)}")
  if l5_outcomes!={"same":1000,"increase":1000,"no_path":1000}:issues.append(f"Level 5 balance {dict(l5_outcomes)}")
 if densities and (min(densities)<.1 or max(densities)>.3):issues.append("hole density range")
 issues.extend(table_issues(root,records));features=["dataset_version","coordinate_frame","canvas_size","seed","hole_density","grid_radius","shortest_path_length","difficulty_score","num_hole_tiles","num_alternate_shortest_paths","level2_neighbor_direction_is_toward_home","level5_outcome","level5_new_shortest_path_length","generation_attempt"]
 whitelist={"num_hole_tiles":"definitionally equals Level 1","shortest_path_length":"definitionally equals Level 3","num_alternate_shortest_paths":"definitionally equals Level 4","level5_outcome":"definitionally equals Level 5"}
 metrics={"images_checked":len(records),"questions_checked":sum(len(r["questions"]) for r in records),"mismatches":len(issues),"grid_radius_distribution":dict(radii),"level2_distribution":dict(l2_answers),"level5_distribution":dict(l5_outcomes),"level5_constant_answer_baseline":max(l5_outcomes.values())/len(records),"level5_invariants":dict(invariants),"png_full_tile_class_recovery":f"{png_recovered}/{len(records)}","hole_density":{"min":min(densities),"mean":sum(densities)/len(densities),"max":max(densities)},"answer_distributions":answer_distributions(records),"leak_audit":leak_audit(records,features,whitelist),"full_parameter_distributions":distributions(records,["hole_density","grid_radius","shortest_path_length","difficulty_score","num_hole_tiles","num_alternate_shortest_paths"],["level2_neighbor_direction_is_toward_home","level5_outcome"]),"guard_injection_tests":{"original_path":{"violating_no_path_rejected":fresh_bfs(set(),(0,0),(1,0))[0] is None,"boundary_adjacent_accepted":fresh_bfs({(0,0),(1,0)},(0,0),(1,0))[0]==1},"level5_cut_vertex":{"violating_non_cut_rejected":not level5_invariant({(0,0),(1,0),(0,1),(1,-1)},(0,0),(1,0),(0,1),1,1,"no_path",1),"boundary_cut_accepted":level5_invariant({(0,0),(1,0),(2,0)},(0,0),(2,0),(1,0),2,1,"no_path",None)}},"issues":issues};(root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 lines=["Hex Pathfinding Dataset v2 Validation Report","="*46,f"Total images checked: {len(records)}",f"Total questions checked: {metrics['questions_checked']}",f"Total mismatches found: {len(issues)}","",f"Grid radii: {dict(radii)}",f"Level 2 answers: {dict(l2_answers)}",f"Level 5 outcomes: {dict(l5_outcomes)}",f"Level 5 constant baseline: {metrics['level5_constant_answer_baseline']:.6f}",f"Level 5 invariant results: {dict(invariants)}",f"PNG full tile-class recovery: {png_recovered}/{len(records)}",f"Hole density: {metrics['hole_density']}","",f"Guard injection tests: {metrics['guard_injection_tests']}","",f"Leak audit: {json.dumps(metrics['leak_audit'],sort_keys=True)}","",f"Full parameter distributions: {json.dumps(metrics['full_parameter_distributions'],sort_keys=True)}","","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines));return len(issues)
def main():
 p=argparse.ArgumentParser();p.add_argument("root",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();raise SystemExit(1 if validate(a.root) else 0)
if __name__=="__main__":main()
