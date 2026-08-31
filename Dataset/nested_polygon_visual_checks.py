"""Independent raster and geometry checks for the nested-polygon family."""
from __future__ import annotations
import csv,json,math
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image,ImageStat
import nested_polygon_common as common

BACKGROUND=np.asarray((253,250,244),dtype=np.float64)
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}

def summary(values):
 if not values:return {"count":0,"min":None,"p25":None,"p50":None,"p75":None,"p95":None,"max":None}
 array=np.asarray(values,dtype=float);return {"count":len(values),"min":float(np.min(array)),"p25":float(np.percentile(array,25)),"p50":float(np.percentile(array,50)),"p75":float(np.percentile(array,75)),"p95":float(np.percentile(array,95)),"max":float(np.max(array))}

def png_connected_outline_count(image,minimum_component_pixels=12):
 """Count separated rendered outlines using only the saved RGB raster."""
 distance=np.max(np.abs(image.astype(np.int16)-BACKGROUND.astype(np.int16)),axis=2);mask=distance>=18
 parent=[];area=[];previous=[]
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 def union(a,b):
  a=find(a);b=find(b)
  if a==b:return
  if area[a]<area[b]:a,b=b,a
  parent[b]=a;area[a]+=area[b]
 for row in mask:
  xs=np.flatnonzero(row);runs=[]
  if len(xs):
   cuts=np.flatnonzero(np.diff(xs)>1);starts=np.r_[0,cuts+1];ends=np.r_[cuts,len(xs)-1]
   for s,e in zip(starts,ends):
    rid=len(parent);parent.append(rid);area.append(int(xs[e]-xs[s]+1));runs.append((int(xs[s]),int(xs[e]),rid))
  pi=0
  for start,end,rid in runs:
   while pi<len(previous) and previous[pi][1]<start-1:pi+=1
   pj=pi
   while pj<len(previous) and previous[pj][0]<=end+1:union(rid,previous[pj][2]);pj+=1
  previous=runs
 roots={find(i) for i in range(len(parent))}
 return sum(area[root]>=minimum_component_pixels for root in roots)
def bbox_center(shape):
 vertices=np.asarray(shape["vertices"],dtype=float);return ((vertices[:,0].min()+vertices[:,0].max())/2,(vertices[:,1].min()+vertices[:,1].max())/2)
def segment_distances(points,a,b):
 vector=b-a;den=float(vector@vector)
 if not den:return np.linalg.norm(points-a,axis=1)
 projection=np.clip(((points-a)@vector)/den,0,1);return np.linalg.norm(points-(a+projection[:,None]*vector),axis=1)
def ink_centroid(image,shape,line_width):
 vertices=np.asarray(shape["vertices"],dtype=float);radius=max(2.25,1.35*line_width);x0=max(0,int(np.floor(vertices[:,0].min()-radius-1)));x1=min(image.shape[1],int(np.ceil(vertices[:,0].max()+radius+1)));y0=max(0,int(np.floor(vertices[:,1].min()-radius-1)));y1=min(image.shape[0],int(np.ceil(vertices[:,1].max()+radius+1)));crop=image[y0:y1,x0:x1].astype(float);dark=np.clip((BACKGROUND.mean()-crop.mean(axis=2))/BACKGROUND.mean(),0,1);ys,xs=np.nonzero(dark>.015)
 if not len(xs):return tuple(shape["center"])
 points=np.column_stack((xs+x0+.5,ys+y0+.5));dist=np.full(len(points),np.inf)
 for i in range(len(vertices)):dist=np.minimum(dist,segment_distances(points,vertices[i],vertices[(i+1)%len(vertices)]))
 keep=dist<=radius;weights=dark[ys[keep],xs[keep]]
 if not np.any(keep) or weights.sum()<=0:return tuple(shape["center"])
 center=(points[keep]*weights[:,None]).sum(axis=0)/weights.sum();return tuple(center)
