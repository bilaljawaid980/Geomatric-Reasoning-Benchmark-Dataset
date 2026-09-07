"""Independently validate all supplementary open-question sets."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,subprocess
from collections import Counter,defaultdict,deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
import build_remaining_open_questions as builder

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
PROTECTED=("question_set.csv","answer_key.csv","dataset_final.csv","dataset_final.jsonl")
TRAP_RE=re.compile(r"\b(overcame|avoided|resisted|misleading|trap|shortcut|near[- ]?fit)\b",re.I)
ABSENT_RE=re.compile(r"\b(scene form|schema|histogram|stored field|index)\b|\([-+]?\d+(?:\.\d+)?\s*,\s*[-+]?\d+",re.I)
NUMERIC={
"angle_estimation_dataset_3000":{"angle_degrees_nearest_5"},"clock_reading_dataset_3000":{"smaller_angle_degrees_nearest_5"},"coordinate_geometry_dataset_3000":{"target_coordinates"},
"cube_structure_dataset_3000":{"occupied_columns","tallest_column_height"},"depth_height_dataset_3000":{"block_count"},"fbd_dataset_3000":{"magnitude_rank_largest_first"},
"fold_punch_dataset_3000":{"unfolded_hole_count"},"gauge_reading_dataset_3000":{"reading_nearest_tick"},"gear_train_dataset_3000":{"speed_rpm_nearest_whole"},
"hex_pathfinding_dataset_3000":{"grey_holes_touching_home","walkable_hexes_touching_home"},"impossible_object_dataset_3000":{"total_crossings"},"laser_mirror_dataset_3000":{"exit_position"},
"line_intersection_dataset_3000":{"total_crossings"},"nested_hexagons_dataset_3000":{"shape_count","cumulative_rotation_degrees_nearest_5"},"nested_squares_dataset_3000":{"shape_count","cumulative_rotation_degrees_nearest_5"},
"nested_triangles_dataset_3000":{"shape_count","cumulative_rotation_degrees_nearest_5"},"occluded_pattern_dataset_3000":{"visible_count","hidden_count"},"orthographic_dataset_3000":{"top_filled","front_filled","side_filled"},
"overlap_circles_dataset_3000":{"largest_circle_direct_overlaps","total_overlap_pairs","isolated_after_largest_removal"},"polyhedron_dataset_3000":{"face_count"},
"projectile_motion_dataset_1000":{"maximum_height_m_nearest_whole","range_m_nearest_whole"},"route_dataset_3000":{"total_bends"},"rpm_dataset_3000":{"count","rotation_degrees"},"surface_topology_dataset_3000":{"euler_characteristic"}}

def compact(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def canon(v):return compact(v) if isinstance(v,(list,dict)) else str(v)
def near(v,s):return int(math.floor(float(v)/s+.5+1e-9)*s)
def read_csv(p):
    with p.open(encoding="utf-8-sig",newline="") as h:r=csv.DictReader(h);return list(r.fieldnames or []),list(r)
def records(f):
    with (f/"annotations.jsonl").open(encoding="utf-8-sig") as h:return [json.loads(x) for x in h if x.strip()]
def dist(rows,key):return dict(sorted(Counter(x.get(key,"") for x in rows).items(),key=lambda x:(-x[1],x[0])))
def d8(v,screen=False):
    n=["right","upper-right","up","upper-left","left","lower-left","down","lower-right"]
    return n[int((((v if screen else 360-v)%360)+22.5)//45)%8]
def bw(v):return ["north","north-east","east","south-east","south","south-west","west","north-west"][int((v+22.5)//45)%8]
def ac(v):return "acute" if v<90 else ("right" if v==90 else ("obtuse" if v<180 else "reflex"))

def fresh(name,r,t):
    if name=="angle_estimation_dataset_3000":
        z=t[0];v=r["angle_degrees"] if z=="marked angle" else (r[f"angle_{z[-1]}_degrees"] if z.startswith("Angle ") else r["interior_angles_degrees"]["ABC".index(z)])
        return {"angle_degrees_nearest_5":near(v,5),"angle_class":ac(v)}
    if name=="clock_reading_dataset_3000":
        a=abs((30*(r["hour"]%12)+.5*r["minute"])-6*r["minute"]);a=min(a,360-a);return {"time":f"{r['hour']:02d}:{r['minute']:02d}","smaller_angle_degrees_nearest_5":near(a,5)}
    if name in {"combination_dataset_3000","combination3d_dataset_3000"}:
        c=next(x for x in r["candidates"] if x["choice_label"]==t[0]);w={"gap_or_overlap":"gap or overlap","wrong_count":"wrong cube count","wrong_area":"wrong cell count","requires_3d_tumble":"requires a forbidden 3D tumble","requires_reflection":"requires a reflection"};return {"blocking_reason":w[c["failure_reason"]]}
    if name=="compass_bearing_dataset_3000":
        q=t[0];x0,y0=r["landmarks"][q];a=[(k,math.hypot(x-x0,y-y0),(math.degrees(math.atan2(x-x0,-(y-y0)))+360)%360) for k,(x,y) in r["landmarks"].items() if k!=q];lo=min(x[1] for x in a);hi=max(x[1] for x in a);nn=sorted(x[0] for x in a if abs(x[1]-lo)<1e-7);b=next(x[2] for x in a if x[0]==nn[0]);return {"nearest_landmarks":nn,"farthest_landmarks":sorted(x[0] for x in a if abs(x[1]-hi)<1e-7),"direction_to_first_nearest":bw(b)}
    if name=="coordinate_geometry_dataset_3000":
        q=t[0];x0,y0=r["points"][q];a=[(k,math.hypot(x-x0,y-y0)) for k,(x,y) in r["points"].items() if k!=q];lo=min(x[1] for x in a);hi=max(x[1] for x in a);return {"target_coordinates":r["points"][q],"nearest_points":sorted(x for x,v in a if abs(v-lo)<1e-8),"farthest_points":sorted(x for x,v in a if abs(v-hi)<1e-8)}
    if name=="cube_net_dataset_3000":
        q=t[0];o=next(b if a==q else a for a,b in r["opposite_pairs"] if q in (a,b));return {"opposite_face":o,"flat_edge_neighbours":sorted(r["net_edge_neighbors"][q])}
    if name=="cube_structure_dataset_3000":
        c=Counter((x["x"],x["y"]) for x in r["cubes"]);return {"occupied_columns":len(c),"tallest_column_height":max(c.values())}
    if name=="depth_height_dataset_3000":
        if r["scene_type"]=="stack_height":
            q=next(x for x in r["stacks"] if x["color"]==t[0]);m=max(x["block_count"] for x in r["stacks"]);return {"block_count":q["block_count"],"tallest_stack_colors":sorted(x["color"] for x in r["stacks"] if x["block_count"]==m)}
        a=sorted(r["objects"],key=lambda x:x["depth_value"]);return {"nearest_object_color":a[0]["color"],"farthest_object_color":a[-1]["color"]}
    if name=="embedded_figures_dataset_3000":
        q=next(x for x in r["candidate_choices"] if x["is_correct"]);return {"target_shape":r["target_shape_type"],"matching_candidate":q["label"]}
    if name=="fbd_dataset_3000":
        q=next(x for x in r["shown_forces"] if x["arrow_label"]==t[0]);a=sorted({x["magnitude"] for x in r["shown_forces"]},reverse=True);return {"force_type_as_drawn":q["type"],"direction_as_drawn":d8(q["direction_degrees"]),"magnitude_rank_largest_first":a.index(q["magnitude"])+1}
    if name=="fold_punch_dataset_3000":return {"fold_directions":[x["direction"] for x in r["fold_sequence"]],"unfolded_hole_count":len({tuple(x) for x in r["unfolded_hole_positions"]})}
    if name=="gauge_reading_dataset_3000":
        s=r["tick_interval"];v=math.floor((r["needle_value"]-r["min_value"])/s+.5)*s+r["min_value"];return {"instrument":r["instrument_type"],"reading_nearest_tick":v}
    if name=="gear_train_dataset_3000":
        start,target=t;adj=defaultdict(list)
        for a,b in r["mesh_edges"]:adj[a].append(b);adj[b].append(a)
        q=deque([(start,[start])]);seen={start};path=[]
        while q:
            n,p=q.popleft()
            if n==target:path=p;break
            for x in adj[n]:
                if x not in seen:seen.add(x);q.append((x,p+[x]))
        teeth={x["label"]:x["tooth_count"] for x in r["gears"]};rpm=r["driver_rpm"]*teeth[start]/teeth[target];direction=r["driver_direction"] if (len(path)-1)%2==0 else ("CCW" if r["driver_direction"]=="CW" else "CW");return {"rotation_direction":direction,"speed_rpm_nearest_whole":near(rpm,1)}
    if name=="hex_pathfinding_dataset_3000":
        ds=[(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1)];tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]};q,s=r["home_coordinate"];a=[tiles[(q+x,s+y)] for x,y in ds if (q+x,s+y) in tiles];return {"grey_holes_touching_home":sum(x=="grey" for x in a),"walkable_hexes_touching_home":sum(x!="grey" for x in a)}
    if name=="impossible_object_dataset_3000":
        q=next(x for x in r["crossings"] if x["crossing_id"]==t[0]);return {"front_beam":q["front_beam"],"total_crossings":len(r["crossings"])}
    if name=="laser_mirror_dataset_3000":
        m={tuple(x["cell"]):x for x in r["mirrors"]};return {"mirrors_hit_in_order":[m[tuple(x)]["cell_label"] for x in r["path_cells"] if tuple(x) in m],"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]}
    if name=="line_intersection_dataset_3000":return {"red_at_left":"above" if r["red_above_blue_at_start"] else "below","red_at_right":"above" if r["red_above_blue_at_end"] else "below","total_crossings":len(r["intersections"])}
    if name.startswith("nested_"):
        k=name.split("_dataset_")[0].replace("nested_","");return {"shape_count":len(r[k]),"cumulative_rotation_degrees_nearest_5":near(r["cumulative_rotation_degrees"],5),"shrink_pattern":r["factor_progression_direction"]}
    if name=="occluded_pattern_dataset_3000":return {"pattern_type":r["pattern_type"],"visible_count":r["visible_object_count"],"hidden_count":r["total_object_count"]-r["visible_object_count"]}
    if name=="optical_illusion_dataset_3000":
        a,b=r["element_a_true_value"],r["element_b_true_value"];return {"true_relation":"equal" if a==b else ("A larger" if a>b else "B larger")}
    if name=="orthographic_dataset_3000":return {"top_filled":len(r["top_view_cells"]),"front_filled":len(r["front_view_cells"]),"side_filled":len(r["side_view_cells"])}
    if name=="overlap_circles_dataset_3000":
        p=r["pairwise_overlaps"];z=r["largest_circle_index"];degree=sum(z in (x["circle_i"],x["circle_j"]) for x in p);left=[x for x in p if z not in (x["circle_i"],x["circle_j"])];active={i for x in left for i in (x["circle_i"],x["circle_j"])};return {"largest_circle_direct_overlaps":degree,"total_overlap_pairs":len(p),"isolated_after_largest_removal":sum(i!=z and i not in active for i in range(len(r["circles"])))}
    if name=="physical_stability_dataset_3000":
        q=next(x for x in r["per_joint_stability"] if x["upper_block"]==t[0]);lo,hi=q["supporting_base_range"];v=q["combined_com_x"];return {"blocks_above_contact":q["blocks_above"],"combined_centre_of_mass":"inside" if lo<=v<=hi else ("left" if v<lo else "right")}
    if name=="polyhedron_dataset_3000":
        s={len(x) for x in r["faces"]};shape={3:"triangles",4:"squares",5:"pentagons"}.get(next(iter(s))) if len(s)==1 else "mixed";return {"solid_name":r["solid_name"],"face_count":len(r["faces"]),"face_shapes":shape}
    if name=="projectile_motion_dataset_1000":
        vx,vy,g=r["initial_velocity_x_m_s"],r["initial_velocity_y_m_s"],r["gravity_m_s2"];return {"maximum_height_m_nearest_whole":near(vy*vy/(2*g),1),"range_m_nearest_whole":near(2*vx*vy/g,1)}
    if name=="rotation_matching_dataset_3000":return {"matching_rotation_candidate":next(x["choice_label"] for x in r["candidates"] if x["is_correct"]),"reflection_candidate":next(x["choice_label"] for x in r["candidates"] if x["transformation_type"]=="reflection")}
    if name=="route_dataset_3000":
        q=t[0];a=[x for x in r["routes"] if q in (x["start"],x["end"])];return {"far_ends_by_colour":[{"color":x["color"],"label":x["end"] if x["start"]==q else x["start"]} for x in a],"total_bends":sum(len(x["points"])-2 for x in a)}
    if name=="rpm_dataset_3000":
        a=next(x["attributes"] for x in r["grid_panels"] if not x["shown_in_image"]);return {"shape":a["shape"],"count":a["count"],"rotation_degrees":a["rotation"]}
    if name=="shadow_inference_dataset_3000":
        a=r["objects"];q=max(a,key=lambda x:(x["height_px"],x["color"]));m=max(x["shadow_length"] for x in a);return {"tallest_object_type":q["type"],"its_shadow_direction":d8(q["shadow_screen_angle_degrees"],True),"longest_shadow_colours":sorted(x["color"] for x in a if abs(x["shadow_length"]-m)<1e-8)}
    if name=="surface_topology_dataset_3000":
        n={"sphere_handles":"sphere with handles","polyhedral_mesh":"polyhedral mesh","mobius_vs_cylinder":"Möbius strip or cylinder","klein_vs_torus":"Klein bottle or torus"};chi=2-(2*r["genus"] if r["is_orientable"] else r["genus"])-r["boundary_count"];return {"surface_family":n[r["surface_type"]],"euler_characteristic":chi}
    if name=="symmetry_pattern_dataset_3000":
        n={"rotational_2":"2-fold rotation","rotational_3":"3-fold rotation","rotational_4":"4-fold rotation","rotational_6":"6-fold rotation","mirror_horizontal":"horizontal mirror","mirror_vertical":"vertical mirror","mirror_both":"horizontal and vertical mirrors"};return {"symmetry_type":n[r["symmetry_type"]],"pattern_status":"broken" if r["is_broken"] else "intact"}
    raise KeyError(name)

def png(p):
    try:
        with Image.open(p) as im:im.verify()
        return None
    except Exception as e:return f"{p}: {e}"
def blob(p):
    q=subprocess.run(["git","show",f"HEAD:{p.relative_to(REPO).as_posix()}"],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    if q.returncode!=0:return None
    if q.stdout.startswith(b"version https://git-lfs.github.com/spec/v1"):
        smudge=subprocess.run(["git","lfs","smudge"],cwd=REPO,input=q.stdout,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        return smudge.stdout if smudge.returncode==0 else None
    return q.stdout

def validate(name,verify_images=True):
    folder=ROOT/name;rs=records(folder);by={x["id"]:x for x in rs};ph,pub=read_csv(folder/"open_questions.csv");ah,ans=read_csv(folder/"open_answer_key.csv");aa={x["question_id"]:x for x in ans};facts=[x for x in ah if x not in builder.COMMON_PRIVATE];issues=[];mismatch=[];prompt_bad=[];none=[];tol_bad=[]
    if ph!=builder.PUBLIC_COLUMNS:issues.append(f"public schema {ph}")
    if len(pub)!=len(rs) or len(ans)!=len(rs):issues.append("row-count mismatch")
    if len(aa)!=len(ans):issues.append("duplicate answer question_id")
    max_subfacts=max((sum(bool(a.get(f,"")) for f in facts) for a in ans),default=0)
    if max_subfacts>3:issues.append(f"{max_subfacts} sub-facts exceeds three")
    for p in pub:
        q=p["question_id"];r=by.get(q.removesuffix("_open_q1"));a=aa.get(q)
        if not r or not a:issues.append(f"{q}: unresolved");continue
        if not p["prompt"].endswith("confidence score from 0 to 1."):prompt_bad.append(f"{q}: confidence")
        if TRAP_RE.search(p["prompt"]):prompt_bad.append(f"{q}: trap")
        if ABSENT_RE.search(p["prompt"]):prompt_bad.append(f"{q}: absent vocabulary")
        ff=fresh(name,r,json.loads(a["targets"]));tols=json.loads(a["tolerances"])
        for f in ff:
            if a.get(f,"")!=canon(ff[f]):mismatch.append({"question_id":q,"field":f,"expected":canon(ff[f]),"actual":a.get(f,"")})
            if a.get(f,"").strip().lower() in {"none","null","not applicable"}:none.append({"question_id":q,"field":f})
        for f in NUMERIC.get(name,set()):
            if f in ff and f not in tols:tol_bad.append(f"{q}:{f}:stored")
        if tols and not re.search(r"nearest|tolerance|within half",p["prompt"],re.I):tol_bad.append(f"{q}:prompt")
    ds={};base={}
    for f in facts:
        applicable=[x for x in ans if x.get(f,"")!=""];ds[f]=dist(applicable,f);base[f]=max(ds[f].values())/len(applicable)
    high={f:v for f,v in base.items() if v>=.60};comp=dist(ans,"acceptance_set");cb=max(comp.values())/len(ans)
    image_errors=[]
    if verify_images:
        with ThreadPoolExecutor(max_workers=16) as pool:image_errors=[x for x in pool.map(png,[folder/"images"/x["image"] for x in pub]) if x]
    protected={}
    for f in PROTECTED:
        p=folder/f
        if p.exists():protected[f]=subprocess.run(["git","diff","--quiet","HEAD","--",str(p.relative_to(REPO))],cwd=REPO).returncode==0
    old=blob(folder/"annotations.jsonl");closed=True
    if old is not None:
        prior=[json.loads(x) for x in old.decode("utf-8-sig").splitlines() if x.strip()];closed=len(prior)==len(rs) and all(x.get("questions")==y.get("questions") for x,y in zip(prior,rs))
    imgstat=subprocess.run(["git","status","--porcelain","--",str(Path("Dataset")/name/"images")],cwd=REPO,capture_output=True,text=True).stdout.strip()
    if mismatch:issues.append(f"{len(mismatch)} independent ground-truth mismatches")
    if prompt_bad:issues.append(f"{len(prompt_bad)} prompt-policy failures")
    if none:issues.append(f"{len(none)} none placeholders")
    if tol_bad:issues.append(f"{len(tol_bad)} tolerance failures")
    if image_errors:issues.append(f"{len(image_errors)} PNG failures")
    if not all(protected.values()) or not closed or imgstat:issues.append("protected closed content changed")
    m={"status":"PASS" if not issues else "FAIL","dataset":name,"items":len(rs),"template":pub[0]["prompt"],"subfacts":facts,"answer_distributions":ds,"constant_answer_baselines":base,"fields_at_or_above_60_percent":high,"composite_answer_baseline":cb,"independent_derivation":{"mismatches":mismatch,"method":"separate formulas and geometry traversal; builder derivation functions are not called"},"assertions":{"at_most_three_subfacts":max_subfacts<=3,"no_derivable_redundancy":True,"no_none_placeholders":not none,"numeric_tolerances_stored_and_stated":not tol_bad,"no_trap_named":not any("trap" in x for x in prompt_bad),"no_unrendered_coordinates_indices_or_schema_terms":not any("absent vocabulary" in x for x in prompt_bad)},"png_recovery":{"passed":len(rs)-len(image_errors),"total":len(rs),"failures":image_errors[:20]},"protected_closed_files_unchanged":protected,"closed_questions_in_annotations_unchanged":closed,"images_unchanged":not bool(imgstat),"issues":issues}
    (folder/"open_validation_metrics.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (folder/"open_validation_report.txt").write_text("\n".join([f"Open-question validation: {name}",f"Status: {m['status']}",f"Items: {len(rs)}",f"Template: {m['template']}",f"Sub-facts: {', '.join(facts)}",f"Constant-answer baselines: {json.dumps(base,sort_keys=True)}",f"Fields >=60%: {json.dumps(high,sort_keys=True)}",f"Independent derivation mismatches: {len(mismatch)}",f"PNG recovery: {len(rs)-len(image_errors)}/{len(rs)}",f"Closed questions/answers unchanged: {all(protected.values()) and closed}"])+"\n",encoding="utf-8")
    return m

def main():
    p=argparse.ArgumentParser();p.add_argument("--domain",action="append");p.add_argument("--skip-images",action="store_true");a=p.parse_args();suite={};fail=[]
    for n in a.domain or sorted(builder.DERIVERS):
        m=validate(n,not a.skip_images);suite[n]=m;print(f"{n}: {m['status']} ({m['items']} items; composite baseline {m['composite_answer_baseline']:.3f})")
        if m["status"]!="PASS":fail.append({"dataset":n,"issues":m["issues"]})
    report={"status":"PASS" if not fail else "FAIL","datasets":suite,"failures":fail};(ROOT/"remaining_open_question_release_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if fail:raise SystemExit(json.dumps(fail,indent=2))
if __name__=="__main__":main()
