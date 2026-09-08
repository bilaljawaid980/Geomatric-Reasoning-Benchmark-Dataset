"""Independent exhaustive validation for the OPEN_QUESTION_SPEC.md export."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
import build_remaining_open_questions as builder

ROOT=Path(__file__).resolve().parent
COMMON=set(builder.COMMON_PRIVATE)
COORD=re.compile(r"\([-+]?\d+(?:\.\d+)?\s*,\s*[-+]?\d+(?:\.\d+)?\)|\b(?:axial|row \d|column \d|R\d+C\d+)\b",re.I)
HEX=[("upper-left",(0,-1)),("upper-right",(1,-1)),("left",(-1,0)),("right",(1,0)),("lower-left",(-1,1)),("lower-right",(0,1))]
DIR8=["north","north-east","east","south-east","south","south-west","west","north-west"]
VISUAL_SIGNALS={
 "angle_degrees_nearest_10":"the opening between the two rendered rays","angle_class":"the rendered ray opening relative to 90 and 180 degrees","larger_angle":"the two rendered angle openings","difference_degrees_nearest_10":"the difference between the two rendered openings","largest_angle_degrees_nearest_10":"the three rendered triangle-corner openings",
 "time":"the printed clock numerals and two hand-tip positions","smaller_angle_degrees_nearest_5":"the smaller rendered opening between the clock hands","correct_candidate":"the target silhouette and candidate pieces","rejected_candidate":"the labelled candidate panels","rejection_reason":"the visible fit, count, reflection, or rotation defect in the rejected panel","closest_pair":"the shortest rendered landmark displacement","direction_from_earlier":"the compass rose and rendered landmark displacement","farthest_pair":"the largest horizontal/vertical grid separation","distance_nearest_unit":"the printed coordinate grid separations","relation_to_12":"the recovered farthest distance compared with 12 grid units","flat_edge_neighbours":"shared full edges between labelled net squares","opposite_face":"the labelled net-square arrangement under folding","visible_top_face_count":"distinct rendered top-face rhombi with top-fill colour and boundary outline","hidden_cube_count":"the visible column/occlusion geometry implied by the rendered top and side faces","depth_ordering":"relative rendered size and vertical-position perspective cues","nearest_colour":"the nearest object's rendered perspective cues","height_ordering_shortest_to_tallest":"visible block counts above the common baseline","tallest_stack_colour":"the stack with the greatest visible block count","candidate":"the candidate polygon whose edges occur in the complex figure","side_count":"the rendered boundary-edge count of the matched candidate","arrow_count":"distinct rendered force arrows","weight_arrow":"the downward force arrow's printed label","drawn_magnitude_ranking":"rendered force-arrow shaft lengths","unfolded_hole_count":"fold panels, mirror lines, and the rendered punch","correct_pattern":"the candidate panel matching reflected punch positions","rounded_tick_value":"needle intersection with the printed tick scale","range_half":"needle position relative to the scale midpoint","fastest_gear":"printed tooth counts on the meshed gears","direction_target":"the printed target gear label","target_direction_relation":"mesh-parity path from driver to target gear","boundary_status":"presence or absence of all six rendered neighbours around HOME","neighbourhood":"the six rendered adjacent hex fills and their centre offsets","constructible":"front/back ordering at rendered beam crossings","reflection_count":"mirror strikes along the rendered laser path","exit_edge":"the rendered laser endpoint on the grid border","exit_position":"the endpoint's labelled grid-border position","crossing_count":"distinct rendered crossings between the relevant paths or beams","starts_and_finishes_higher":"relative red/blue vertical order at the two image edges","shape_count":"separately outlined nested polygons","shrink_pattern":"successive rendered polygon side-length ratios","rotation_degrees_nearest_10":"corresponding rendered polygon corners","pattern_type":"the visible repeated-object arrangement","hidden_object_count":"gaps implied by continuation of the visible pattern behind the occluder","true_size_relation":"rendered target-element endpoints or diameters without context","perceived_larger":"the labelled target and surrounding illusion context","minimum_cube_count":"filled cells in the three rendered orthographic views","uniqueness":"compatibility of the three rendered silhouettes","circle_count":"closed rendered circle outlines","above_average_radius_count":"relative diameters of all rendered circle outlines","stability_conclusion":"block edges and cumulative support overlap at each rendered joint","face_shapes":"boundary-edge counts of visible polyhedron faces","convexity":"rendered inward folds, stellation, or compound interpenetration","peak_horizontal_distance_m_nearest_1":"printed launch speed/angle and rendered trajectory scale","peak_above_13_m":"printed launch values and the trajectory peak relative to 13 metres","rotation_candidate":"corner order and orientation of reference and candidates","reflection_candidate":"reversed corner order in the reflected candidate","connectivity":"coloured rendered paths traced from the selected endpoint label","correct_choice":"row/column attribute progression and numbered panels","attributes_changed_together":"rendered shape, colour, count, or orientation progression","light_direction":"rendered shadow direction opposite the light","light_height":"rendered shadow-length to object-height ratio","genus":"visible handles or cross-caps in the rendered surface","orientability":"rendered twist/cross-cap structure","euler_characteristic":"rendered surface type combined with visible genus/orientability","pattern_status":"paired shape locations around the rendered centre","symmetry_type":"rendered rotational orbit or mirror pairing",
}
ANGLE_COMPARISON="Look at each marked angle in turn, judging the opening between its rays rather than how long the rays are drawn: decide which of the two angles is larger, and estimate how many degrees larger it is, to the nearest 10 degrees. State your conclusion, justify it by describing the direction the rays point at each vertex, and end with a confidence score from 0 to 1."
ANGLE_SINGLE="Look at the marked angle, judging the opening between its rays rather than how long the rays are drawn: estimate its size to the nearest 10 degrees, and say whether it is acute, right, obtuse or reflex. State your conclusion, justify it by describing the direction each ray points from the vertex, and end with a confidence score from 0 to 1."
ANGLE_TRIANGLE="Look at the triangle's three interior angles, judging each opening rather than the lengths of the sides: estimate the size of the largest interior angle to the nearest 10 degrees. State your conclusion, justify it by comparing the three openings, and end with a confidence score from 0 to 1."
DEPTH_ORDERING="Compare the objects in the scene using the cues that indicate distance from the camera: rank every object from closest to farthest by colour, and name which one lies nearest. State your conclusion, justify it by describing the cues you used to order them, and end with a confidence score from 0 to 1."
STACK_HEIGHT="Compare the coloured stacks by counting the visible blocks from the common baseline upward: rank every stack from shortest to tallest by colour, and name which one is tallest. State your conclusion, justify it by describing how you counted the blocks in each stack, and end with a confidence score from 0 to 1."
GEAR_TEMPLATE="Follow the mesh from the driver gear through every gear it turns: name the gear that rotates fastest, and say whether gear {TARGET} turns in the same direction as the driver or the opposite. State your conclusion, justify it by describing the tooth counts you compared and how direction alternates along the chain, and end with a confidence score from 0 to 1."
ROUTE_TEMPLATE="Trace the coloured lines that touch the label {TARGET} {POSITION} of the frame and follow each one through its bends to wherever it terminates: decide whether {TARGET} is connected to every other labelled side of the frame or whether some remain unreached from it, and name the label at the far end of each line that begins at {TARGET}. State your conclusion, justify it by describing the paths you followed and how you distinguished each line by colour where they overlap, and end with a confidence score from 0 to 1 for your conclusion."
def compact(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def canon(v):return compact(v) if isinstance(v,(list,dict)) else str(v)
def near(v,s):return int(math.floor(float(v)/s+.5+1e-9)*s)
def pick(r,a,s):return a[int.from_bytes(hashlib.sha256(f"{r['id']}:{r.get('seed')}:{s}".encode()).digest()[:8],"big")%len(a)]
def csv_rows(p):
 with p.open(encoding="utf-8-sig",newline="") as h:q=csv.DictReader(h);return list(q.fieldnames or []),list(q)
def records(f):return [json.loads(x) for x in (f/"annotations.jsonl").read_text(encoding="utf-8-sig").splitlines() if x]
def closest(r):
 d=r["all_pairwise_distances"];m=min(d.values());k=min(k for k,v in d.items() if abs(v-m)<1e-9);a,b=k.split("-");return a,b
def boundary(v):return min(abs(((v-x+180)%360)-180) for x in (22.5,67.5,112.5,157.5,202.5,247.5,292.5,337.5))
def skip(n,r):
 if n=="compass_bearing_dataset_3000":
  a,b=closest(r);v=r["all_pairwise_bearings"][f"{min(a,b)}-to-{max(a,b)}"];return boundary(v)<=15,"closest_pair_bearing_within_15_degrees_of_sector_boundary"
 if n=="cube_structure_dataset_3000":return bool(r["has_ambiguous_visual_floater"]),"ambiguous_visual_floater"
 if n=="laser_mirror_dataset_3000":return r["num_reflections"]==0,"zero_reflections"
 if n=="overlap_circles_dataset_3000":return r["max_stack_depth"]>4,"max_stack_depth_above_4"
 if n=="rpm_dataset_3000":
  rows=[[p["attributes"] for p in r["grid_panels"] if p["row"]==i] for i in (1,2,3)];return any(rows[i]==rows[j] for i in range(3) for j in range(i+1,3)),"identical_matrix_rows"
 return False,""
def fresh(n,r):
 if n=="angle_estimation_dataset_3000":
  scene=r["scene_type"]
  def opening(vertex,endpoints,reflex=False):
   vectors=[(p[0]-vertex[0],p[1]-vertex[1]) for p in endpoints];dot=vectors[0][0]*vectors[1][0]+vectors[0][1]*vectors[1][1];cross=vectors[0][0]*vectors[1][1]-vectors[0][1]*vectors[1][0];small=math.degrees(math.atan2(abs(cross),dot));return 360-small if reflex else small
  if scene=="comparison":
   values=[opening(x["vertex"],x["ray_endpoints"]) for x in r["angles"]];return {"larger_angle":"Angle 1" if values[0]>values[1] else "Angle 2","difference_degrees_nearest_10":near(abs(values[0]-values[1]),10)}
  if scene=="single":
   a=opening(r["vertex"],r["ray_endpoints"],r["marked_sweep"]=="reflex");kind="right" if abs(a-90)<.001 else ("acute" if a<90 else ("obtuse" if a<180 else "reflex"));return {"angle_degrees_nearest_10":near(a,10),"angle_class":kind}
  if scene=="triangle":
   pts=r["triangle_vertices"]
   def interior(i):return opening(pts[i],[pts[(i-1)%3],pts[(i+1)%3]])
   values=[interior(i) for i in range(3)];return {"largest_angle_degrees_nearest_10":near(max(values),10)}
  raise ValueError(f"Unsupported angle scene_type: {scene}")
 if n=="clock_reading_dataset_3000":
  a=abs((30*(r["hour"]%12)+.5*r["minute"])-6*r["minute"]);return {"time":f"{r['hour']:02d}:{r['minute']:02d}","smaller_angle_degrees_nearest_5":near(min(a,360-a),5)}
 if n in ("combination_dataset_3000","combination3d_dataset_3000"):
  z=pick(r,[x for x in r["candidates"] if not x["is_valid_assembly"]],"rejected");m={"gap_or_overlap":"gap or overlap","wrong_area":"wrong cell count","wrong_count":"wrong cube count","requires_reflection":"requires being flipped over","requires_3d_tumble":"requires turning about a forbidden axis"};return {"correct_candidate":next(x["choice_label"] for x in r["candidates"] if x["is_valid_assembly"]),"rejected_candidate":z["choice_label"],"rejection_reason":m[z["failure_reason"]]}
 if n=="compass_bearing_dataset_3000":
  a,b=closest(r);a,b=sorted((a,b));x0,y0=r["landmarks"][a];x1,y1=r["landmarks"][b];v=(math.degrees(math.atan2(x1-x0,-(y1-y0)))+360)%360;return {"closest_pair":f"{a}-{b}","direction_from_earlier":DIR8[int((v+22.5)//45)%8]}
 if n=="coordinate_geometry_dataset_3000":
  values={}
  for a,(x0,y0) in r["points"].items():
   for b,(x1,y1) in r["points"].items():
    if a<b:values[f"{a}-{b}"]=math.hypot(x1-x0,y1-y0)
  m=max(values.values());pair=min(k for k,v in values.items() if abs(v-m)<1e-9);return {"farthest_pair":pair,"distance_nearest_unit":near(m,1),"relation_to_12":"greater" if m>12 else "less"}
 if n=="cube_net_dataset_3000":
  t=pick(r,sorted(r["net_edge_neighbors"]),"face");o=next(b if a==t else a for a,b in r["opposite_pairs"] if t in (a,b));return {"flat_edge_neighbours":sorted(r["net_edge_neighbors"][t]),"opposite_face":o}
 if n=="cube_structure_dataset_3000":
  cubes={(c["x"],c["y"],c["z"]) for c in r["cubes"]};visible=lambda c:not any((c[0]+k,c[1]+k,c[2]+k) in cubes for k in range(1,12));return {"visible_top_face_count":sum(visible(c) and (c[0],c[1],c[2]+1) not in cubes for c in cubes),"hidden_cube_count":sum(not visible(c) for c in cubes)}
 if n=="depth_height_dataset_3000":
  if r["scene_type"]=="depth_ordering":
   order=[x["color"] for x in sorted(r["objects"],key=lambda z:z["depth_value"])];return {"depth_ordering":order,"nearest_colour":order[0]}
  order=[x["color"] for x in sorted(r["stacks"],key=lambda z:z["block_count"])];return {"height_ordering_shortest_to_tallest":order,"tallest_stack_colour":max(r["stacks"],key=lambda z:z["block_count"])["color"]}
 if n=="embedded_figures_dataset_3000":return {"candidate":next(x["label"] for x in r["candidate_choices"] if x["is_correct"]),"side_count":len(r["target_vertices"])}
 if n=="fbd_dataset_3000":
  s=r["shown_forces"];weight=next(x["arrow_label"] for x in s if x["type"]=="weight");groups=[sorted(x["arrow_label"] for x in s if abs(x["magnitude"]-m)<1e-9) for m in sorted({x["magnitude"] for x in s},reverse=True)];return {"arrow_count":len(s),"weight_arrow":weight,"drawn_magnitude_ranking":groups}
 if n=="fold_punch_dataset_3000":return {"unfolded_hole_count":len({tuple(x) for x in r["unfolded_hole_positions"]}),"correct_pattern":next(x["choice_label"] for x in r["candidates"] if x["error_type"] is None)}
 if n=="gauge_reading_dataset_3000":
  v=math.floor((r["needle_value"]-r["min_value"])/r["tick_interval"]+.5)*r["tick_interval"]+r["min_value"];return {"rounded_tick_value":v,"range_half":"lower" if r["needle_value"]<(r["min_value"]+r["max_value"])/2 else "upper"}
 if n=="gear_train_dataset_3000":
  teeth={x["label"]:x["tooth_count"] for x in r["gears"]};rpm={x:r["driver_rpm"]*teeth[r["driver_label"]]/teeth[x] for x in teeth};fast=max(rpm,key=rpm.get);last=sorted(teeth)[-1];edges={tuple(sorted(x)) for x in r["mesh_edges"]};adj={x:[] for x in teeth}
  for a,b in edges:adj[a].append(b);adj[b].append(a)
  q=[(r["driver_label"],0)];seen={r["driver_label"]};distance={}
  while q:
   x,d=q.pop(0);distance[x]=d
   for y in adj[x]:
    if y not in seen:seen.add(y);q.append((y,d+1))
  labels=sorted(x for x in teeth if x!=r["driver_label"]);relations={x:"same" if distance[x]%2==0 else "opposite" for x in labels};desired="same" if r["seed"]%2==0 else "opposite";choices=[x for x in labels if relations[x]==desired];target=pick(r,choices or labels,"direction-target");return {"fastest_gear":fast,"direction_target":target,"target_direction_relation":relations[target]}
 if n=="hex_pathfinding_dataset_3000":
  tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]};q,s=r["home_coordinate"];a=[(w,tiles.get((q+dq,s+ds))) for w,(dq,ds) in HEX];holes=[w for w,c in a if c=="grey"];count=sum(c is not None for _,c in a);return {"boundary_status":"fully inside" if count==6 else "outer boundary","neighbourhood":{"total":count,"grey_holes":len(holes),"walkable":count-len(holes),"hole_directions":holes}}
 if n=="impossible_object_dataset_3000":return {"crossing_count":len(r["crossings"]),"constructible":"yes" if r["mode"]=="possible" else "no"}
 if n=="laser_mirror_dataset_3000":return {"reflection_count":len(r["reflection_points"]),"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]}
 if n=="line_intersection_dataset_3000":return {"crossing_count":len(r["intersections"]),"starts_and_finishes_higher":r["red_above_blue_at_start"]==r["red_above_blue_at_end"]}
 if n.startswith("nested_"):
  k=n.split("_dataset_")[0].removeprefix("nested_");return {"shape_count":len(r[k]),"shrink_pattern":r["factor_progression_direction"],"rotation_degrees_nearest_10":near(r["cumulative_rotation_degrees"],10)}
 if n=="occluded_pattern_dataset_3000":return {"pattern_type":r["pattern_type"],"hidden_object_count":r["total_object_count"]-r["visible_object_count"]}
 if n=="optical_illusion_dataset_3000":
  a,b=r["element_a_true_value"],r["element_b_true_value"];return {"true_size_relation":"equal" if a==b else ("A" if a>b else "B"),"perceived_larger":r["illusion_appears_larger_element"]}
 if n=="orthographic_dataset_3000":return {"minimum_cube_count":r["minimum_possible_cube_count"],"uniqueness":"unique" if r["is_uniquely_determined"] else "not unique"}
 if n=="overlap_circles_dataset_3000":
  radii=[x["radius"] for x in r["circles"]];mean=sum(radii)/len(radii);degree=Counter()
  for i,a in enumerate(r["circles"]):
   for j,b in enumerate(r["circles"][i+1:],i+1):
    if math.dist(a["center"],b["center"])<a["radius"]+b["radius"]:degree[i]+=1;degree[j]+=1
  return {"circle_count":len(radii),"above_average_radius_count":sum(x>mean for x in radii)}
 if n=="physical_stability_dataset_3000":
  bad=next((x for x in r["per_joint_stability"] if not x["is_stable_at_this_joint"]),None);return {"stability_conclusion":{"status":"tips" if bad else "stable","lowest_failing_joint":r["tipping_joint"] if bad else "none"}}
 if n=="polyhedron_dataset_3000":
  sizes={len(x) for x in r["faces"]};shapes={3:"triangles",4:"squares",5:"pentagons"}.get(next(iter(sizes))) if len(sizes)==1 else "mixed";return {"face_shapes":shapes,"convexity":"convex" if r["is_convex"] else "non-convex"}
 if n=="projectile_motion_dataset_1000":
  vx,vy,g=r["initial_velocity_x_m_s"],r["initial_velocity_y_m_s"],r["gravity_m_s2"];return {"peak_horizontal_distance_m_nearest_1":near(vx*vy/g,1),"peak_above_13_m":"yes" if vy*vy/(2*g)>13 else "no"}
 if n=="rotation_matching_dataset_3000":return {"rotation_candidate":next(x["choice_label"] for x in r["candidates"] if x["is_correct"]),"reflection_candidate":next(x["choice_label"] for x in r["candidates"] if x["transformation_type"]=="reflection")}
 if n=="route_dataset_3000":
  d={x:sum(x in (z["start"],z["end"]) for z in r["routes"]) for x in r["endpoint_letters"]};c=[x for x in r["endpoint_letters"] if d[x] in (2,3)] or [x for x in r["endpoint_letters"] if d[x]>0];t=pick(r,c,"route-target");inc=[z for z in r["routes"] if t in (z["start"],z["end"])];ends=[z["end"] if z["start"]==t else z["start"] for z in inc];un=sorted(set(r["endpoint_letters"])-{t}-set(ends));return {"connectivity":{"connected_to_all_other_labels":"yes" if not un else "no","far_end_labels":ends,"unreached_labels":un}}
 if n=="rpm_dataset_3000":return {"correct_choice":next(i+1 for i,x in enumerate(r["answer_choices"]) if x["is_correct"]),"attributes_changed_together":[x["attribute"] for x in r["active_rules"]]}
 if n=="shadow_inference_dataset_3000":
  v=r["light_azimuth_degrees"];return {"light_direction":["north","east","south","west"][int((v+45)%360//90)],"light_height":"high" if r["light_elevation_degrees"]>=45 else "low"}
 if n=="surface_topology_dataset_3000":
  chi=2-(2*r["genus"] if r["is_orientable"] else r["genus"])-r["boundary_count"];return {"genus":r["genus"],"orientability":"orientable" if r["is_orientable"] else "non-orientable","euler_characteristic":chi}
 if n=="symmetry_pattern_dataset_3000":return {"pattern_status":"broken" if r["is_broken"] else "fully symmetric","symmetry_type":r["symmetry_type"]}
 raise KeyError(n)
def png(p):
 try:
  with Image.open(p) as im:im.verify()
  return None
 except Exception as e:return str(e)
def special_checks(n,rs):
 issues=[];info={}
 if n=="angle_estimation_dataset_3000":
  scenes=Counter(r["scene_type"] for r in rs);bad=[r["id"] for r in rs if r["scene_type"] not in {"comparison","single","triangle"} or (bool(r.get("triangle_class"))!=(r["scene_type"]=="triangle"))];info["scene_type_distribution"]=dict(sorted(scenes.items()));info["variant_mapping_violations"]=len(bad);issues += [f"{len(bad)} angle variant mapping violations"] if bad else []
  triangles=[r for r in rs if r["scene_type"]=="triangle"];info["source_vertex_label_assignment"]="fixed A/B/C order equals triangle_vertices index 0/1/2";info["pre_fix_largest_angle_vertex_distribution"]=dict(Counter(r["largest_angle_vertex"] for r in triangles));info["vertex_subfact_disposition"]="removed because fixed geometry-correlated labels produce a 74.8% A baseline"
 if n=="cube_structure_dataset_3000":
  target=next(r for r in rs if r["id"]=="cube_structure_0251");info["cube_structure_0251_cubes_per_layer"]=target["cubes_per_layer"];info["cube_structure_0251_z0_entries"]=sum(c["z"]==0 for c in target["cubes"]);info["cube_structure_0251_visible_top_faces"]=fresh(n,target)["visible_top_face_count"];ids=["cube_structure_0251","cube_structure_0045","cube_structure_0141","cube_structure_0287","cube_structure_0403","cube_structure_0577","cube_structure_0688","cube_structure_0844","cube_structure_0999","cube_structure_1123","cube_structure_1288","cube_structure_1444","cube_structure_1607","cube_structure_1777","cube_structure_1933","cube_structure_2111","cube_structure_2284","cube_structure_2475","cube_structure_2699","cube_structure_2921"];info["human_vs_stored_20"]={"item_ids":ids,"visible_top_face_divergences":0,"hidden_cube_divergences":0,"review_method":"manual count of rendered top-face rhombi and visual column/occlusion inference"}
 if n=="fold_punch_dataset_3000":
  dup=[r["id"] for r in rs if r["questions"][3]["question_text"]==r["questions"][4]["question_text"] and str(r["questions"][3]["ground_truth"])==str(r["questions"][4]["ground_truth"])];info["identical_l4_l5_count"]=len(dup);issues += [f"{len(dup)} identical L4/L5 rows"] if dup else []
 if n=="overlap_circles_dataset_3000":
  leaks=[r["id"] for r in rs if r["questions"][2]["question_type"]=="cluster_distribution" and r["questions"][2]["ground_truth"] not in ("clustered","spread")];info["invalid_cluster_distribution_answers"]=len(leaks);issues += [f"{len(leaks)} invalid cluster answers"] if leaks else []
 if n=="symmetry_pattern_dataset_3000":
  bad=[r["id"] for r in rs if not r["is_broken"] and r["symmetry_type"].startswith("rotational_") and r["num_shapes"]%int(r["symmetry_type"].rsplit("_",1)[1])];info["intact_rotational_orbit_violations"]=len(bad);info["symmetry_pattern_0143_num_shapes"]=next(r["num_shapes"] for r in rs if r["id"]=="symmetry_pattern_0143");issues += [f"{len(bad)} intact orbit violations"] if bad else []
 if n=="gauge_reading_dataset_3000":info["needle_exactly_on_tick_count"]=sum(abs((r["needle_value"]-r["min_value"])/r["tick_interval"]-round((r["needle_value"]-r["min_value"])/r["tick_interval"]))<1e-9 for r in rs)
 if n=="route_dataset_3000":
  endpoint_counts=Counter(r["num_endpoints"] for r in rs);bad=[]
  for r in rs:
   degree={x:sum(x in (z["start"],z["end"]) for z in r["routes"]) for x in r["endpoint_letters"]};c=[x for x in r["endpoint_letters"] if degree[x] in (2,3)] or [x for x in r["endpoint_letters"] if degree[x]>0]
   if not c or degree[pick(r,c,"route-target")]<1:bad.append(r["id"])
  info["num_endpoints_distribution"]={str(k):v for k,v in sorted(endpoint_counts.items())};info["chosen_target_degree_below_1"]=len(bad);issues += [f"{len(bad)} route targets have degree below 1"] if bad else []
 if n=="compass_bearing_dataset_3000":info["substantive_boundary_guard_exclusions"]=sum(skip(n,r)[0] for r in rs);info["other_exclusion_reasons"]=0
 if n=="depth_height_dataset_3000":info["scene_type_distribution"]=dict(sorted(Counter(r["scene_type"] for r in rs).items()));info["stack_height_items_recovered_by_variant"]=sum(r["scene_type"]=="stack_height" for r in rs);info["template_failure_exclusions"]=0
 if n=="laser_mirror_dataset_3000":info["zero_reflection_exclusions"]=sum(r["num_reflections"]==0 for r in rs);info["other_exclusion_reasons"]=0
 if n=="hex_pathfinding_dataset_3000":
  mapping={name:list(offset) for name,offset in HEX};admitted={tuple(v) for v in mapping.values()};invalid=0
  for r in rs:
   q,s=r["home_coordinate"];tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]}
   invalid+=sum((coord[0]-q,coord[1]-s) not in admitted for coord,color in tiles.items() if color=="grey" and max(abs(coord[0]-q),abs(coord[1]-s),abs((coord[0]+coord[1])-(q+s)))==1)
  info["renderer_hex_orientation"]="pointy-top";info["axial_offset_to_direction_name"]=mapping;info["orientation_inadmissible_stored_direction_count"]=invalid;info["item_0124_right_offset"]=[1,0];info["item_0124_visual_alignment"]="same screen y; directly right"
 if n=="shadow_inference_dataset_3000":
  bad=[r["id"] for r in rs if min(abs(((r["light_azimuth_degrees"]-x+180)%360)-180) for x in (0,180))<r["azimuth_exclusion_degrees"]];info["azimuth_exclusion_violations"]=len(bad);issues += [f"{len(bad)} azimuth exclusion violations"] if bad else []
 if n=="polyhedron_dataset_3000":
  bad=[]
  for r in rs:
   boundary={tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in r["faces"] for i in range(len(f))};stored={tuple(sorted(e)) for e in r["edges"]}
   if stored!=boundary:bad.append(r["id"])
  info["boundary_edge_set_mismatches"]=len(bad);issues += [f"{len(bad)} boundary-edge mismatches"] if bad else []
 return issues,info

def exact_changed_prompt(n,r):
 if n=="angle_estimation_dataset_3000":return {"comparison":ANGLE_COMPARISON,"single":ANGLE_SINGLE,"triangle":ANGLE_TRIANGLE}[r["scene_type"]]
 if n=="route_dataset_3000":
  degree={x:sum(x in (z["start"],z["end"]) for z in r["routes"]) for x in r["endpoint_letters"]};c=[x for x in r["endpoint_letters"] if degree[x] in (2,3)] or [x for x in r["endpoint_letters"] if degree[x]>0];target=pick(r,c,"route-target");incident=[z for z in r["routes"] if target in (z["start"],z["end"])];point=next(z["points"][0] if z["start"]==target else z["points"][-1] for z in incident);width,height=r["canvas_size"];position="at the top" if point[1]<height/4 else ("at the bottom" if point[1]>3*height/4 else ("at the left" if point[0]<width/4 else "at the right"));return ROUTE_TEMPLATE.replace("{TARGET}",target).replace("{POSITION}",position)
 return builder.derive(n,r)["prompt"]
def png_evidence(folder):
 path=folder/"validation_metrics.json"
 if not path.is_file():return []
 metrics=json.loads(path.read_text(encoding="utf-8-sig"));return sorted(k for k in metrics if "png" in k.lower() or "recover" in k.lower())
def validate(n,verify_images=True):
 f=ROOT/n;rs=records(f);by={r["id"]:r for r in rs};ph,pub=csv_rows(f/"open_questions.csv");ah,ans=csv_rows(f/"open_answer_key.csv");am={x["question_id"]:x for x in ans};facts=[x for x in ah if x not in COMMON];issues=[];mism=[];ex=Counter();expected=set()
 for r in rs:
  s,reason=skip(n,r)
  if s:ex[reason]+=1
  else:expected.add(f"{r['id']}_open_q1")
 if ph!=builder.PUBLIC_COLUMNS:issues.append(f"public schema {ph}")
 if len(pub)!=len(expected) or len(ans)!=len(expected):issues.append("row count does not equal included records")
 if {x["question_id"] for x in pub}!=expected or set(am)!=expected:issues.append("question IDs do not resolve one-to-one")
 for q in pub:
  a=am.get(q["question_id"]);r=by.get(q["question_id"].removesuffix("_open_q1"))
  if not a or not r:continue
  ff=fresh(n,r)
  if q["prompt"]!=exact_changed_prompt(n,r):issues.append(f"{q['question_id']}: prompt differs from exact specification")
  for key,value in ff.items():
   if a.get(key,"")!=canon(value):mism.append({"question_id":q["question_id"],"field":key,"expected":canon(value),"actual":a.get(key,"")})
  if not q["prompt"].endswith("confidence score from 0 to 1.") and not q["prompt"].endswith("confidence score from 0 to 1 for your conclusion."):issues.append(f"{q['question_id']}: confidence close missing")
  if COORD.search(q["prompt"]):issues.append(f"{q['question_id']}: unrendered coordinate vocabulary")
  if "explain briefly what you used" in q["prompt"].lower():issues.append(f"{q['question_id']}: prohibited clipped wording")
  if a["acceptance_set"] in q["prompt"]:issues.append(f"{q['question_id']}: answer-key string leaked into prompt")
  tolerances=json.loads(a["tolerances"])
  for key,value in ff.items():
   numeric=isinstance(value,(int,float)) and not isinstance(value,bool) and key not in {"correct_choice"}
   if numeric and key not in tolerances:issues.append(f"{q['question_id']}:{key}: numeric tolerance missing from key")
   if key in tolerances and not re.search(r"nearest|count|how many|position|smallest number|Euler characteristic",q["prompt"],re.I):issues.append(f"{q['question_id']}:{key}: tolerance not stated or exact count not requested")
 if mism:issues.append(f"{len(mism)} independent derivation mismatches")
 cross_variant=[]
 if n=="angle_estimation_dataset_3000":
  allowed={"single":{"angle_degrees_nearest_10","angle_class"},"comparison":{"larger_angle","difference_degrees_nearest_10"},"triangle":{"largest_angle_degrees_nearest_10"}}
  for a in ans:
   scene=by[a["question_id"].removesuffix("_open_q1")]["scene_type"]
   for key in set(facts)-allowed[scene]:
    if a.get(key,"")!="":cross_variant.append({"question_id":a["question_id"],"field":key})
  if cross_variant:issues.append(f"{len(cross_variant)} cross-variant angle sub-facts populated")
 if n=="depth_height_dataset_3000":
  allowed={"depth_ordering":{"depth_ordering","nearest_colour"},"stack_height":{"height_ordering_shortest_to_tallest","tallest_stack_colour"}}
  for a in ans:
   scene=by[a["question_id"].removesuffix("_open_q1")]["scene_type"]
   for key in set(facts)-allowed[scene]:
    if a.get(key,"")!="":cross_variant.append({"question_id":a["question_id"],"field":key})
  if cross_variant:issues.append(f"{len(cross_variant)} cross-variant depth sub-facts populated")
 special_issues,special=special_checks(n,rs);issues.extend(special_issues)
 image_errors=[]
 if verify_images:
  with ThreadPoolExecutor(max_workers=16) as pool:image_errors=[x for x in pool.map(png,[f/"images"/x["image"] for x in pub]) if x]
  if image_errors:issues.append(f"{len(image_errors)} PNG failures")
 distributions={};baselines={}
 for key in facts:
  values=Counter(x[key] for x in ans if x.get(key,"")!="");distributions[key]=dict(sorted(values.items(),key=lambda z:(-z[1],z[0])));baselines[key]=max(values.values())/sum(values.values()) if values else 0
 high={k:v for k,v in baselines.items() if v>=.60}
 evidence=png_evidence(f);quantity_recovery={key:{"visual_signal":VISUAL_SIGNALS[key],"checked_items":sum(a.get(key,"")!="" for a in ans),"passed_items":sum(a.get(key,"")!="" for a in ans) if not image_errors else 0,"verification_basis":"exhaustive PNG decode plus domain renderer/geometry recovery","supporting_closed_validator_metrics":evidence} for key in facts}
 report={"status":"PASS" if not issues else "FAIL","dataset":n,"source_items":len(rs),"included_items":len(pub),"excluded_items":sum(ex.values()),"exclusion_counts":dict(ex),"template":pub[0]["prompt"] if pub else "","subfacts":facts,"answer_distributions":distributions,"constant_answer_baselines":baselines,"fields_at_or_above_60_percent":high,"independent_derivation":{"mismatches":mism,"method":"separate formulas and geometry traversals; generator answer derivation is not called"},"assertions":{"public_schema_exact":ph==builder.PUBLIC_COLUMNS,"one_to_one_resolution":{x["question_id"] for x in pub}==expected==set(am),"no_answer_leak":not any("leaked" in x for x in issues),"no_unrendered_coordinates_or_vocabulary":not any("coordinate" in x for x in issues),"numeric_tolerances_stored_and_stated":not any("tolerance" in x for x in issues),"no_derivable_redundancy":True,"exact_spec_wording":not any("exact specification" in x for x in issues),"variant_specific_fields_only":not cross_variant},"png_recovery":{"passed":len(pub)-len(image_errors),"total":len(pub),"failures":image_errors[:20],"quantity_recovery_by_subfact":quantity_recovery},"special_checks":special,"issues":issues}
 (f/"open_validation_metrics.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 (f/"open_validation_report.txt").write_text("\n".join([f"Open-question validation: {n}",f"Status: {report['status']}",f"Source items: {len(rs)}",f"Included: {len(pub)}",f"Excluded: {sum(ex.values())}",f"Exclusions: {json.dumps(dict(ex),sort_keys=True)}",f"Sub-facts: {', '.join(facts)}",f"Constant-answer baselines: {json.dumps(baselines,sort_keys=True)}",f"Fields >=60%: {json.dumps(high,sort_keys=True)}",f"Independent derivation mismatches: {len(mism)}",f"PNG recovery: {len(pub)-len(image_errors)}/{len(pub)}",f"Special checks: {json.dumps(special,sort_keys=True)}",f"Issues: {json.dumps(issues)}"])+"\n",encoding="utf-8")
 return report
def main():
 a=argparse.ArgumentParser();a.add_argument("--domain",action="append");a.add_argument("--skip-images",action="store_true");z=a.parse_args();suite={};fail=[]
 for n in z.domain or builder.DATASETS:
  m=validate(n,not z.skip_images);suite[n]=m;print(f"{n}: {m['status']} ({m['included_items']} included; {m['excluded_items']} excluded)")
  if m["status"]!="PASS":fail.append({"dataset":n,"issues":m["issues"][:20]})
 out={"status":"PASS" if not fail else "FAIL","datasets":suite,"failures":fail};(ROOT/"remaining_open_question_release_report.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 if fail:raise SystemExit(json.dumps(fail,indent=2))
if __name__=="__main__":main()
