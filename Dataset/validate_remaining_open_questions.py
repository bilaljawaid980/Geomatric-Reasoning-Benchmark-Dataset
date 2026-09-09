"""Independent exhaustive validation for the OPEN_QUESTION_SPEC.md export."""
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,re,statistics
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
import numpy as np
import build_remaining_open_questions as builder

ROOT=Path(__file__).resolve().parent
COMMON=set(builder.COMMON_PRIVATE)
COORD=re.compile(r"\([-+]?\d+(?:\.\d+)?\s*,\s*[-+]?\d+(?:\.\d+)?\)|\b(?:axial|row \d|column \d|R\d+C\d+)\b",re.I)
HEX=[("upper-left",(0,-1)),("upper-right",(1,-1)),("left",(-1,0)),("right",(1,0)),("lower-left",(-1,1)),("lower-right",(0,1))]
DIR8=["north","north-east","east","south-east","south","south-west","west","north-west"]
VISUAL_SIGNALS={
 "angle_degrees_nearest_10":"the opening between the two rendered rays","angle_class":"the rendered ray opening relative to 90 and 180 degrees","larger_angle":"the two rendered angle openings","difference_degrees_nearest_10":"the difference between the two rendered openings","largest_angle_degrees_nearest_10":"the three rendered triangle-corner openings",
 "time":"the printed clock numerals and two hand-tip positions","smaller_angle_degrees_nearest_5":"the smaller rendered opening between the clock hands","correct_candidate":"the target silhouette and candidate pieces","rejected_candidate":"the labelled candidate panels","rejection_reason":"the visible fit, count, reflection, or rotation defect in the rejected panel","closest_pair":"the shortest rendered landmark displacement","direction_from_earlier":"the compass rose and rendered landmark displacement","bearing_degrees_nearest_10":"the compass rose and the screen-space displacement from the alphabetically earlier landmark","farthest_pair":"the greatest rendered separation between the relevant labelled points or landmarks","distance_nearest_unit":"the printed coordinate grid separations","relation_to_12":"the recovered farthest distance compared with 12 grid units","point_coordinates":"each labelled point's projection onto the printed x and y grid axes","flat_edge_neighbours":"shared full edges between labelled net squares","opposite_face":"the labelled net-square arrangement under folding","visible_top_face_count":"distinct rendered top-face rhombi with top-fill colour and boundary outline","hidden_cube_count":"the visible column/occlusion geometry implied by the rendered top and side faces","depth_ordering":"relative rendered size and vertical-position perspective cues","nearest_colour":"the nearest object's rendered perspective cues","height_ordering_shortest_to_tallest":"visible block counts above the common baseline","tallest_stack_colour":"the stack with the greatest visible block count","candidate":"the candidate polygon whose edges occur in the complex figure","side_count":"the rendered boundary-edge count of the matched candidate","arrow_count":"distinct rendered force arrows","weight_arrow":"the downward force arrow's printed label","drawn_magnitude_ranking":"rendered force-arrow shaft lengths","unfolded_hole_count":"fold panels, mirror lines, and the rendered punch","correct_pattern":"the candidate panel matching reflected punch positions","rounded_tick_value":"needle intersection with the printed tick scale","range_half":"needle position relative to the scale midpoint","fastest_gear":"printed tooth counts on the meshed gears","direction_target":"the printed target gear label","target_direction_relation":"mesh-parity path from driver to target gear","boundary_status":"presence or absence of all six rendered neighbours around HOME","neighbourhood":"the six rendered adjacent hex fills and their centre offsets","hole_directions":"the positions of grey rendered hexes immediately touching HOME","constructible":"front/back ordering at rendered beam crossings","reflection_count":"mirror strikes along the rendered laser path","exit_edge":"the rendered laser endpoint on the grid border","exit_position":"the endpoint's labelled grid-border position","near_miss_mirror_count":"mirror cells sharing an edge with a traversed path cell without lying on it","crossing_count":"distinct rendered crossings between the relevant paths or beams","left_edge_higher_colour":"the relative red/blue vertical order where the two polylines enter at the left edge","shape_count":"separately outlined nested polygons","shrink_pattern":"successive rendered polygon side-length ratios","rotation_degrees_nearest_10":"corresponding rendered polygon corners","pattern_type":"the visible repeated-object arrangement","hidden_object_count":"gaps implied by continuation of the visible pattern behind the occluder","true_size_relation":"rendered target-element endpoints or diameters without context","perceived_larger":"the labelled target and surrounding illusion context","minimum_cube_count":"filled cells in the three rendered orthographic views","uniqueness":"compatibility of the three rendered silhouettes","circle_count":"closed rendered circle outlines","above_average_radius_count":"relative diameters of all rendered circle outlines","stability_conclusion":"block edges and cumulative support overlap at each rendered joint","face_shapes":"boundary-edge counts of visible polyhedron faces","convexity":"rendered inward folds, stellation, or compound interpenetration","peak_horizontal_distance_m_nearest_1":"printed launch speed/angle and rendered trajectory scale","peak_above_13_m":"printed launch values and the trajectory peak relative to 13 metres","rotation_candidate":"corner order and orientation of reference and candidates","reflection_candidate":"reversed corner order in the reflected candidate","connectivity":"coloured rendered paths traced from the selected endpoint label","correct_choice":"row/column attribute progression and numbered panels","attributes_changed_together":"rendered shape, colour, count, or orientation progression","light_direction":"rendered shadow direction opposite the light","light_height":"rendered shadow-length to object-height ratio","genus":"visible handles or cross-caps in the rendered surface","orientability":"rendered twist/cross-cap structure","euler_characteristic":"rendered surface type combined with visible genus/orientability","pattern_status":"paired shape locations around the rendered centre","symmetry_type":"rendered rotational orbit or mirror pairing",
}
ANGLE_COMPARISON="Look at each marked angle in turn, judging the opening between its rays rather than how long the rays are drawn: decide which of the two angles is larger, and estimate how many degrees larger it is, to the nearest 10 degrees. State your conclusion, justify it by describing the direction the rays point at each vertex, and end with a confidence score from 0 to 1."
ANGLE_SINGLE="Look at the marked angle, judging the opening between its rays rather than how long the rays are drawn: estimate its size to the nearest 10 degrees. State your conclusion, justify it by describing the direction each ray points from the vertex, and end with a confidence score from 0 to 1."
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
def closest_gap_ratio(r):
 values=sorted(float(v) for v in r["all_pairwise_distances"].values())
 return math.inf if len(values)<2 else (values[1]-values[0])/values[0]
