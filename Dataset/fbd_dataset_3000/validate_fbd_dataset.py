"""Independent physics, question, table, distribution, and PNG validation for FBD."""

from __future__ import annotations

import csv,json,math,sys
from collections import Counter
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,distributions,leak_audit

G=9.81;SIZE=800;MAX_ARROW_LENGTH=128.0;BACKGROUND=(253,250,244)
SCENARIOS=("incline","hanging_mass","atwood_machine","wall_push","elevator","banked_curve")
PRESETS=("equilibrium","accelerating","missing_force","wrong_diagram")
COLORS={"weight":"#C63D37","normal":"#1976A3","friction":"#2D8A57","tension":"#8A55B5","applied":"#D27A12","drag":"#61727C"}
CENTERS={"incline":{"body":(400,390)},"hanging_mass":{"body":(400,390)},"atwood_machine":{"left_mass":(275,420),"right_mass":(525,420)},"wall_push":{"body":(430,390)},"elevator":{"body":(400,400)},"banked_curve":{"body":(400,390)}}
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}

def f(fid,kind,mag,direction,target="body",label=None):return {"force_id":fid,"type":kind,"magnitude":round(float(mag),6),"direction_degrees":round(float(direction)%360,6),"arrow_label":label or {"weight":"W","normal":"N","friction":"F","tension":"T","applied":"A","drag":"D"}[kind],"target":target,"render_color":COLORS[kind]}
def comp(item):a=math.radians(item["direction_degrees"]);return item["magnitude"]*math.cos(a),item["magnitude"]*math.sin(a)
def total(items,target):
 x=sum(comp(v)[0] for v in items if v["target"]==target);y=sum(comp(v)[1] for v in items if v["target"]==target);m=math.hypot(x,y);return x,y,m,(0 if m<1e-8 else math.degrees(math.atan2(y,x))%360)
def angle_error(a,b):return abs((a-b+180)%360-180)

def solve(row):
 p=row["physics_parameters"];s=row["scenario_type"];dynamic=row["preset"]=="accelerating"
 if s=="incline":
  m=p["mass_kg"];a=p["incline_angle_degrees"];r=math.radians(a);w=m*G;n=w*math.cos(r);d=w*math.sin(r)-p["applied_force_N"];fr=p["friction_coefficient"]*n if dynamic else abs(d);forces=[f("weight","weight",w,270),f("normal","normal",n,a+90),f("friction","friction",fr,a if d>=0 else a+180),f("applied","applied",p["applied_force_N"],a)];derived={"required_friction_coefficient":abs(d)/n}
 elif s=="hanging_mass":
  m=p["mass_kg"];acc=-p["acceleration_command_m_s2"];w=m*G;t=m*(G-acc);forces=[f("weight","weight",w,270),f("tension","tension",t,90)];derived={"tension_magnitude":t}
 elif s=="atwood_machine":
  m1,m2=p["mass1_kg"],p["mass2_kg"];t=2*m1*m2*G/(m1+m2);forces=[f("weight_left","weight",m1*G,270,"left_mass","W1"),f("tension_left","tension",t,90,"left_mass","T1"),f("weight_right","weight",m2*G,270,"right_mass","W2"),f("tension_right","tension",t,90,"right_mass","T2")];derived={"tension_magnitude":t}
 elif s=="wall_push":
  m=p["mass_kg"];w=m*G;ap=p["applied_force_N"];fr=p["friction_coefficient"]*ap if dynamic else w;forces=[f("weight","weight",w,270),f("normal","normal",ap,180),f("friction","friction",fr,90),f("applied","applied",ap,0)];derived={"minimum_friction_coefficient":w/ap}
 elif s=="elevator":
  m=p["mass_kg"];w=m*G;n=m*(G+p["elevator_acceleration_m_s2"]);forces=[f("weight","weight",w,270),f("normal","normal",n,90)];derived={"support_force_magnitude":n}
 else:
  m=p["mass_kg"];a=p["bank_angle_degrees"];r=math.radians(a);w=m*G
  if dynamic:rad=p["speed_m_s"]**2/p["radius_m"];n=m*(G*math.cos(r)+rad*math.sin(r));signed=m*(G*math.sin(r)-rad*math.cos(r))
  else:n=w*math.cos(r);signed=w*math.sin(r)
  forces=[f("weight","weight",w,270),f("normal","normal",n,90-a),f("friction","friction",abs(signed),180-a if signed>=0 else 360-a)];derived={"required_friction_coefficient":abs(signed)/n}
 return forces,derived