def spread(centers,outer):return max(math.dist(centers[0],center) for center in centers[1:])/outer

def point_inside(point,polygon,tolerance=1e-7):
 px,py=point;signs=[]
 for i in range(len(polygon)):
  ax,ay=polygon[i];bx,by=polygon[(i+1)%len(polygon)];cross=(bx-ax)*(py-ay)-(by-ay)*(px-ax)
  if abs(cross)>tolerance:signs.append(cross>0)
 return not signs or all(value==signs[0] for value in signs)
def orientation_from_vertices(item,spec):
 vertices=item["vertices"];cx=sum(v[0] for v in vertices)/len(vertices);cy=sum(v[1] for v in vertices)/len(vertices);vx,vy=vertices[0]
 angle=math.degrees(math.atan2(vy-cy,vx-cx))+135 if spec.key=="square" else math.degrees(math.atan2(vx-cx,cy-vy))
 return angle%spec.modulus
def vertex_rotation(shapes,spec):
 delta=(orientation_from_vertices(shapes[-1],spec)-orientation_from_vertices(shapes[0],spec))%spec.modulus
 return 0.0 if delta<.03 or delta>spec.modulus-.03 else delta
def classify_rotation(shapes):
 differences=[shapes[i+1]["rotation_angle"]-shapes[i]["rotation_angle"] for i in range(len(shapes)-1)]
 if all(abs(value)<1e-7 for value in differences):return "fixed"
 return "uniform_whole_nest" if max(differences)-min(differences)<=.0003 else "per_shape_independent"
def hex_rgb(value):value=value.lstrip("#");return tuple(int(value[i:i+2],16) for i in (0,2,4))
def stroke_match(pixel,target,residual=14,minimum=.10):
 background=tuple(BACKGROUND.astype(int));direction=[target[i]-background[i] for i in range(3)];observed=[pixel[i]-background[i] for i in range(3)];den=sum(v*v for v in direction);opacity=sum(observed[i]*direction[i] for i in range(3))/den
 if not minimum<=opacity<=1.08:return False
 predicted=[background[i]+opacity*direction[i] for i in range(3)];return max(abs(pixel[i]-predicted[i]) for i in range(3))<=residual
def stroke_hit_array(image,point,target,radius=5):
 x0,y0=(round(v) for v in point);crop=image[max(0,y0-radius):min(image.shape[0],y0+radius+1),max(0,x0-radius):min(image.shape[1],x0+radius+1)].astype(float)
 if not crop.size:return False
 direction=np.asarray(target,dtype=float)-BACKGROUND;observed=crop-BACKGROUND;den=float(direction@direction);opacity=np.sum(observed*direction,axis=2)/den;predicted=BACKGROUND+opacity[:,:,None]*direction;residual=np.max(np.abs(crop-predicted),axis=2)
 return bool(np.any((opacity>=.10)&(opacity<=1.08)&(residual<=14)))
def png_outline_checks(image,row,shapes,vertex_fn):
 issues=[]
 for shape in shapes:
  vertices=vertex_fn(shape["center"],shape["side_length"],shape["rotation_angle"]);target=hex_rgb(shape["stroke_color"])
  for edge in range(len(vertices)):
   a,b=vertices[edge],vertices[(edge+1)%len(vertices)];hits=0
   for fraction in (.25,.5,.75):
    point=(a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1]));hits+=stroke_hit_array(image,point,target)
   if hits<2:issues.append(f"{row['id']}: PNG shape {shape['index']} edge {edge+1} mismatch")
 return issues

def expected_questions(row,shapes,spec):
 ratio=shapes[0]["side_length"]/shapes[-1]["side_length"];delta=Fraction(str(round(vertex_rotation(shapes,spec),4)));next_fraction=Fraction(str(shapes[-1]["side_length"]))*Fraction(str(row["size_reduction_factor"]))/Fraction(str(shapes[0]["side_length"]))
 return [(f"count_{spec.plural}",str(len(shapes)),"numeric"),("outline_color_pattern",common.color_pattern(shapes),"choice"),("outer_inner_side_ratio",f"{ratio:.1f}",common.RATIO_ANSWER_FORMAT),("cumulative_rotation",str(common.round_half_up(delta)),common.rotation_answer_format(spec)),(f"next_{spec.singular}_visually_distinguishable","yes" if next_fraction>Fraction(5,100) else "no","yes_no")]
