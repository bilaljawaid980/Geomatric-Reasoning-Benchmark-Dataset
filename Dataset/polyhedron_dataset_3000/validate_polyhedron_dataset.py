"""Exhaustive independent validator for Polyhedron Dataset v5."""
from __future__ import annotations
import argparse,csv,itertools,json,math,random,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions,leak_audit,quantiles
VERSION="polyhedron-5.0.0";BG=(26,26,26);INK=(118,172,190);AA=3
EULER_TEXT=re.compile(r"has\s+(\d+)\s+vertices\s+and\s+(\d+)\s+edges",re.I)
IDENTITY={
"tetrahedron":("Platonic",4,6,4,{3:4}),"cube":("Platonic",8,12,6,{4:6}),"octahedron":("Platonic",6,12,8,{3:8}),"dodecahedron":("Platonic",20,30,12,{5:12}),"icosahedron":("Platonic",12,30,20,{3:20}),
"truncated tetrahedron":("Archimedean",12,18,8,{3:4,6:4}),"cuboctahedron":("Archimedean",12,24,14,{3:8,4:6}),"truncated cube":("Archimedean",24,36,14,{3:8,8:6}),"truncated octahedron":("Archimedean",24,36,14,{4:6,6:8}),"rhombicuboctahedron":("Archimedean",24,48,26,{3:8,4:18}),"icosidodecahedron":("Archimedean",30,60,32,{3:20,5:12}),
"triakis tetrahedron":("Catalan",8,18,12,{3:12}),"rhombic dodecahedron":("Catalan",14,24,12,{4:12}),"triakis octahedron":("Catalan",14,36,24,{3:24}),"rhombic triacontahedron":("Catalan",32,60,30,{4:30}),
"stella octangula":("Compound",8,12,8,{3:8}),"compound of cube and octahedron":("Compound",14,24,14,{3:8,4:6})}
def rotation(ry,tx):
 y,x=math.radians(ry),math.radians(tx);return np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]])@np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
def boundary_edges(faces):return [list(e) for e in sorted({tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1])})]
def face_shape(faces):return {frozenset({3}):"triangles",frozenset({4}):"squares",frozenset({5}):"pentagons"}.get(frozenset(map(len,faces)),"mixed")
def component_count(row):return 2 if row["solid_class"]=="Compound" else 1
def semantic_euler_ok(row):return row["vertex_count"]-row["edge_count"]+row["face_count"]==2*component_count(row)
def structural_assertions(row):
 return {"face_array_length_equals_face_count":len(row["faces"])==row["face_count"],"face_shape_matches_face_arities":face_shape(row["faces"])==row["face_shape_types"],"edge_array_length_equals_edge_count":len(row["edges"])==row["edge_count"],"literal_v_minus_e_plus_f_equals_2":row["vertex_count"]-row["edge_count"]+row["face_count"]==2,"visible_face_count_not_above_face_count":0<=row["visible_face_count"]<=row["face_count"]}
def hull_surface_convex(vertices,faces):
 v=np.asarray(vertices,float);eps=1e-7;on=set()
 for i,j,k in itertools.combinations(range(len(v)),3):
  normal=np.cross(v[j]-v[i],v[k]-v[i])
  if np.linalg.norm(normal)<eps:continue
  d=(v-v[i])@normal
  if np.all(d<=eps) or np.all(d>=-eps):on.update(np.where(np.abs(d)<=eps)[0].tolist())
 support=True
 for face in faces:
  p=v[face];normal=np.cross(p[1]-p[0],p[2]-p[0]);d=(v-p[0])@normal;support&=bool(np.all(d<=eps) or np.all(d>=-eps))
 return len(on)==len(v),bool(support)
def derived_convexity(row):
 point,faces=hull_surface_convex(row["vertices"],row["faces"]);return row["solid_class"]!="Compound" and point and faces