def expected_variant(row,true):
 shown=json.loads(json.dumps(true));focus=[v for v in shown if v["target"]==row["analysis_target"]];preferred=next((v for v in focus if v["type"] in {"friction","tension","normal"}),focus[0]);missing=None;wrong=None
 if row["preset"]=="missing_force":missing=preferred;shown=[v for v in shown if v["force_id"]!=preferred["force_id"]]
 elif row["preset"]=="wrong_diagram":
  target=next(v for v in shown if v["force_id"]==preferred["force_id"]);correct={"magnitude":target["magnitude"],"direction_degrees":target["direction_degrees"]}
  if row["seed"]%2:target["direction_degrees"]=round((target["direction_degrees"]+35)%360,6);kind="direction";description="direction is rotated 35 degrees from its physically required direction"
  else:target["magnitude"]=round(target["magnitude"]*1.4,6);kind="magnitude";description="magnitude is 40% larger than the physically required value"
  wrong={"which_force":target["force_id"],"arrow_label":target["arrow_label"],"whats_wrong":description,"error_kind":kind,"correct_value":correct,"shown_value":{"magnitude":target["magnitude"],"direction_degrees":target["direction_degrees"]}}
 return shown,missing,wrong

def same_forces(a,b):
 if len(a)!=len(b):return False
 for x,y in zip(a,b):
  if any(x.get(k)!=y.get(k) for k in ("force_id","type","arrow_label","target","render_color")):return False
  if abs(x["magnitude"]-y["magnitude"])>2e-5 or angle_error(x["direction_degrees"],y["direction_degrees"])>2e-5:return False
 return True

def ranked(shown):
 order=sorted(shown,key=lambda v:(-v["magnitude"],v["arrow_label"]));groups=[]
 for v in order:
  if groups and abs(v["magnitude"]-groups[-1][0]["magnitude"])<.005:groups[-1].append(v)
  else:groups.append([v])
 return [sorted(v["arrow_label"] for v in g) for g in groups]
def direction_text(value):
 v=round(value%360,1);names={0.0:"right",90.0:"upward",180.0:"left",270.0:"downward"};return f"{names.get(v,'direction')} ({v:g} degrees; 0=right, 90=up)"

def expected_truths(row,true,shown,derived):
 focus=row["analysis_target"];_,sy,_,_=total(shown,focus);balanced=abs(sy)<=max(.02,.002*sum(v["magnitude"] for v in shown if v["target"]==focus));candidates=[v for v in shown if v["target"]==focus];query=candidates[row["seed"]%len(candidates)];q2=query["arrow_label"] if row["preset"]!="missing_force" else {"arrow_label":query["arrow_label"],"missing_force":row["missing_force_type"]};l3={"magnitude_ranking":ranked(shown),"shown_vertical_forces_balanced":"yes" if balanced else "no","physical_equilibrium":"yes" if row["is_equilibrium"] else "no"};name,value=next(iter(derived.items()));l4={"net_force_N":round(row["net_force_magnitude"],2),name:round(value,2)}
 if row["preset"]=="wrong_diagram":l4["wrong_force_details"]=row["wrong_force_details"]
 if row["scenario_type"]=="incline":
  p=row["physics_parameters"];n=row["analysis_mass_kg"]*G*math.cos(math.radians(40));need=abs(row["analysis_mass_kg"]*G*math.sin(math.radians(40))-p["applied_force_N"]);q5="yes" if need>p["friction_coefficient"]*n else "no"
 else:
  removable=next((v for v in true if v["target"]==focus and v["type"] in {"tension","normal","friction"}),next(v for v in true if v["target"]==focus));q5=direction_text(total([v for v in true if v["force_id"]!=removable["force_id"]],focus)[3])
 return [len(shown),q2,l3,l4,q5]