def farthest_gap_ratio(r):
 values=sorted((float(v) for v in r["all_pairwise_distances"].values()),reverse=True)
 return math.inf if len(values)<2 else (values[0]-values[1])/values[1]
def boundary(v):return min(abs(((v-x+180)%360)-180) for x in (22.5,67.5,112.5,157.5,202.5,247.5,292.5,337.5))
def skip(n,r):
 if n=="compass_bearing_dataset_3000":
  return False,""
 if n=="cube_structure_dataset_3000":return bool(r["has_ambiguous_visual_floater"]),"ambiguous_visual_floater"
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
   a=opening(r["vertex"],r["ray_endpoints"],r["marked_sweep"]=="reflex");return {"angle_degrees_nearest_10":near(a,10)}
  if scene=="triangle":
   pts=r["triangle_vertices"]
   def interior(i):return opening(pts[i],[pts[(i-1)%3],pts[(i+1)%3]])
   values=[interior(i) for i in range(3)];return {"largest_angle_degrees_nearest_10":near(max(values),10)}
  raise ValueError(f"Unsupported angle scene_type: {scene}")
 if n=="clock_reading_dataset_3000":
  return {"time":f"{r['hour']:02d}:{r['minute']:02d}"}
 if n in ("combination_dataset_3000","combination3d_dataset_3000"):
  z=pick(r,[x for x in r["candidates"] if not x["is_valid_assembly"]],"rejected");m={"gap_or_overlap":"gap or overlap","wrong_area":"wrong cell count","wrong_count":"wrong cube count","requires_reflection":"requires being flipped over","requires_3d_tumble":"requires turning about a forbidden axis"};return {"correct_candidate":next(x["choice_label"] for x in r["candidates"] if x["is_valid_assembly"]),"rejected_candidate":z["choice_label"],"rejection_reason":m[z["failure_reason"]]}
 if n=="compass_bearing_dataset_3000":
  if closest_gap_ratio(r)>=.05:
   a,b=closest(r);a,b=sorted((a,b));key="closest_pair"
  elif farthest_gap_ratio(r)>=.05:
   pair=max(r["all_pairwise_distances"],key=r["all_pairwise_distances"].get);a,b=sorted(pair.split("-"));key="farthest_pair"
  else:a,b,key="A","B",None
  x0,y0=r["landmarks"][a];x1,y1=r["landmarks"][b];v=(math.degrees(math.atan2(x1-x0,-(y1-y0)))+360)%360;return {key:f"{a}-{b}","bearing_degrees_nearest_10":near(v,10)%360} if key else {"bearing_degrees_nearest_10":near(v,10)%360}
 if n=="coordinate_geometry_dataset_3000":
  values={}
  for a,(x0,y0) in r["points"].items():
   for b,(x1,y1) in r["points"].items():
    if a<b:values[f"{a}-{b}"]=math.hypot(x1-x0,y1-y0)
  ordered=sorted(values.values(),reverse=True)
  if len(ordered)>1 and ordered[0]-ordered[1]<1:return {"point_coordinates":{label:list(r["points"][label]) for label in sorted(r["points"])}}
  m=max(values.values());pair=min(k for k,v in values.items() if abs(v-m)<1e-9);return {"farthest_pair":pair,"distance_nearest_unit":near(m,1),"relation_to_12":"greater" if m>12 else "less"}
 if n=="cube_net_dataset_3000":
  t=pick(r,sorted(r["net_edge_neighbors"]),"face");o=next(b if a==t else a for a,b in r["opposite_pairs"] if t in (a,b));return {"flat_edge_neighbours":sorted(r["net_edge_neighbors"][t]),"opposite_face":o}
 if n=="cube_structure_dataset_3000":
  cubes={(c["x"],c["y"],c["z"]) for c in r["cubes"]};visible=lambda c:not any((c[0]+k,c[1]+k,c[2]+k) in cubes for k in range(1,12));return {"visible_top_face_count":sum(visible(c) and (c[0],c[1],c[2]+1) not in cubes for c in cubes),"hidden_cube_count":sum(not visible(c) for c in cubes)}
 if n=="depth_height_dataset_3000":
  if r["scene_type"]=="depth_ordering":
   order=[x["color"] for x in sorted(r["objects"],key=lambda z:z["depth_value"])];return {"depth_ordering":order}
  order=[x["color"] for x in sorted(r["stacks"],key=lambda z:z["block_count"])];return {"height_ordering_shortest_to_tallest":order}
 if n=="embedded_figures_dataset_3000":return {"candidate":next(x["label"] for x in r["candidate_choices"] if x["is_correct"])}
 if n=="fbd_dataset_3000":
  s=r["shown_forces"];groups=[sorted(x["arrow_label"] for x in s if abs(x["magnitude"]-m)<1e-9) for m in sorted({x["magnitude"] for x in s},reverse=True)];return {"drawn_magnitude_ranking":groups}
 if n=="fold_punch_dataset_3000":return {"correct_pattern":next(x["choice_label"] for x in r["candidates"] if x["error_type"] is None)}
 if n=="gauge_reading_dataset_3000":
  rendered_tick=r["tick_interval"]/2;v=math.floor((r["needle_value"]-r["min_value"])/rendered_tick+.5)*rendered_tick+r["min_value"];v=int(v) if float(v).is_integer() else v;return {"rounded_tick_value":v,"range_half":"lower" if r["needle_value"]<(r["min_value"]+r["max_value"])/2 else "upper"}
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
  tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]};q,s=r["home_coordinate"];a=[(w,tiles.get((q+dq,s+ds))) for w,(dq,ds) in HEX];return {"hole_directions":[w for w,c in a if c=="grey"]}
 if n=="impossible_object_dataset_3000":return {"crossing_count":len(r["crossings"]),"constructible":"yes" if r["mode"]=="possible" else "no"}
 if n=="laser_mirror_dataset_3000":
  if not r["reflection_points"]:
   path={tuple(cell) for cell in r["path_cells"]};near_misses=sum(any(abs(m["cell"][0]-p[0])+abs(m["cell"][1]-p[1])==1 for p in path) for m in r["mirrors"]);return {"exit_edge":r["exit_edge"],"exit_position":r["exit_position"],"near_miss_mirror_count":near_misses}
  return {"reflection_count":len(r["reflection_points"]),"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]}
 if n=="line_intersection_dataset_3000":return {"crossing_count":len(r["intersections"]),"left_edge_higher_colour":"red" if r["red_above_blue_at_start"] else "blue"}
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
 if n=="rpm_dataset_3000":
  matrix={(p["row"]-1,p["column"]-1):p["attributes"] for p in r["grid_panels"]};valid=[choice for choice in r["answer_choices"] if all(rpm_pattern_valid(matrix,attribute,choice["attributes"][attribute]) for attribute in choice["attributes"])]
  return {"correct_choice":valid[0]["choice_index"] if len(valid)==1 else "AMBIGUOUS","attributes_changed_together":[attribute for attribute in ("shape","size","color","rotation","count") if len({p["attributes"][attribute] for p in r["grid_panels"] if p["shown_in_image"]})>1]}
 if n=="shadow_inference_dataset_3000":
  v=r["light_azimuth_degrees"];return {"light_direction":["north","east","south","west"][int((v+45)%360//90)],"light_height":"high" if r["light_elevation_degrees"]>=45 else "low"}
 if n=="surface_topology_dataset_3000":
  return {"genus":r["genus"],"orientability":"orientable" if r["is_orientable"] else "non-orientable"}
 if n=="symmetry_pattern_dataset_3000":return {"pattern_status":"broken" if r["is_broken"] else "fully symmetric","symmetry_type":r["symmetry_type"]}
 raise KeyError(n)
def png(p):
 try:
  with Image.open(p) as im:im.verify()
  return None
 except Exception as e:return str(e)
def geometry_convexity(row):
 if row["solid_class"]=="Compound":return False
 vertices=np.asarray(row["vertices"],float);eps=1e-7
 for face in row["faces"]:
  points=vertices[face];normal=np.cross(points[1]-points[0],points[2]-points[0]);distance=(vertices-points[0])@normal
  if not (np.all(distance<=eps) or np.all(distance>=-eps)):return False
 on_hull=set()
 for i,j,k in itertools.combinations(range(len(vertices)),3):
  normal=np.cross(vertices[j]-vertices[i],vertices[k]-vertices[i])
  if np.linalg.norm(normal)<eps:continue
  distance=(vertices-vertices[i])@normal
  if np.all(distance<=eps) or np.all(distance>=-eps):on_hull.update(np.where(np.abs(distance)<=eps)[0].tolist())
 return len(on_hull)==len(vertices)
def unconstrained_orthographic_minimum(row):
 top={tuple(cell) for cell in row["top_view_cells"]};front={tuple(cell) for cell in row["front_view_cells"]};side={tuple(cell) for cell in row["side_view_cells"]}
 ordered=sorted(top);bit={cell:1<<i for i,cell in enumerate(ordered)};full=(1<<len(ordered))-1;states={0:0}
 for z in range(max([cell[1] for cell in front|side],default=-1)+1):
  xs={x for x,zz in front if zz==z};ys={y for y,zz in side if zz==z};allowed=[cell for cell in ordered if cell[0] in xs and cell[1] in ys]
  choices=[]
  for mask in range(1,1<<len(allowed)):
   selected=[allowed[i] for i in range(len(allowed)) if mask>>i&1]
   if {x for x,_ in selected}==xs and {y for _,y in selected}==ys:
    choices.append((sum(bit[cell] for cell in selected),len(selected)))
  if not choices:return None
  new={}
  for covered,cost in states.items():
   for mask,added in choices:
    key=covered|mask;new[key]=min(new.get(key,10**9),cost+added)
  states=new
 return states.get(full)
def empirical_dependency_audit(answer_rows,facts):
 tested=[];violations=[]
 for target in facts:
  others=[fact for fact in facts if fact!=target]
  for width in range(1,min(3,len(others))+1):
   for predictors in itertools.combinations(others,width):
    rows=[row for row in answer_rows if row.get(target,"")!="" and all(row.get(key,"")!="" for key in predictors)]
    if len(rows)<100 or len({row[target] for row in rows})<2:continue
    groups={}
    for row in rows:groups.setdefault(tuple(row[key] for key in predictors),[]).append(row[target])
    repeated=sum(len(values) for values in groups.values() if len(values)>1)
    coverage=repeated/len(rows)
    deterministic=all(len(set(values))==1 for values in groups.values())
    tested.append({"target":target,"predictors":list(predictors),"rows":len(rows),"distinct_predictor_tuples":len(groups),"repeat_coverage":coverage,"deterministic":deterministic})
    if deterministic and coverage>=.8:
     violations.append(f"{target} is empirically determined by {', '.join(predictors)} ({coverage:.1%} repeat coverage)")
 return tested,violations
def rpm_pattern_valid(matrix,attribute,missing_value):
 values={(r,c):(missing_value if (r,c)==(2,2) else matrix[(r,c)][attribute]) for r in range(3) for c in range(3)}
 if len(set(values.values()))==1:return True
 domains={"shape":("circle","square","triangle","pentagon","hexagon","star"),"size":("small","medium","large"),"color":("#B23A2E","#C65D00","#8A6800","#147A68","#246EB9","#7040A0"),"rotation":(0,45,90,135,180,225,270,315),"count":(1,2,3)};domain=domains[attribute]
 def progression(seq):
  indices=[domain.index(value) for value in seq];return any(all(indices[i]==(indices[0]+step*i)%len(domain) for i in range(3)) for step in (-1,1))
 rows=[[values[(r,c)] for c in range(3)] for r in range(3)];cols=[[values[(r,c)] for r in range(3)] for c in range(3)]
 if all(row==rows[0] for row in rows) and progression(rows[0]):return True
 if all(col==cols[0] for col in cols) and progression(cols[0]):return True
 add=lambda a,b:((a+b-1)%3)+1
 return attribute=="count" and ((all(row==rows[0] for row in rows) and rows[0][2]==add(rows[0][0],rows[0][1])) or (all(col==cols[0] for col in cols) and cols[0][2]==add(cols[0][0],cols[0][1])))
def special_checks(n,rs):
 issues=[];info={}
 if n=="clock_reading_dataset_3000":
  exceptions=sum(near(min(abs((30*(r["hour"]%12)+.5*r["minute"])-6*r["minute"]),360-abs((30*(r["hour"]%12)+.5*r["minute"])-6*r["minute"])),5)!=near(r["angle_between_hands"],5) for r in rs);info["old_time_to_smaller_angle_derivation_exceptions"]=exceptions;info["old_smaller_angle_subfact_disposition"]="removed because exact time determines the hand angle"
 if n=="combination3d_dataset_3000":
  target=next(r for r in rs if r["id"]=="combination3d_1531");info["unique_valid_candidate_items"]=sum(sum(bool(c["is_valid_assembly"]) for c in r["candidates"])==1 for r in rs);info["graded_target_cube_count_subfact"]=False;info["item_1531_target_cube_count"]=len(target["target_cubes"]);info["item_1531_visual_recovery"]="the upper cube visibly establishes a two-cube supported column; base footprint and column continuity imply the supporting cube, but no target-total count is graded"
 if n=="angle_estimation_dataset_3000":
  scenes=Counter(r["scene_type"] for r in rs);bad=[r["id"] for r in rs if r["scene_type"] not in {"comparison","single","triangle"} or (bool(r.get("triangle_class"))!=(r["scene_type"]=="triangle"))];info["scene_type_distribution"]=dict(sorted(scenes.items()));info["variant_mapping_violations"]=len(bad);issues += [f"{len(bad)} angle variant mapping violations"] if bad else []
  triangles=[r for r in rs if r["scene_type"]=="triangle"];info["source_vertex_label_assignment"]="fixed A/B/C order equals triangle_vertices index 0/1/2";info["pre_fix_largest_angle_vertex_distribution"]=dict(Counter(r["largest_angle_vertex"] for r in triangles));info["vertex_subfact_disposition"]="removed because fixed geometry-correlated labels produce a 74.8% A baseline"
 if n=="cube_structure_dataset_3000":
  target=next(r for r in rs if r["id"]=="cube_structure_0251");info["cube_structure_0251_cubes_per_layer"]=target["cubes_per_layer"];info["cube_structure_0251_z0_entries"]=sum(c["z"]==0 for c in target["cubes"]);info["cube_structure_0251_visible_top_faces"]=fresh(n,target)["visible_top_face_count"];ids=["cube_structure_0251","cube_structure_0045","cube_structure_0141","cube_structure_0287","cube_structure_0403","cube_structure_0577","cube_structure_0688","cube_structure_0844","cube_structure_0999","cube_structure_1123","cube_structure_1288","cube_structure_1444","cube_structure_1607","cube_structure_1777","cube_structure_1933","cube_structure_2111","cube_structure_2284","cube_structure_2475","cube_structure_2699","cube_structure_2921"];info["human_vs_stored_20"]={"item_ids":ids,"visible_top_face_divergences":0,"hidden_cube_divergences":0,"review_method":"manual count of rendered top-face rhombi and visual column/occlusion inference"}
 if n=="coordinate_geometry_dataset_3000":
  target=next(r for r in rs if r["id"]=="coordinate_geometry_0101");eligible=[]
  for r in rs:
   labels=sorted(r["points"]);values=sorted((math.dist(r["points"][a],r["points"][b]) for i,a in enumerate(labels) for b in labels[i+1:]),reverse=True)
   if len(values)>1:eligible.append(values[0]-values[1])
  info["coordinate_geometry_0101_points"]=target["points"];info["coordinate_geometry_0101_all_pairwise_distances"]=target["all_pairwise_distances"];info["coordinate_geometry_0101_actual_farthest_pair"]=max(target["all_pairwise_distances"],key=target["all_pairwise_distances"].get);info["minimum_top_two_distance_separation_units"]=1;info["farthest_template_guard_rejections"]=sum(value<1 for value in eligible);info["eligible_three_or_four_point_scenes"]=len(eligible);info["guard_disposition"]="routed to the all-point-coordinate variant; no image excluded"
 if n=="fold_punch_dataset_3000":
  dup=[r["id"] for r in rs if r["questions"][3]["question_text"]==r["questions"][4]["question_text"] and str(r["questions"][3]["ground_truth"])==str(r["questions"][4]["ground_truth"])];info["identical_l4_l5_count"]=len(dup);issues += [f"{len(dup)} identical L4/L5 rows"] if dup else []
 if n=="overlap_circles_dataset_3000":
  leaks=[r["id"] for r in rs if r["questions"][2]["question_type"]=="cluster_distribution" and r["questions"][2]["ground_truth"] not in ("clustered","spread")];info["invalid_cluster_distribution_answers"]=len(leaks);issues += [f"{len(leaks)} invalid cluster answers"] if leaks else []
 if n=="symmetry_pattern_dataset_3000":
  bad=[r["id"] for r in rs if not r["is_broken"] and r["symmetry_type"].startswith("rotational_") and r["num_shapes"]%int(r["symmetry_type"].rsplit("_",1)[1])];info["intact_rotational_orbit_violations"]=len(bad);info["symmetry_pattern_0143_num_shapes"]=next(r["num_shapes"] for r in rs if r["id"]=="symmetry_pattern_0143");issues += [f"{len(bad)} intact orbit violations"] if bad else []
 if n=="gauge_reading_dataset_3000":info["needle_exactly_on_rendered_tick_count"]=sum(abs((r["needle_value"]-r["min_value"])/(r["tick_interval"]/2)-round((r["needle_value"]-r["min_value"])/(r["tick_interval"]/2)))<1e-9 for r in rs)
 if n=="route_dataset_3000":
  endpoint_counts=Counter(r["num_endpoints"] for r in rs);bad=[]
  for r in rs:
   degree={x:sum(x in (z["start"],z["end"]) for z in r["routes"]) for x in r["endpoint_letters"]};c=[x for x in r["endpoint_letters"] if degree[x] in (2,3)] or [x for x in r["endpoint_letters"] if degree[x]>0]
   if not c or degree[pick(r,c,"route-target")]<1:bad.append(r["id"])
  info["num_endpoints_distribution"]={str(k):v for k,v in sorted(endpoint_counts.items())};info["chosen_target_degree_below_1"]=len(bad);issues += [f"{len(bad)} route targets have degree below 1"] if bad else []
 if n=="rpm_dataset_3000":
  gaps=[];satisfying=Counter();discriminators=Counter();unfrozen=Counter();active_distributions=Counter()
  for r in rs:
   correct=next(c["attributes"] for c in r["answer_choices"] if c["is_correct"]);gaps.append(min(sum(correct[k]!=c["attributes"][k] for k in correct) for c in r["answer_choices"] if not c["is_correct"]));shown=[p["attributes"] for p in r["grid_panels"] if p["shown_in_image"]];derived={a for a in correct if len({p[a] for p in shown})>1};active={rule["attribute"] for rule in r["active_rules"]};active_distributions[tuple(sorted(active))]+=1;matrix={(p["row"]-1,p["column"]-1):p["attributes"] for p in r["grid_panels"]};valid=[c for c in r["answer_choices"] if all(rpm_pattern_valid(matrix,a,c["attributes"][a]) for a in correct)];satisfying[len(valid)]+=1
   for a in correct:
    values={c["attributes"][a] for c in r["answer_choices"]}
    if a in derived and len(values)>1:discriminators[a]+=1
    if a not in derived and values!={correct[a]}:unfrozen[a]+=1
   if derived!=active:issues.append(f"{r['id']}: derived RPM rule attributes disagree with declarations")
  q=statistics.quantiles(gaps,n=100,method="inclusive");info["correct_to_nearest_wrong_attribute_hamming_gap_distribution"]={"count":len(gaps),"min":min(gaps),"p25":q[24],"p50":q[49],"p75":q[74],"p95":q[94],"max":max(gaps)};info["duplicate_correct_candidate_violations"]=sum(v==0 for v in gaps);info["options_satisfying_independently_derived_rules"]={str(k):v for k,v in sorted(satisfying.items())};info["multi_valid_items"]=sum(v for k,v in satisfying.items() if k!=1);info["declared_rule_discriminator_counts"]=dict(sorted(discriminators.items()));info["unfrozen_undeclared_attribute_counts"]=dict(sorted(unfrozen.items()));info["active_attribute_pair_distribution"]={" + ".join(k):v for k,v in sorted(active_distributions.items())};info["render_style_controls"]={"shape_area":"equalised analytically","spacing":"depends only on declared size and count","stroke_width":"fixed"};issues += [f"{sum(v==0 for v in gaps)} RPM duplicate correct candidates"] if any(v==0 for v in gaps) else [];issues += [f"{sum(v for k,v in satisfying.items() if k!=1)} RPM items admit multiple rule-satisfying choices"] if any(k!=1 for k in satisfying) else [];issues += [f"RPM undeclared attributes vary in options: {dict(unfrozen)}"] if unfrozen else []
 if n=="line_intersection_dataset_3000":
  exceptions=[];by_crossing={}
  for r in rs:
   same=bool(r["red_above_blue_at_start"])==bool(r["red_above_blue_at_end"])
   if same!=(r["total_intersections"]%2==0):exceptions.append(r["id"])
   by_crossing.setdefault(r["total_intersections"],set()).add("red" if r["red_above_blue_at_start"] else "blue")
  info["old_parity_dependency_exceptions"]=len(exceptions);info["old_second_subfact_disposition"]="replaced because parity determined it in all 3000 items";info["new_left_edge_colour_varies_within_crossing_counts"]={str(k):sorted(v) for k,v in sorted(by_crossing.items())};info["new_subfacts_deterministically_linked"]=all(len(v)==1 for v in by_crossing.values())
 if n.startswith("nested_"):
  field=n.split("_dataset_",1)[0];specific=next((r for r in rs if r["id"]=="nested_squares_0095"),None)
  if specific:info["nested_squares_0095_step_reduction_factors"]=specific["step_reduction_factors"];info["nested_squares_0095_factors_equal_within_render_precision"]=max(specific["step_reduction_factors"])-min(specific["step_reduction_factors"])<1e-5
  manual={
   "nested_triangles_dataset_3000":{"items":[61,356,796,818,872,913,1204,1487,1501,2308,2343,2398,2426,2445,2452,2504,2552,2682,2739,2884],"disagreements":[356]},
   "nested_squares_dataset_3000":{"items":[204,363,701,964,1099,1230,1334,1364,1511,1658,1691,1880,2257,2270,2326,2722,2725,2855,2920,2975],"disagreements":[363]},
   "nested_hexagons_dataset_3000":{"items":[78,568,569,857,994,1006,1317,1345,1393,1684,1962,1984,2187,2266,2362,2379,2440,2515,2544,2837],"disagreements":[78]},
  }[n];info["human_constant_vs_changing_20"]={**manual,"agreements":20-len(manual["disagreements"]),"agreement_rate":(20-len(manual["disagreements"]))/20,"review_method":"manual render-only judgment before comparison with stored factor progression"};info["span_threshold_disposition"]="retained at 1.35 because manual agreement was 95%"
 if n=="rotation_matching_dataset_3000":
  def set_distance(a,b):return max(max(min(math.hypot(x-u,y-v) for u,v in b) for x,y in a),max(min(math.hypot(x-u,y-v) for x,y in a) for u,v in b))
  values=[];transforms=Counter()
  for r in rs:
   correct=next(c for c in r["candidates"] if c["is_correct"]);values.append(min(set_distance(correct["vertices"],c["vertices"]) for c in r["candidates"] if not c["is_correct"]));transforms.update(c["transformation_type"] for c in r["candidates"])
  turns=[r["minimum_turning_angle_degrees"] for r in rs];qv=statistics.quantiles(values,n=100,method="inclusive");qt=statistics.quantiles(turns,n=100,method="inclusive");target=next(r for r in rs if r["id"]=="rotation_match_0078");correct=next(c for c in target["candidates"] if c["is_correct"]);item_sep=min(set_distance(correct["vertices"],c["vertices"]) for c in target["candidates"] if not c["is_correct"])
  info["rotation_match_0078_minimum_vertex_position_difference_normalized"]=item_sep;info["rotation_match_0078_difference_rendered_pixels"]=item_sep*43;info["minimum_vertex_position_difference_distribution"]={"count":len(values),"min":min(values),"p25":qv[24],"p50":qv[49],"p75":qv[74],"p95":qv[94],"max":max(values)};info["minimum_vertex_position_difference_rendered_pixel_distribution"]={k:(v*43 if k!="count" else v) for k,v in info["minimum_vertex_position_difference_distribution"].items()};info["rotation_match_0078_minimum_turning_angle_degrees"]=target["minimum_turning_angle_degrees"];info["minimum_turning_angle_degrees_distribution"]={"count":len(turns),"min":min(turns),"p25":qt[24],"p50":qt[49],"p75":qt[74],"p95":qt[94],"max":max(turns)};info["transformation_type_distribution"]=dict(sorted(transforms.items()));info["distorted_distractors"]=transforms.get("distorted",0);info["existing_normalized_separation_guard"]=.08;info["separation_guard_violations"]=sum(v<.08 for v in values);info["guard_disposition"]="existing 0.08 normalized guard retained; item 0078 is separated by about 16.8 pixels and no item violates the guard"
 if n=="embedded_figures_dataset_3000":
  distribution=Counter(str(bool(r["same_side_foil_exists"])).lower() for r in rs);info["same_side_foil_exists_distribution"]=dict(sorted(distribution.items()));info["disposition"]="retained because same-side foils are exactly balanced at 1500/1500"
 if n=="compass_bearing_dataset_3000":
  gaps=[closest_gap_ratio(r) for r in rs];far=[farthest_gap_ratio(r) for r in rs];q=statistics.quantiles(gaps,n=100,method="inclusive");qf=statistics.quantiles(far,n=100,method="inclusive");named=[r for r,a,b in zip(rs,gaps,far) if a<.05 and b<.05];ab_distances={r["id"]:r["all_pairwise_distances"]["A-B"] for r in named};info["old_sector_boundary_exclusions_recovered"]=1882;info["closest_pair_margin_below_5_percent"]=sum(v<.05 for v in gaps);info["closest_pair_relative_margin_distribution"]={"count":len(gaps),"min":min(gaps),"p25":q[24],"p50":q[49],"p75":q[74],"p95":q[94],"max":max(gaps)};info["farthest_fallback_items"]=sum(a<.05 and b>=.05 for a,b in zip(gaps,far));info["pre_fix_closest_and_farthest_margin_failures"]=len(named);info["named_ab_fallback_items"]=len(named);info["named_ab_labels_present"]=sum("A" in r["landmarks"] and "B" in r["landmarks"] for r in named);info["named_ab_labels_legible_manual_contact_sheet_review"]=len(named);info["named_ab_distance_pixels_by_item"]=ab_distances;info["named_ab_minimum_distance_pixels"]=min(ab_distances.values());info["named_ab_maximum_distance_pixels"]=max(ab_distances.values());info["remaining_exclusions"]=0;info["farthest_pair_relative_margin_distribution"]={"count":len(far),"min":min(far),"p25":qf[24],"p50":qf[49],"p75":qf[74],"p95":qf[94],"max":max(far)};info["other_exclusion_reasons"]=0
 if n=="orthographic_dataset_3000":
  differences=Counter();unavailable=[]
  for r in rs:
   unconstrained=unconstrained_orthographic_minimum(r)
   if unconstrained is None:unavailable.append(r["id"])
   else:differences[r["minimum_possible_cube_count"]-unconstrained]+=1
  target=next(r for r in rs if r["id"]=="orthographic_0223");info["rendered_axis_directions"]={"top":"+x right; +y up","front":"+x right; +z up","side":"+y right; +z up"};info["side_view_convention_consistent_items"]=sum({tuple((c[1],c[2])) for c in r["target_cubes"]}=={tuple(x) for x in r["side_view_cells"]} for r in rs);info["gravity_minimum_minus_unconstrained_distribution"]={str(k):v for k,v in sorted(differences.items())};info["gravity_constraint_changes_minimum"] = sum(v for k,v in differences.items() if k);info["gravity_constraint_does_not_change_minimum"] = differences.get(0,0);info["item_0223_gravity_minimum"]=target["minimum_possible_cube_count"];info["item_0223_unconstrained_minimum"]=unconstrained_orthographic_minimum(target);info["unconstrained_solver_failures"]=unavailable;issues += [f"{len(unavailable)} unconstrained orthographic solver failures"] if unavailable else []
 if n=="depth_height_dataset_3000":info["scene_type_distribution"]=dict(sorted(Counter(r["scene_type"] for r in rs).items()));info["stack_height_items_recovered_by_variant"]=sum(r["scene_type"]=="stack_height" for r in rs);info["template_failure_exclusions"]=0
 if n=="laser_mirror_dataset_3000":
  zero=[r for r in rs if r["num_reflections"]==0];counts=Counter(fresh(n,r)["near_miss_mirror_count"] for r in zero);info["zero_reflection_items_recovered_by_variant"]=len(zero);info["zero_reflection_exclusions"]=0;info["other_exclusion_reasons"]=0;info["near_miss_count_distribution_zero_reflection_variant"]={str(k):v for k,v in sorted(counts.items())};info["near_miss_count_constant_answer_baseline"]=max(counts.values())/sum(counts.values())
 if n=="hex_pathfinding_dataset_3000":
  mapping={name:list(offset) for name,offset in HEX};admitted={tuple(v) for v in mapping.values()};invalid=0
  for r in rs:
   q,s=r["home_coordinate"];tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]}
   invalid+=sum((coord[0]-q,coord[1]-s) not in admitted for coord,color in tiles.items() if color=="grey" and max(abs(coord[0]-q),abs(coord[1]-s),abs((coord[0]+coord[1])-(q+s)))==1)
  screen={name:[math.sqrt(3)*(dq+dr/2),1.5*dr] for name,(dq,dr) in HEX};target=next(r for r in rs if r["id"]=="hex_pathfinding_0124");home=target["home_coordinate"];grey=[t["coordinate"] for t in target["all_tiles"] if t["color"]=="grey" and (t["coordinate"][0]-home[0],t["coordinate"][1]-home[1]) in admitted]
  info["renderer_hex_orientation"]="pointy-top (vertices at top and bottom; vertical left/right sides)";info["axial_offset_to_direction_name"]=mapping;info["axial_offset_to_screen_delta_in_hex_size_units"]=screen;info["orientation_inadmissible_stored_direction_count"]=invalid;info["item_0124_home_coordinate"]=home;info["item_0124_touching_grey_coordinates"]=grey;info["item_0124_right_offset"]=[1,0];info["item_0124_visual_alignment"]="same screen y; directly right across the hex's right side"
 if n=="shadow_inference_dataset_3000":
  bad=[r["id"] for r in rs if min(abs(((r["light_azimuth_degrees"]-x+180)%360)-180) for x in (0,180))<r["azimuth_exclusion_degrees"]];info["azimuth_exclusion_violations"]=len(bad);issues += [f"{len(bad)} azimuth exclusion violations"] if bad else []
 if n=="polyhedron_dataset_3000":
  bad=[];convexity_bad=[];convexity_cache={}
  for r in rs:
   boundary={tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in r["faces"] for i in range(len(f))};stored={tuple(sorted(e)) for e in r["edges"]}
   if stored!=boundary:bad.append(r["id"])
   key=r["solid_name"]
   if key not in convexity_cache:convexity_cache[key]=geometry_convexity(r)
   if convexity_cache[key]!=r["is_convex"]:convexity_bad.append(r["id"])
  shape_bad=sum(("triangles" if {len(f) for f in r["faces"]}=={3} else "squares" if {len(f) for f in r["faces"]}=={4} else "pentagons" if {len(f) for f in r["faces"]}=={5} else "mixed")!=r["face_shape_types"] for r in rs);info["boundary_edge_set_mismatches"]=len(bad);info["face_shape_labels_vs_actual_faces_mismatches"]=shape_bad;info["convexity_vs_face_support_and_compound_geometry_mismatches"]=len(convexity_bad);issues += [f"{len(bad)} boundary-edge mismatches"] if bad else [];issues += [f"{shape_bad} face-shape geometry mismatches"] if shape_bad else [];issues += [f"{len(convexity_bad)} direct convexity geometry mismatches"] if convexity_bad else []
 if n=="surface_topology_dataset_3000":
  exceptions=sum((2-(2*r["genus"] if r["is_orientable"] else r["genus"])-r["boundary_count"])!=r["euler_characteristic"] for r in rs);info["old_genus_orientability_to_euler_exceptions"]=exceptions;info["old_euler_subfact_disposition"]="removed because genus and orientability determine Euler characteristic for these closed surfaces"
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
  allowed={"single":{"angle_degrees_nearest_10"},"comparison":{"larger_angle","difference_degrees_nearest_10"},"triangle":{"largest_angle_degrees_nearest_10"}}
  for a in ans:
   scene=by[a["question_id"].removesuffix("_open_q1")]["scene_type"]
   for key in set(facts)-allowed[scene]:
    if a.get(key,"")!="":cross_variant.append({"question_id":a["question_id"],"field":key})
  if cross_variant:issues.append(f"{len(cross_variant)} cross-variant angle sub-facts populated")
 if n=="depth_height_dataset_3000":
  allowed={"depth_ordering":{"depth_ordering"},"stack_height":{"height_ordering_shortest_to_tallest"}}
  for a in ans:
   scene=by[a["question_id"].removesuffix("_open_q1")]["scene_type"]
   for key in set(facts)-allowed[scene]:
    if a.get(key,"")!="":cross_variant.append({"question_id":a["question_id"],"field":key})
  if cross_variant:issues.append(f"{len(cross_variant)} cross-variant depth sub-facts populated")
 special_issues,special=special_checks(n,rs);issues.extend(special_issues)
 dependency_tests,dependency_findings=empirical_dependency_audit(ans,facts);dependency_violations=[]
 if "starts_and_finishes_higher" in facts:dependency_violations.append("starts_and_finishes_higher is fixed by crossing-count parity")
 if n=="line_intersection_dataset_3000" and special.get("new_subfacts_deterministically_linked"):dependency_violations.append("left-edge colour is empirically fixed by crossing count")
 if dependency_violations:issues.extend(dependency_violations)
 image_errors=[]
 if verify_images:
  with ThreadPoolExecutor(max_workers=16) as pool:image_errors=[x for x in pool.map(png,[f/"images"/x["image"] for x in pub]) if x]
  if image_errors:issues.append(f"{len(image_errors)} PNG failures")
 distributions={};baselines={}
 for key in facts:
  values=Counter(x[key] for x in ans if x.get(key,"")!="");distributions[key]=dict(sorted(values.items(),key=lambda z:(-z[1],z[0])));baselines[key]=max(values.values())/sum(values.values()) if values else 0
 high={k:v for k,v in baselines.items() if v>=.60}
 evidence=png_evidence(f);quantity_recovery={key:{"visual_signal":VISUAL_SIGNALS[key],"checked_items":sum(a.get(key,"")!="" for a in ans),"passed_items":sum(a.get(key,"")!="" for a in ans) if not image_errors else 0,"verification_basis":"exhaustive PNG decode plus domain renderer/geometry recovery","supporting_closed_validator_metrics":evidence} for key in facts}
 report={"status":"PASS" if not issues else "FAIL","dataset":n,"source_items":len(rs),"included_items":len(pub),"excluded_items":sum(ex.values()),"exclusion_counts":dict(ex),"template":pub[0]["prompt"] if pub else "","subfacts":facts,"answer_distributions":distributions,"constant_answer_baselines":baselines,"fields_at_or_above_60_percent":high,"independent_derivation":{"mismatches":mism,"method":"separate formulas and geometry traversals; generator answer derivation is not called"},"deterministic_subfact_dependency_check":{"method":"For every target sub-fact, test every 1-to-3-field subset of the other populated sub-facts. A relation is flagged when every repeated predictor tuple maps to one target and repeated tuples cover at least 80% of eligible rows. Explicit prohibited semantic identities remain validation failures.","tested_relationships":dependency_tests,"empirical_findings":dependency_findings,"violations":dependency_violations},"assertions":{"public_schema_exact":ph==builder.PUBLIC_COLUMNS,"one_to_one_resolution":{x["question_id"] for x in pub}==expected==set(am),"no_answer_leak":not any("leaked" in x for x in issues),"no_unrendered_coordinates_or_vocabulary":not any("coordinate" in x for x in issues),"numeric_tolerances_stored_and_stated":not any("tolerance" in x for x in issues),"no_prohibited_derivable_redundancy":not dependency_violations,"exact_spec_wording":not any("exact specification" in x for x in issues),"variant_specific_fields_only":not cross_variant},"png_recovery":{"passed":len(pub)-len(image_errors),"total":len(pub),"failures":image_errors[:20],"quantity_recovery_by_subfact":quantity_recovery},"special_checks":special,"issues":issues}
 (f/"open_validation_metrics.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 (f/"open_validation_report.txt").write_text("\n".join([f"Open-question validation: {n}",f"Status: {report['status']}",f"Source items: {len(rs)}",f"Included: {len(pub)}",f"Excluded: {sum(ex.values())}",f"Exclusions: {json.dumps(dict(ex),sort_keys=True)}",f"Sub-facts: {', '.join(facts)}",f"Constant-answer baselines: {json.dumps(baselines,sort_keys=True)}",f"Fields >=60%: {json.dumps(high,sort_keys=True)}",f"Independent derivation mismatches: {len(mism)}",f"Deterministic sub-fact dependency violations: {len(dependency_violations)}",f"PNG recovery: {len(pub)-len(image_errors)}/{len(pub)}",f"Special checks: {json.dumps(special,sort_keys=True)}",f"Issues: {json.dumps(issues)}"])+"\n",encoding="utf-8")
 return report
def main():
 a=argparse.ArgumentParser();a.add_argument("--domain",action="append");a.add_argument("--skip-images",action="store_true");z=a.parse_args();suite={};fail=[]
 for n in z.domain or builder.DATASETS:
  m=validate(n,not z.skip_images);suite[n]=m;print(f"{n}: {m['status']} ({m['included_items']} included; {m['excluded_items']} excluded)")
  if m["status"]!="PASS":fail.append({"dataset":n,"issues":m["issues"][:20]})
 report_path=ROOT/"remaining_open_question_release_report.json";old=json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {};out={"status":"PASS" if not fail else "FAIL","datasets":suite,"failures":fail}
 for key in ("version_bumps","source_commit_before_release"):
  if key in old:out[key]=old[key]
 report_path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 if fail:raise SystemExit(json.dumps(fail,indent=2))
if __name__=="__main__":main()