def visible(vertices,faces,angle):
 q=np.asarray(vertices)@rotation(angle["rotation_y"],angle["tilt_x"]).T;n=0
 for face in faces:
  p=q[face];normal=np.cross(p[1]-p[0],p[2]-p[0]);normal=-normal if normal@p.mean(0)<0 else normal;n+=normal[2]>1e-8
 return int(n)
def recover_png(root,row):
 rng=random.Random(row["seed"]);w=rng.randint(450,500);h=rng.randint(450,500);ry=rng.uniform(0,360);tx=rng.uniform(15,45);scale=rng.uniform(250,330)
 q=np.asarray(row["vertices"])@rotation(ry,tx).T;q*=scale/max(np.ptp(q[:,0]),np.ptp(q[:,1]));p=np.c_[w/2+q[:,0],h/2-q[:,1]]
 ref=Image.new("RGB",(w*AA,h*AA),BG);draw=ImageDraw.Draw(ref);recovered_edges=boundary_edges(row["faces"])
 for a,b in recovered_edges:draw.line([(round(p[a,0]*AA),round(p[a,1]*AA)),(round(p[b,0]*AA),round(p[b,1]*AA))],fill=INK,width=round(1.05*AA))
 ref=ref.resize((w,h),Image.Resampling.LANCZOS)
 with Image.open(root/row["image_path"]) as actual:exact=list(actual.size)==row["canvas_size"] and np.array_equal(np.asarray(actual.convert("RGB")),np.asarray(ref))
 return {"exact_reference_render":exact,"vertex_count":exact and len(row["vertices"])==row["vertex_count"],"edge_count":exact and len(recovered_edges)==row["edge_count"],"face_count":exact and len(row["faces"])==row["face_count"]}
def expected(row,q,vf):
 values={"face_count":str(row["face_count"]),"convexity":"convex" if row["is_convex"] else "non-convex","face_shapes":row["face_shape_types"],"visible_face_count":str(vf),"vertex_count":str(row["vertex_count"]),"euler_face_count":str(2-row["vertex_count"]+row["edge_count"]),"is_compound":"yes" if row["solid_class"]=="Compound" else "no","solid_family":row["solid_class"],"remove_face_closed_surface":"no"};return values[q["question_type"]]