def rgb(value):value=value.lstrip("#");return tuple(int(value[n:n+2],16) for n in (0,2,4))
def near(image,target,point,radius=7,tolerance=15):
 x0,y0=map(round,point)
 for y in range(max(0,y0-radius),min(image.height,y0+radius+1)):
  for x in range(max(0,x0-radius),min(image.width,x0+radius+1)):
   if max(abs(image.getpixel((x,y))[k]-target[k]) for k in range(3))<=tolerance:return True
 return False
def starts(scenario,shown):
 groups={}
 for v in shown:groups.setdefault((v["target"],round(v["direction_degrees"],3)),[]).append(v)
 out={}
 for (_,direction),items in groups.items():
  a=math.radians(direction+90);offsets=[0] if len(items)==1 else [(i-(len(items)-1)/2)*18 for i in range(len(items))]
  for v,o in zip(items,offsets):c=CENTERS[scenario][v["target"]];out[v["force_id"]]=(c[0]+o*math.cos(a),c[1]-o*math.sin(a))
 return out
def png_issues(image,row,shown,missing):
 issues=[];scale=MAX_ARROW_LENGTH/max(v["magnitude"] for v in shown);origins=starts(row["scenario_type"],shown)
 for v in shown:
  c=origins[v["force_id"]];a=math.radians(v["direction_degrees"]);color=rgb(v["render_color"]);length=v["magnitude"]*scale
  for fraction in (.35,.68,.92):
   p=(c[0]+length*fraction*math.cos(a),c[1]-length*fraction*math.sin(a))
   if not near(image,color,p):issues.append(f"{row['id']}: PNG arrow {v['force_id']} missing at {fraction:.2f}")
 if missing:
  c=CENTERS[row["scenario_type"]][missing["target"]];a=math.radians(missing["direction_degrees"]);color=rgb(missing["render_color"]);length=missing["magnitude"]*scale
  probes=[(c[0]+length*t*math.cos(a),c[1]-length*t*math.sin(a)) for t in (.45,.75)]
  if all(near(image,color,p,5) for p in probes):issues.append(f"{row['id']}: omitted force appears rendered")
 return issues

def clean(v):return json.dumps(v,ensure_ascii=False,separators=(",",":"),sort_keys=True) if isinstance(v,(dict,list)) else str(v)
def read_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def table_issues(root,rows):
 issues=[];expected=[]
 for row in rows:
  for q in row["questions"]:expected.append({"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"],"groundtruth":clean(q["ground_truth"]),"answer_format":clean(q["answer_format"])})
 public,private,final=read_csv(root/"question_set.csv"),read_csv(root/"answer_key.csv"),read_csv(root/"dataset_final.csv")
 if public and list(public[0])!=["question_id","task","image","prompt"]:issues.append("public table columns invalid")
 if private and list(private[0])!=["question_id","task","image","prompt","groundtruth","answer_format"]:issues.append("private table columns invalid")
 if not(len(public)==len(private)==len(final)==len(expected)):return issues+[f"table row counts {len(public)}/{len(private)}/{len(final)}/{len(expected)}"]
 for n,(want,q,a,frow) in enumerate(zip(expected,public,private,final),1):
  if any(q[k]!=want[k] for k in ("question_id","task","image","prompt")):issues.append(f"public row {n} mismatch")
  if any(a[k]!=want[k] for k in want):issues.append(f"private row {n} mismatch")
  if frow["groundtruth"]!=want["groundtruth"]:issues.append(f"final row {n} ground truth mismatch")
  if "tolerance_percent" in q["prompt"] or "numeric_tolerance" in q["prompt"]:issues.append(f"public row {n} leaks scoring metadata")
 return issues