def read_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))
def validate_tables(root,records):
 issues=[];expected=[]
 for row in records:
  for question in row["questions"]:expected.append((row,question))
 public=read_csv(root/"question_set_v3.csv");private=read_csv(root/"answer_key_v3.csv");final=read_csv(root/"dataset_final_v3.csv")
 if list(public[0])!=["dataset_version","question_id","task","image","prompt"]:issues.append("v3 public columns mismatch")
 if list(private[0])!=["dataset_version","question_id","task","image","prompt","groundtruth","answer_format"]:issues.append("v3 private columns mismatch")
 if not len(public)==len(private)==len(final)==len(expected):return issues+["v3 table row-count mismatch"]
 for i,((row,q),pub,priv,flat) in enumerate(zip(expected,public,private,final),1):
  want={"dataset_version":row["dataset_version"],"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"]}
  if any(pub.get(key)!=value for key,value in want.items()):issues.append(f"v3 public row {i} mismatch")
  if any(priv.get(key)!=value for key,value in want.items()) or priv["groundtruth"]!=str(q["ground_truth"]) or priv["answer_format"]!=q["answer_format"]:issues.append(f"v3 private row {i} mismatch")
  if any(token in pub["prompt"].lower() for token in ("graded within","tolerance","±")):issues.append(f"v3 tolerance leaked {q['question_id']}")
 return issues

def constant_capture(values,tolerance):
 best=max((sum(abs(value-answer)<=tolerance for value in values),answer) for answer in range(min(values),max(values)+1));return {"answer":best[1],"captured":best[0],"total":len(values),"share":best[0]/len(values)}