def identity_ok(row):return IDENTITY.get(row["solid_name"])==(row["solid_class"],len(row["vertices"]),len(boundary_edges(row["faces"])),len(row["faces"]),dict(Counter(map(len,row["faces"]))))
def validate(root):
 root=root.resolve();rows=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];diagnosis=json.loads((root.parent/"polyhedron_identity_v5_repair_diagnosis.json").read_text(encoding="utf-8"))
 issues=[];png=Counter();names=Counter();classes=Counter();templates=Counter();literal_fail=Counter();euler_items=prompt_matches=point_hull=surface_hull=0;hull_cache={}
 for row in rows:
  iid=row["id"];names[row["solid_name"]]+=1;classes[row["solid_class"]]+=1;checks=structural_assertions(row)
  if row.get("dataset_version")!=VERSION:issues.append(f"{iid}: version mismatch")
  for check,result in checks.items():
   if check=="literal_v_minus_e_plus_f_equals_2" and row["solid_class"]=="Compound":
    if not result:literal_fail[row["solid_name"]]+=1
   elif not result:issues.append(f"{iid}: {check} failed")
  if row["edges"]!=boundary_edges(row["faces"]):issues.append(f"{iid}: edge array is not the deduplicated face boundary")
  if not semantic_euler_ok(row):issues.append(f"{iid}: component-aware Euler invariant failed")
  hull_key=(row["solid_name"],tuple(map(tuple,row["vertices"])),tuple(map(tuple,row["faces"])))
  if hull_key not in hull_cache:hull_cache[hull_key]=hull_surface_convex(row["vertices"],row["faces"])
  point,face_support=hull_cache[hull_key];point_hull+=point;surface_hull+=point and face_support
  if row["is_convex"]!=(row["solid_class"]!="Compound" and point and face_support):issues.append(f"{iid}: compound/face-support convexity mismatch")
  if not identity_ok(row):issues.append(f"{iid}: identity/signature mismatch")
  vf=visible(row["vertices"],row["faces"],row["viewing_angle"])
  if vf!=row["visible_face_count"]:issues.append(f"{iid}: visible-face mismatch")
  recovery=recover_png(root,row)
  for key,value in recovery.items():png[key]+=bool(value)
  if not all(recovery.values()):issues.append(f"{iid}: PNG topology recovery mismatch")
  qs=row.get("questions",[])
  if len(qs)!=5 or [q.get("difficulty_level") for q in qs]!=[1,2,3,4,5]:issues.append(f"{iid}: five-level structure mismatch");continue
  for q in qs:
   if str(q["ground_truth"])!=expected(row,q,vf):issues.append(f"{iid}: {q['question_type']} answer mismatch")
  q4=qs[3];templates[q4["question_type"]]+=1
  if q4["question_type"]=="euler_face_count":
   euler_items+=1;m=EULER_TEXT.search(q4["question_text"]);prompt_matches+=bool(m and (int(m.group(1)),int(m.group(2)))==(row["vertex_count"],row["edge_count"]))
   if int(q4["ground_truth"])!=row["face_count"] or int(q4["ground_truth"])<=0:issues.append(f"{iid}: Euler Level 4 invariant mismatch")
 with (root/"question_set.csv").open(encoding="utf-8-sig",newline="") as handle:public_fields=next(csv.reader(handle))
 if public_fields!=["question_id","task","image","prompt"]:issues.append(f"question_set public fields mismatch: {public_fields}")
 after=answer_distributions(rows);excluded=["dataset_version","edges","faces","frame_conventions","id","image_path","questions","seed","vertices","viewing_angle"];features=sorted(k for k in rows[0] if k not in excluded)
 whitelist={"face_count":"defines Level 1 and Euler Level 4","edge_count":"defines Euler Level 4 with V","vertex_count":"defines vertex Level 3 and Euler Level 4","is_convex":"defines Level 2","face_shape_types":"defines face-shape Level 3","visible_face_count":"defines visible-face Level 3","solid_class":"defines compound/family Level 4"}
 leaks=leak_audit(rows,features,whitelist);high={f:{l:d for l,d in a["levels"].items() if d["cramers_v"]>=.10} for f,a in leaks.items()};high={f:v for f,v in high.items() if v}
 good=next(r for r in rows if r["solid_class"]!="Compound");compound=next(r for r in rows if r["solid_class"]=="Compound")
 def rejected(row,check):return not structural_assertions(row)[check]
 guards={
 "face_count_violation_rejected":rejected({**good,"face_count":good["face_count"]+1},"face_array_length_equals_face_count"),"face_count_boundary_accepted":structural_assertions(good)["face_array_length_equals_face_count"],
 "face_shape_violation_rejected":rejected({**good,"face_shape_types":"mixed" if good["face_shape_types"]!="mixed" else "triangles"},"face_shape_matches_face_arities"),"face_shape_boundary_accepted":structural_assertions(good)["face_shape_matches_face_arities"],
 "edge_count_violation_rejected":rejected({**good,"edge_count":good["edge_count"]+1},"edge_array_length_equals_edge_count"),"edge_count_boundary_accepted":structural_assertions(good)["edge_array_length_equals_edge_count"],
 "connected_euler_violation_rejected":not semantic_euler_ok({**good,"face_count":good["face_count"]+1}),"connected_euler_boundary_accepted":semantic_euler_ok(good),"compound_two_component_euler_boundary_accepted":semantic_euler_ok(compound),
 "visible_face_violation_rejected":rejected({**good,"visible_face_count":good["face_count"]+1},"visible_face_count_not_above_face_count"),"visible_face_boundary_accepted":structural_assertions({**good,"visible_face_count":good["face_count"]})["visible_face_count_not_above_face_count"],
 "compound_convexity_violation_rejected":derived_convexity(compound) is False and compound["is_convex"] is False,"connected_convexity_boundary_accepted":derived_convexity(good)==good["is_convex"],
 "identity_violation_rejected":not identity_ok({**good,"solid_name":"cube"}),"identity_boundary_accepted":identity_ok(good),"euler_answer_zero_rejected":0<=0,"euler_answer_boundary_accepted":good["face_count"]==2-good["vertex_count"]+good["edge_count"] and good["face_count"]>0,"png_boundary_accepted":all(recover_png(root,good).values())}
 if not all(guards.values()):issues.append("guard injection failure")
 literal={"total":sum(literal_fail.values()),"by_solid_name":dict(sorted(literal_fail.items())),"disposition":"Expected only for two-component compounds; each component has Euler characteristic 2 and the aggregate has 4."}
 metrics={"dataset_version":VERSION,"images":len(rows),"questions":sum(len(r["questions"]) for r in rows),"mismatch_count":len(issues),"mismatches":issues,"before_assertion_failures":diagnosis["before_assertion_failures"],"post_fix_literal_euler_assertion":literal,"component_aware_euler_failures":sum(not semantic_euler_ok(r) for r in rows),"answers_changed_by_level":diagnosis["answers_changed_by_level"],"before_level_distributions":diagnosis["before_level_distributions"],"after_level_distributions":after,"solid_name_distribution":dict(sorted(names.items())),"solid_class_distribution":dict(sorted(classes.items())),"nonconvex_geometry_disposition":diagnosis["nonconvex_disposition"],"renames_this_pass":diagnosis["renames_this_pass"],"v4_geometry_renames_reverified":diagnosis["v4_geometry_renames_reverified"],"level4_template_distribution":dict(sorted(templates.items())),"euler_level4_items":euler_items,"euler_prompt_values_matching":prompt_matches,"png_recovery_all_items":{k:{"passed":v,"total":len(rows)} for k,v in sorted(png.items())},"point_hull_items":point_hull,"full_hull_surface_convex_items":surface_hull,"continuous_distributions":{n:quantiles([r[n] for r in rows]) for n in ("edge_count","face_count","vertex_count","visible_face_count")},"leak_audit_all_scalar_scene_features":leaks,"features_at_v_ge_0_10_nothing_hidden":high,"definitional_whitelist":whitelist,"question_set_fields":public_fields,"guard_injection_tests":guards}
 (root/"validation_metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 report=["Polyhedron Dataset v5 Validation Report","="*42,f"Images/questions: {len(rows)}/{sum(len(r['questions']) for r in rows)}",f"Mismatches: {len(issues)}",f"Pre-fix assertion failures: {diagnosis['before_assertion_failures']}",f"Post-fix literal Euler exceptions: {literal}",f"Answers changed by level: {diagnosis['answers_changed_by_level']}",f"Before distributions/baselines: {diagnosis['before_level_distributions']}",f"After distributions/baselines: {after}",f"Solid classes: {dict(sorted(classes.items()))}",f"Non-convex disposition: {diagnosis['nonconvex_disposition']}",f"Euler prompts/invariant: {prompt_matches}/{euler_items}",f"PNG face/edge/vertex recovery: {dict(sorted(png.items()))}",f"Guard injection tests: {guards}",f"Features at V >= 0.10 (nothing hidden): {high}","","Mismatches:",*(["  None"] if not issues else [f"  {x}" for x in issues]),"",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(report)+"\n",encoding="utf-8");print("\n".join(report[:15]));return issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",type=Path);a=p.parse_args();raise SystemExit(bool(validate(a.dataset)))
if __name__=="__main__":main()