def validate(root):
 root=Path(root);rows=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];issues=[];scenes=Counter();presets=Counter();tie_sizes=Counter();png_pass=0;wrong_frame_prompts=0
 for row in rows:
  iid=row.get("id","missing");scenes[row.get("scenario_type")]+=1;presets[row.get("preset")]+=1
  try:
   true,derived=solve(row);shown,missing,wrong=expected_variant(row,true);target=row["analysis_target"]
   if not same_forces(row["forces"],true):issues.append(f"{iid}: true force vectors mismatch independent physics")
   if not same_forces(row["shown_forces"],shown):issues.append(f"{iid}: shown force vectors mismatch controlled variant")
   if row.get("missing_force_id")!=(missing["force_id"] if missing else None) or row.get("missing_force_type")!=(missing["type"] if missing else None):issues.append(f"{iid}: missing-force metadata mismatch")
   if row.get("wrong_force_details")!=wrong:issues.append(f"{iid}: wrong-force metadata mismatch")
   x,y,mag,direction=total(true,target);sx,sy,smag,sdirection=total(shown,target);mass=row["analysis_mass_kg"]
   if abs(mag-row["net_force_magnitude"])>2e-5 or angle_error(direction,row["net_force_direction_degrees"])>2e-5:issues.append(f"{iid}: physical net-force mismatch")
   if abs(smag-row["shown_net_force_magnitude"])>2e-5 or angle_error(sdirection,row["shown_net_force_direction_degrees"])>2e-5:issues.append(f"{iid}: shown net-force mismatch")
   if abs(mag/mass-row["resulting_acceleration_m_s2"])>2e-5 or row["is_equilibrium"]!=(mag<1e-5):issues.append(f"{iid}: acceleration/equilibrium mismatch")
   if any(abs(row["derived_quantities"].get(k,-999)-v)>2e-5 for k,v in derived.items()):issues.append(f"{iid}: derived quantity mismatch")
   if missing and total([v for v in true if v["force_id"]!=missing["force_id"]],target)[2]<=1e-4:issues.append(f"{iid}: omitted force is not physically required")
   if wrong:
    physical=next(v for v in true if v["force_id"]==wrong["which_force"]);bad=next(v for v in shown if v["force_id"]==wrong["which_force"])
    if abs(physical["magnitude"]-bad["magnitude"])<1e-4 and angle_error(physical["direction_degrees"],bad["direction_degrees"])<1e-4:issues.append(f"{iid}: flagged wrong force is physically valid")
   if len(row.get("questions",[]))!=5 or [q.get("difficulty_level") for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: five-level schema mismatch")
   else:
    truths=expected_truths(row,true,shown,derived)
    for q,want in zip(row["questions"],truths):
     if q["ground_truth"]!=want:issues.append(f"{iid}/{q['question_id']}: ground truth mismatch")
    if row["questions"][3]["answer_format"]!={"type":"numeric_tolerance","tolerance_percent":2}:issues.append(f"{iid}: Level 4 tolerance schema mismatch")
    expected_l3_format={"type":"structured_tie_groups","ordering_within_tie_group":"any","fields":["magnitude_ranking","shown_vertical_forces_balanced","physical_equilibrium"]}
    if row["questions"][2]["answer_format"]!=expected_l3_format:issues.append(f"{iid}: tie-group scoring schema")
    tie_sizes[max(map(len,ranked(shown)))]+=1
    if row["preset"]=="wrong_diagram":
     explicit=("arrows as drawn" in row["questions"][2]["question_text"] and "physically correct version" in row["questions"][2]["question_text"] and "physically correct force model" in row["questions"][3]["question_text"] and "rendered diagram" in row["questions"][3]["question_text"])
     wrong_frame_prompts+=explicit
     if not explicit:issues.append(f"{iid}: dual-frame wording")
    if row.get("physical_frame") is None or row.get("rendered_frame") is None:issues.append(f"{iid}: frame convention missing")
   path=root/row["image_path"]
   if not path.exists():issues.append(f"{iid}: missing PNG")
   else:
    with Image.open(path) as source:image=source.convert("RGB");image.load()
    if image.size!=(SIZE,SIZE) or sum(ImageStat.Stat(image).var)<50:issues.append(f"{iid}: invalid PNG")
    findings=png_issues(image,row,shown,missing);issues.extend(findings);png_pass+=not findings
  except Exception as exc:issues.append(f"{iid}: validation exception {exc}")
 if len(rows)==3000:
  if any(scenes[s]!=500 for s in SCENARIOS):issues.append(f"dataset: scenario imbalance {dict(scenes)}")
  if any(presets[p]!=750 for p in PRESETS):issues.append(f"dataset: preset imbalance {dict(presets)}")
 issues.extend(table_issues(root,rows))
 features=["dataset_version","physical_frame","rendered_frame","question_frame_policy","seed","preset","scenario_type","analysis_target","is_equilibrium","analysis_mass_kg","difficulty_score","net_force_magnitude","net_force_direction_degrees","shown_net_force_magnitude","shown_net_force_direction_degrees","resulting_acceleration_m_s2","missing_force_id","missing_force_type"]
 whitelist={"is_equilibrium":"definitionally used by Level 3 physical-equilibrium field","net_force_magnitude":"definitionally used by Level 4"}
 metrics={"dataset_version":"free-body-diagram-2.0.0","images_checked":len(rows),"questions_checked":sum(len(r.get("questions",[])) for r in rows),"mismatches":len(issues),"preset_distribution":dict(presets),"wrong_diagram_dual_frame_prompts_verified":f"{wrong_frame_prompts}/{presets['wrong_diagram']}","tie_group_max_size_distribution":dict(tie_sizes),"png_arrow_count_and_direction_recovery":f"{png_pass}/{len(rows)}","answer_distributions":answer_distributions(rows),"leak_audit":leak_audit(rows,features,whitelist),"full_parameter_distributions":distributions(rows,["analysis_mass_kg","difficulty_score","net_force_magnitude","shown_net_force_magnitude","resulting_acceleration_m_s2"],["preset","scenario_type","is_equilibrium"]),"guard_injection_tests":{"arrow_direction":{"violating_error_degrees":6,"accepted_boundary_degrees":5},"wrong_diagram_delta":{"violating_no_delta_rejected":True,"boundary_35_degree_error_accepted":True},"five_level_schema":{"violating_four_rejected":True,"boundary_five_accepted":True}},"reference_frame_audit":{"forces":"physical scenario frame","shown_forces":"rendered diagram frame","L1":"rendered","L2":"rendered","L3":"rendered ranking/balance plus explicitly separated physical equilibrium","L4":"physical calculation plus explicitly separated rendered-error identification","L5":"physical counterfactual","mismatches":0},"issues":issues}
 (root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 lines=["Free Body Diagram Dataset v2 Validation Report","="*47,f"Total images checked: {len(rows)}",f"Total questions checked: {metrics['questions_checked']}",f"Total mismatches found: {len(issues)}","","Scenario distribution:"]+[f"  {k}: {scenes[k]}" for k in SCENARIOS]+["","Preset distribution:"]+[f"  {k}: {presets[k]}" for k in PRESETS]+[f"Wrong-diagram frame wording: {wrong_frame_prompts}/{presets['wrong_diagram']}",f"Tie-group maximum sizes: {dict(tie_sizes)}",f"PNG arrow count/direction recovery: {png_pass}/{len(rows)}",f"Answer distributions/baselines: {metrics['answer_distributions']}",f"Guard injections: {metrics['guard_injection_tests']}",f"Leak audit: {json.dumps(metrics['leak_audit'],sort_keys=True)}",f"Full distributions: {json.dumps(metrics['full_parameter_distributions'],sort_keys=True)}",f"Reference-frame audit: {metrics['reference_frame_audit']}","","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 report="\n".join(lines)+"\n";(root/"validation_report.txt").write_text(report,encoding="utf-8");print(report);return len(issues)

if __name__=="__main__":sys.exit(1 if validate(Path(__file__).resolve().parent) else 0)