def validate_dataset(root,spec,shape_field,vertex_fn):
 root=Path(root);records=[json.loads(line) for line in (root/"annotations_v3.jsonl").read_text(encoding="utf-8").splitlines() if line];issues=[];modes=Counter();colors=Counter();rejections=Counter();unique_rejected=0;l4=[];l5=Counter();gap=[];metrics={label:defaultdict(list) for label in ("concentric","offset")};raw=defaultdict(list);normalized=defaultdict(list)
 for position,row in enumerate(records,1):
  iid=row["id"];shapes=row[shape_field];modes[row["rotation_mode"]]+=1;colors[row["questions"][1]["ground_truth"]]+=1;rejections.update(row["generation_rejections"]);unique_rejected+=row["rejected_candidates"];label="offset" if row["center_drift"] else "concentric"
  try:
   if row["dataset_version"]!=spec.dataset_version or "_v3_" not in iid:issues.append(f"{iid}: version mismatch")
   if row["rejected_candidates"]!=row["generation_attempt"]:issues.append(f"{iid}: unique rejected-candidate count mismatch")
   if row["seed"]!=spec.seed_namespace+row["source_index"]:issues.append(f"{iid}: seed namespace mismatch")
   if len(shapes)!=row[f"num_{spec.plural}"]:issues.append(f"{iid}: count mismatch")
   w,h=row["canvas_size"]
   for shape in shapes:
    computed=vertex_fn(shape["center"],shape["side_length"],shape["rotation_angle"])
    if any(math.dist(a,b)>.002 for a,b in zip(computed,shape["vertices"])):issues.append(f"{iid}: vertices mismatch {shape['index']}")
    if any(not(19.999<=x<=w-19.999 and 19.999<=y<=h-19.999) for x,y in computed):issues.append(f"{iid}: canvas margin failure")
   for i in range(len(shapes)-1):
    if not all(point_inside(vertex,vertex_fn(shapes[i]["center"],shapes[i]["side_length"],shapes[i]["rotation_angle"]),1e-4) for vertex in vertex_fn(shapes[i+1]["center"],shapes[i+1]["side_length"],shapes[i+1]["rotation_angle"])):issues.append(f"{iid}: nesting failure {i}")
   if classify_rotation(shapes)!=row["rotation_mode"]:issues.append(f"{iid}: mode mismatch")
   angle_delta=(Fraction(str(shapes[-1]["rotation_angle"]))-Fraction(str(shapes[0]["rotation_angle"])))%spec.modulus;vertex_delta=vertex_rotation(shapes,spec);error=abs(float(angle_delta)-vertex_delta);error=min(error,spec.modulus-error)
   if error>.03 or Fraction(row["cumulative_rotation_fraction"])!=angle_delta or angle_delta!=Fraction(row["target_cumulative_rotation_degrees"]):issues.append(f"{iid}: rotation derivation mismatch")
   if not common.rotation_is_margin_safe(angle_delta,row["rotation_mode"],spec):issues.append(f"{iid}: rotation margin")
   relative=common.centroid_spread_fraction(shapes)
   if row["center_drift"]!=(relative>=common.DRIFT_FLOOR):issues.append(f"{iid}: drift metadata mismatch")
   if label=="offset":
    separation=common.gap_separation(shapes,vertex_fn);gap.append(float(separation))
    if separation<spec.gap_margin:issues.append(f"{iid}: gap margin")
   if not common.level5_is_margin_safe(shapes,row["size_reduction_factor"]):issues.append(f"{iid}: Level 5 margin")
   wanted=expected_questions(row,shapes,spec)
   if len(row["questions"])!=5 or [q["difficulty_level"] for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: schema")
   else:
    for question,expected in zip(row["questions"],wanted):
     if (question["question_type"],str(question["ground_truth"]),question["answer_format"])!=expected:issues.append(f"{question['question_id']}: ground truth mismatch")
   l4.append(int(row["questions"][3]["ground_truth"])) if row["rotation_mode"]!="fixed" else None;l5[row["questions"][4]["ground_truth"]]+=1
   signed=shapes[-1]["rotation_angle"]-shapes[0]["rotation_angle"];raw[row["rotation_mode"]].append(signed);normalized[row["rotation_mode"]].append(float(angle_delta))
  except Exception as exc:issues.append(f"{iid}: exception {exc}")
  image_path=root/row["image_path"]
  if not image_path.exists():issues.append(f"{iid}: missing PNG");continue
  with Image.open(image_path) as source:image=source.convert("RGB");image.load()
  if image.size!=tuple(row["canvas_size"]) or sum(ImageStat.Stat(image).var)<50:issues.append(f"{iid}: invalid PNG")
  array=np.asarray(image);issues.extend(png_outline_checks(array,row,shapes,vertex_fn));ink=[ink_centroid(array,shape,row["line_width_px"]) for shape in shapes];bbox=[bbox_center(shape) for shape in shapes];metrics[label]["ink_centroid_spread_fraction"].append(spread(ink,shapes[0]["side_length"]));metrics[label]["bbox_center_spread_fraction"].append(spread(bbox,shapes[0]["side_length"]))
  if position%500==0:print(f"{spec.key}: validated {position}/{len(records)}",flush=True)
 if len(records)==3000:
  if modes["fixed"]!=450:issues.append(f"fixed count {modes['fixed']}")
  if colors!={"alternating":1500,"same color":1500}:issues.append(f"Level 2 distribution {dict(colors)}")
 capture=constant_capture(l4,spec.rotation_tolerance)
 if capture["share"]>float(spec.constant_capture_target)+1e-12:issues.append(f"constant capture {capture['share']:.6f} exceeds target")
 if all((root/name).exists() for name in ("question_set_v3.csv","answer_key_v3.csv","dataset_final_v3.csv")):issues.extend(validate_tables(root,records))
 else:issues.append("v3 flattened tables missing")
 manifest=json.loads((root/"build_manifest_v3.json").read_text(encoding="utf-8"));stats=json.loads((root/"generation_stats_v3.json").read_text(encoding="utf-8"))
 if manifest.get("dataset_version")!=spec.dataset_version or manifest.get("constraints")!=common.constraint_parameters(spec):issues.append("v3 manifest mismatch")
 if stats.get("candidate_scenes_rejected")!=unique_rejected or stats.get("rejections_by_constraint")!=dict(sorted(rejections.items())):issues.append("v3 generation rejection totals mismatch")
 metric_summary={label:{name:summary(values) for name,values in group.items()} for label,group in metrics.items()};separates=all(metric_summary["concentric"][name]["p95"]<float(common.DRIFT_FLOOR) for name in ("ink_centroid_spread_fraction","bbox_center_spread_fraction"));expected_separation=spec.key!="triangle"
 if separates!=expected_separation:issues.append(f"unexpected center-proxy separability {separates}")
 rotation_summary={mode:{"raw_pre_normalization":summary(raw[mode]),"post_normalization":summary(normalized[mode])} for mode in sorted(raw)}
 output={"dataset_version":spec.dataset_version,"images_checked":len(records),"questions_checked":sum(len(row["questions"]) for row in records),"mismatches":len(issues),"apparent_center_metrics":metric_summary,"center_proxy_separable_at_3_percent":separates,"center_alignment_used_as_question":False,"gap_relative_separation_accepted":summary(gap),"gap_relative_separation_all_candidates":stats["gap_separation_all_offset_candidates"],"final_gap_threshold":float(spec.gap_margin),"rotation_delta_distributions":rotation_summary,"wrap_rejections":rejections["rotation_wrap"],"level4_histogram":dict(sorted(Counter(l4).items())),"level4_theoretical_uniform_baseline":float(common.theoretical_constant_capture(spec)),"level4_max_constant_answer_capture":capture,"level4_target":float(spec.constant_capture_target),"seed_handling":f"independent deterministic namespace {spec.seed_namespace}","rotation_modes":dict(sorted(modes.items())),"level2_distribution":dict(sorted(colors.items())),"level5_distribution":dict(sorted(l5.items())),"rejections_by_constraint":dict(sorted(rejections.items())),"issues":issues}
 (root/"validation_metrics_v3.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 lines=[f"Nested {spec.plural.title()} Dataset v3 Validation Report","="*52,f"Dataset version: {spec.dataset_version}",f"Total images checked: {len(records)}",f"Total questions checked: {output['questions_checked']}",f"Total mismatches found: {len(issues)}","",f"Shared Level 2: {dict(colors)}","",f"Center-proxy separability at 3%: {'YES' if separates else 'NO — center alignment removed from questions'}"]
 for label in ("concentric","offset"):
  lines.append(f"  {label}:")
  for name,values in metric_summary[label].items():lines.append(f"    {name}: min={values['min']:.8f}, p50={values['p50']:.8f}, p95={values['p95']:.8f}, max={values['max']:.8f}")
 lines += ["",f"Gap threshold: {float(spec.gap_margin):.4f}",f"Accepted gap separation: {output['gap_relative_separation_accepted']}",f"All-candidate gap separation: {output['gap_relative_separation_all_candidates']}","",f"Level 4 theoretical uniform baseline: {output['level4_theoretical_uniform_baseline']:.6f}",f"Level 4 observed max constant capture: {capture['share']:.6f} at answer {capture['answer']}",f"Level 4 target: {float(spec.constant_capture_target):.6f}",f"Wrap rejections: {rejections['rotation_wrap']}","",f"Seed handling: independent namespace {spec.seed_namespace}",f"Rotation modes: {dict(modes)}",f"All rejection counts: {dict(rejections)}","","Issues:"]+([f"  {issue}" for issue in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report_v3.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines));return len(issues)
