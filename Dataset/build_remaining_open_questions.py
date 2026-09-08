"""Build the supplementary questions specified by OPEN_QUESTION_SPEC.md."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PUBLIC_COLUMNS=["question_id","image","prompt"]
COMMON_PRIVATE=["question_id","image","acceptance_set","tolerances","targets"]

ANGLE_COMPARISON="Look at each marked angle in turn, judging the opening between its rays rather than how long the rays are drawn: decide which of the two angles is larger, and estimate how many degrees larger it is, to the nearest 10 degrees. State your conclusion, justify it by describing the direction the rays point at each vertex, and end with a confidence score from 0 to 1."
ANGLE_SINGLE="Look at the marked angle, judging the opening between its rays rather than how long the rays are drawn: estimate its size to the nearest 10 degrees. State your conclusion, justify it by describing the direction each ray points from the vertex, and end with a confidence score from 0 to 1."
ANGLE_TRIANGLE="Look at the triangle's three interior angles, judging each opening rather than the lengths of the sides: estimate the size of the largest interior angle to the nearest 10 degrees. State your conclusion, justify it by comparing the three openings, and end with a confidence score from 0 to 1."
DEPTH_ORDERING="Compare the objects in the scene using the cues that indicate distance from the camera: rank every object from closest to farthest by colour. State your conclusion, justify it by describing the cues you used to order them, and end with a confidence score from 0 to 1."
STACK_HEIGHT="Compare the coloured stacks by counting the visible blocks from the common baseline upward: rank every stack from shortest to tallest by colour. State your conclusion, justify it by describing how you counted the blocks in each stack, and end with a confidence score from 0 to 1."
GEAR_TEMPLATE="Follow the mesh from the driver gear through every gear it turns: name the gear that rotates fastest, and say whether gear {TARGET} turns in the same direction as the driver or the opposite. State your conclusion, justify it by describing the tooth counts you compared and how direction alternates along the chain, and end with a confidence score from 0 to 1."
ROUTE_TEMPLATE="Trace the coloured lines that touch the label {TARGET} {POSITION} of the frame and follow each one through its bends to wherever it terminates: decide whether {TARGET} is connected to every other labelled side of the frame or whether some remain unreached from it, and name the label at the far end of each line that begins at {TARGET}. State your conclusion, justify it by describing the paths you followed and how you distinguished each line by colour where they overlap, and end with a confidence score from 0 to 1 for your conclusion."
COORDINATE_FALLBACK="Read every labelled point against the printed coordinate grid: report the coordinates of all points in alphabetical order. State your conclusion, justify it by describing how you projected each point to the horizontal and vertical axes, and end with a confidence score from 0 to 1."
LASER_STRAIGHT="Follow the laser from where it enters the grid and trace its straight path across: name the edge and position where it leaves, and say how many mirrors it passes without striking. State your conclusion, justify it by describing the path you traced and where the nearest mirrors sit relative to it, and end with a confidence score from 0 to 1."
COMPASS_FARTHEST="Read the compass rose in the corner, then take the two landmarks that lie farthest apart and give the bearing in degrees from the alphabetically earlier of them to the other, measuring clockwise from north and answering to the nearest 10 degrees. State your conclusion, justify it by describing the displacement you measured and how you read the direction against the rose, and end with a confidence score from 0 to 1."
COMPASS_NAMED_AB="Read the compass rose in the corner, then give the bearing in degrees from landmark A to landmark B, measuring clockwise from north and answering to the nearest 10 degrees. State your conclusion, justify it by describing the displacement you measured and how you read the direction against the rose, and end with a confidence score from 0 to 1."

P={
"angle_estimation_dataset_3000":ANGLE_COMPARISON,
"clock_reading_dataset_3000":"Trace both hands from the centre of the dial out towards the printed numerals: work out which is the hour hand and which is the minute hand, and read the time they show. State your conclusion, justify it by describing where each hand tip falls among the numerals, and end with a confidence score from 0 to 1.",
"combination_dataset_3000":"Compare each separated piece of every candidate with the target shape: decide which single candidate could be slid and turned, without being flipped over, to reproduce the target exactly, and say what disqualifies one of the candidates you rejected. State your conclusion, justify it by describing how you tried to fit the pieces together, and end with a confidence score from 0 to 1.",
"combination3d_dataset_3000":"Compare each separated group of cubes in every candidate with the target structure: decide which single candidate could be moved and turned about the upright axis to reproduce the target exactly, and say what disqualifies one of the candidates you rejected. State your conclusion, justify it by describing how you tried to fit the groups together and how you accounted for cubes hidden behind others, and end with a confidence score from 0 to 1.",
"compass_bearing_dataset_3000":"Read the compass rose in the corner, then compare the straight-line displacement between every pair of landmarks: name the two landmarks that lie closest together, and give the bearing in degrees from the alphabetically earlier of them to the other, measuring clockwise from north and answering to the nearest 10 degrees. State your conclusion, justify it by describing the displacements you compared and how you read the direction against the rose, and end with a confidence score from 0 to 1.",
"coordinate_geometry_dataset_3000":"Read the position of each labelled point against the printed grid: name the pair of points that lie farthest apart, give that distance to the nearest whole unit, and say whether it is greater or less than 12 units. State your conclusion, justify it by describing the horizontal and vertical grid separations you used, and end with a confidence score from 0 to 1.",
"cube_structure_dataset_3000":"Scan the structure cube by cube, taking as vertical the direction the drawing renders as up: count exactly how many cubes have a visible top face, then work out exactly how many cubes are completely hidden from this viewpoint (tolerance 0 for both counts). State your conclusion, justify it by describing how you separated visible top faces from side faces and how the visible stacks imply any concealed cubes, and end with a confidence score from 0 to 1.",
"depth_height_dataset_3000":DEPTH_ORDERING,
"embedded_figures_dataset_3000":"Study the complex figure and each of the candidate shapes beneath it: decide which candidate is hidden inside the figure. State your conclusion, justify it by describing where in the figure you located the shape and which lines belong to it rather than to the surrounding clutter, and end with a confidence score from 0 to 1.",
"fbd_dataset_3000":"Examine only the force arrows as they are drawn in this diagram, setting aside what the scenario physically requires: rank their drawn magnitudes from largest to smallest, grouping any that appear equal. State your conclusion, justify it by describing the length and direction of each arrow as drawn, and end with a confidence score from 0 to 1.",
"fold_punch_dataset_3000":"Follow the fold sequence from the first panel through to the punch: decide which of the unfolded patterns below shows the holes in the right places. State your conclusion, justify it by describing how you reflected the punch across each fold line, and end with a confidence score from 0 to 1.",
"gauge_reading_dataset_3000":"Read the needle against the printed scale: give the value it points to, rounded to the nearest tick mark, and say whether that value lies in the lower or upper half of the gauge's range. State your conclusion, justify it by describing which numbered marks the needle falls between, and end with a confidence score from 0 to 1.",
"gear_train_dataset_3000":GEAR_TEMPLATE,
"impossible_object_dataset_3000":"Trace each beam through the structure and look closely at the points where one beam passes in front of another: count those crossings, then decide whether the depth relationships they imply could all hold at once in a real three-dimensional object. State your conclusion, justify it by describing which beam passes in front at the crossings that decide the matter, and end with a confidence score from 0 to 1.",
"laser_mirror_dataset_3000":"Follow the laser from where it enters the grid, turning it at each mirror it meets: count how many times it reflects, and name the edge and position where it leaves the grid. State your conclusion, justify it by describing the path you traced and which mirrors it struck, and end with a confidence score from 0 to 1.",
"line_intersection_dataset_3000":"Follow both polylines across the image from left edge to right: count how many times they cross one another, and say which colour is higher at the left edge. State your conclusion, justify it by describing where along the width of the image the crossings fall and how you compared the two starting heights, and end with a confidence score from 0 to 1.",
"occluded_pattern_dataset_3000":"Look at the objects visible around the occluder and the arrangement they suggest: name the kind of pattern they form, then work out how many objects the occluder is hiding from view. State your conclusion, justify it by describing how the visible objects let you infer where the pattern continues, and end with a confidence score from 0 to 1.",
"optical_illusion_dataset_3000":"Measure the two marked elements against one another, disregarding the lines and shapes surrounding them: decide whether they are truly equal in size or whether one is genuinely larger, and separately say which one a typical human viewer would perceive as larger. State your conclusion, justify it by describing what you measured and what the surrounding context does to the impression, and end with a confidence score from 0 to 1.",
"orthographic_dataset_3000":"Compare the three orthographic views against one another: work out the smallest number of cubes a gravity-supported structure could have while still producing all three, and decide whether those views pin down a single arrangement or whether some different arrangement could produce the same three silhouettes. State your conclusion, justify it by describing which view constrains which direction, and end with a confidence score from 0 to 1.",
"overlap_circles_dataset_3000":"Examine every circle and the way they lie across one another: count how many circles there are, and give how many are larger than the average size. State your conclusion, justify it by describing how you traced individual outlines where several circles overlap, and end with a confidence score from 0 to 1.",
"physical_stability_dataset_3000":"Work up the stack from the ground, tracking where the combined weight of everything above each joint falls relative to the block beneath it: decide whether the stack stands or tips, and if it tips, name the lowest joint at which it first fails. State your conclusion, justify it by describing how each block sits relative to the one it rests on, and end with a confidence score from 0 to 1.",
"polyhedron_dataset_3000":"Examine the solid's visible faces and the edges bounding them: say what shapes its faces are, and decide whether the solid is convex or whether some part of it folds inward. State your conclusion, justify it by describing the faces you could identify and how you judged convexity, and end with a confidence score from 0 to 1.",
"projectile_motion_dataset_1000":"Read the launch values printed beside the trajectory and follow the arc from launch to landing: give the horizontal distance at which the projectile reaches its highest point, to the nearest metre, and say whether that peak rises above 13 metres. State your conclusion, justify it by describing which printed values you used and how they determine the shape of the arc, and end with a confidence score from 0 to 1.",
"rotation_matching_dataset_3000":"Compare each candidate figure with the reference above them: decide which candidate is the reference turned rather than flipped over, and identify the one candidate that is a mirror image rather than a rotation. State your conclusion, justify it by describing which corners you matched between the reference and each candidate, and end with a confidence score from 0 to 1.",
"rpm_dataset_3000":"Read across the rows and down the columns of the matrix to work out what changes from one panel to the next: decide which of the numbered choices completes the pattern, and say which attributes had to change together for that choice to be the right one. State your conclusion, justify it by describing the progression you found along the rows and down the columns, and end with a confidence score from 0 to 1.",
"shadow_inference_dataset_3000":"Compare each object with the shadow it casts on the ground: say from which general direction the light is coming, and whether it sits high in the sky or low near the horizon. State your conclusion, justify it by describing the direction the shadows fall and how their length compares with the height of the objects casting them, and end with a confidence score from 0 to 1.",
"surface_topology_dataset_3000":"Examine the surface and trace how it closes back on itself: count how many holes or handles it has and decide whether it is orientable. State your conclusion, justify it by describing the feature that fixes the genus and whether the surface has a consistent inside and outside, and end with a confidence score from 0 to 1.",
"symmetry_pattern_dataset_3000":"Examine every shape and where it sits relative to the centre of the arrangement: work out which shapes pair with which, decide whether the pattern is fully symmetric or whether one element has been displaced from where its partner requires it to be, and say what kind of symmetry the arrangement is built on. State your conclusion, justify it by describing which shapes you paired and how you judged their positions, and end with a confidence score from 0 to 1.",
}
FAIL={"gap_or_overlap":"gap or overlap","wrong_area":"wrong cell count","wrong_count":"wrong cube count","requires_reflection":"requires being flipped over","requires_3d_tumble":"requires turning about a forbidden axis"}
DIR8=["north","north-east","east","south-east","south","south-west","west","north-west"]
HEX=[("upper-left",(0,-1)),("upper-right",(1,-1)),("left",(-1,0)),("right",(1,0)),("lower-left",(-1,1)),("lower-right",(0,1))]
def compact(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def pick(r,a,s):return a[int.from_bytes(hashlib.sha256(f"{r['id']}:{r.get('seed')}:{s}".encode()).digest()[:8],"big")%len(a)]
def near(v,s):return int(math.floor(float(v)/s+.5+1e-9)*s)
def out(prompt,facts,targets,tolerances=None,derivation=None):return {"prompt":prompt,"facts":facts,"targets":targets,"tolerances":tolerances or {},"derivation":derivation or {},"acceptance_set":["; ".join(f"{k}={compact(v) if isinstance(v,(list,dict)) else v}" for k,v in facts.items())]}
def closest(r):
 d=r["all_pairwise_distances"];m=min(d.values());k=min(k for k,v in d.items() if abs(v-m)<1e-9);a,b=k.split("-");return a,b,m
def closest_gap_ratio(r):
 values=sorted(float(v) for v in r["all_pairwise_distances"].values())
 return math.inf if len(values)<2 else (values[1]-values[0])/values[0]
def farthest_gap_ratio(r):
 values=sorted((float(v) for v in r["all_pairwise_distances"].values()),reverse=True)
 return math.inf if len(values)<2 else (values[0]-values[1])/values[1]
def farthest_gap(r):
 labels=sorted(r["points"]);values=sorted((math.dist(r["points"][a],r["points"][b]) for i,a in enumerate(labels) for b in labels[i+1:]),reverse=True);return math.inf if len(values)<2 else values[0]-values[1]
def laser_near_misses(r):
 path={tuple(cell) for cell in r["path_cells"]};mirrors=[tuple(m["cell"]) for m in r["mirrors"]]
 return sum(any(abs(cell[0]-p[0])+abs(cell[1]-p[1])==1 for p in path) for cell in mirrors)
def bd(v):return min(abs(((v-x+180)%360)-180) for x in (22.5,67.5,112.5,157.5,202.5,247.5,292.5,337.5))
def excluded(n,r):
 if n=="compass_bearing_dataset_3000":return False,""
 if n=="cube_structure_dataset_3000":return bool(r["has_ambiguous_visual_floater"]),"ambiguous_visual_floater"
 if n=="overlap_circles_dataset_3000":return r["max_stack_depth"]>4,"max_stack_depth_above_4"
 if n=="rpm_dataset_3000":
  rows=[[p["attributes"] for p in r["grid_panels"] if p["row"]==i] for i in (1,2,3)];return any(rows[i]==rows[j] for i in range(3) for j in range(i+1,3)),"identical_matrix_rows"
 return False,""
def derive(n,r):
 p=P.get(n)
 if n=="angle_estimation_dataset_3000":
  scene=r["scene_type"]
  if scene=="comparison":
   a,b=r["angle_1_degrees"],r["angle_2_degrees"];return out(ANGLE_COMPARISON,{"larger_angle":"Angle 1" if a>b else "Angle 2","difference_degrees_nearest_10":near(abs(a-b),10)},["Angle 1","Angle 2"],{"difference_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
  if scene=="single":
   a=r["angle_degrees"];return out(ANGLE_SINGLE,{"angle_degrees_nearest_10":near(a,10)},["marked angle"],{"angle_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
  if scene=="triangle":
   angles=r["interior_angles_degrees"];return out(ANGLE_TRIANGLE,{"largest_angle_degrees_nearest_10":near(max(angles),10)},["triangle interior angles"],{"largest_angle_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
  raise ValueError(f"Unsupported angle scene_type: {scene}")
 if n=="clock_reading_dataset_3000":return out(p,{"time":r["time"]},["clock hands"])
 if n in ("combination_dataset_3000","combination3d_dataset_3000"):
  z=pick(r,[x for x in r["candidates"] if not x["is_valid_assembly"]],"rejected");return out(p,{"correct_candidate":r["correct_answer_choice"],"rejected_candidate":z["choice_label"],"rejection_reason":FAIL[z["failure_reason"]]},["target","candidate panel"])
 if n=="compass_bearing_dataset_3000":
  if closest_gap_ratio(r)>=.05:
   a,b,_=closest(r);a,b=sorted((a,b));v=r["all_pairwise_bearings"][f"{a}-to-{b}"];return out(p,{"closest_pair":f"{a}-{b}","bearing_degrees_nearest_10":near(v,10)%360},[a,b],{"bearing_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
  if farthest_gap_ratio(r)>=.05:
   distances=r["all_pairwise_distances"];pair=max(distances,key=distances.get);a,b=sorted(pair.split("-"));v=r["all_pairwise_bearings"][f"{a}-to-{b}"];return out(COMPASS_FARTHEST,{"farthest_pair":f"{a}-{b}","bearing_degrees_nearest_10":near(v,10)%360},[a,b],{"bearing_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
  v=r["all_pairwise_bearings"]["A-to-B"];return out(COMPASS_NAMED_AB,{"bearing_degrees_nearest_10":near(v,10)%360},["A","B"],{"bearing_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
 if n=="coordinate_geometry_dataset_3000":
  if farthest_gap(r)<1:
   points={label:list(r["points"][label]) for label in sorted(r["points"])};return out(COORDINATE_FALLBACK,{"point_coordinates":points},sorted(points))
  d=r["all_pairwise_distances"];m=max(d.values());pair=min(k for k,v in d.items() if abs(v-m)<1e-9);return out(p,{"farthest_pair":pair,"distance_nearest_unit":near(m,1),"relation_to_12":"greater" if m>12 else "less"},pair.split("-"),{"distance_nearest_unit":{"absolute_tolerance":1,"unit":"grid units"}})
 if n=="cube_net_dataset_3000":
  t=pick(r,sorted(r["net_edge_neighbors"]),"face");q="Look at the labelled squares and the edges they share while the net lies flat: name the faces that touch face {TARGET} along a fold edge, then fold the net in your mind and name the face that ends up directly opposite {TARGET} on the finished cube. State your conclusion, justify it by describing the fold you followed and why a square touching only at a corner does not count, and end with a confidence score from 0 to 1.".replace("{TARGET}",t);o=next(b if a==t else a for a,b in r["opposite_pairs"] if t in (a,b));return out(q,{"flat_edge_neighbours":sorted(r["net_edge_neighbors"][t]),"opposite_face":o},[t])
 if n=="cube_structure_dataset_3000":
  cubes={(c["x"],c["y"],c["z"]) for c in r["cubes"]};visible=lambda c:not any((c[0]+k,c[1]+k,c[2]+k) in cubes for k in range(1,12));tops=sum(visible(c) and (c[0],c[1],c[2]+1) not in cubes for c in cubes);return out(p,{"visible_top_face_count":tops,"hidden_cube_count":r["hidden_cube_count"]},["visible top faces","concealed cubes"],{k:{"absolute_tolerance":0,"unit":"count"} for k in ("visible_top_face_count","hidden_cube_count")})
 if n=="depth_height_dataset_3000":
  if r["scene_type"]=="depth_ordering":return out(DEPTH_ORDERING,{"depth_ordering":r["depth_ordering"]},["coloured objects"])
  return out(STACK_HEIGHT,{"height_ordering_shortest_to_tallest":list(reversed(r["height_ordering"]))},["coloured stacks"])
 if n=="embedded_figures_dataset_3000":return out(p,{"candidate":r["correct_answer_choice"]},["complex figure","candidate panel"])
 if n=="fbd_dataset_3000":
  s=r["shown_forces"];groups=[sorted(x["arrow_label"] for x in s if abs(x["magnitude"]-m)<1e-9) for m in sorted({x["magnitude"] for x in s},reverse=True)];return out(p,{"drawn_magnitude_ranking":groups},["drawn force arrows"])
 if n=="fold_punch_dataset_3000":return out(p,{"correct_pattern":r["correct_answer_choice"]},["fold sequence","candidate panel"])
 if n=="gauge_reading_dataset_3000":return out(p,{"rounded_tick_value":r["rounded_tick_value"],"range_half":"lower" if r["needle_value"]<(r["min_value"]+r["max_value"])/2 else "upper"},["needle","scale"],{"rounded_tick_value":{"absolute_tolerance":r["tick_interval"]/2,"unit":r["unit"]}})
 if n=="gear_train_dataset_3000":
  fast=max(r["computed_rotation"],key=lambda x:r["computed_rotation"][x]["rpm"]);labels=sorted(x["label"] for x in r["gears"] if x["label"]!=r["driver_label"]);relations={x:"same" if r["computed_rotation"][x]["direction"]==r["driver_direction"] else "opposite" for x in labels};desired="same" if r["seed"]%2==0 else "opposite";choices=[x for x in labels if relations[x]==desired];target=pick(r,choices or labels,"direction-target");q=GEAR_TEMPLATE.replace("{TARGET}",target);return out(q,{"fastest_gear":fast,"direction_target":target,"target_direction_relation":relations[target]},[r["driver_label"],target])
 if n=="hex_pathfinding_dataset_3000":
  tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]};q,s=r["home_coordinate"];a=[(w,tiles.get((q+dq,s+ds))) for w,(dq,ds) in HEX];holes=[w for w,c in a if c=="grey"];prompt="Look closely at the green HOME hex and everything that immediately surrounds it: name the position of every grey hole touching it using these six direction names only: upper-left, upper-right, left, right, lower-left, lower-right. State your conclusion, justify it by describing exactly what you see around HOME, and end with a confidence score from 0 to 1.";return out(prompt,{"hole_directions":holes},["HOME"])
 if n=="impossible_object_dataset_3000":return out(p,{"crossing_count":r["num_crossings"],"constructible":"yes" if r["mode"]=="possible" else "no"},["beams","crossings"],{"crossing_count":{"absolute_tolerance":1,"unit":"crossing"}})
 if n=="laser_mirror_dataset_3000":
  if r["num_reflections"]==0:return out(LASER_STRAIGHT,{"exit_edge":r["exit_edge"],"exit_position":r["exit_position"],"near_miss_mirror_count":laser_near_misses(r)},["straight laser path","nearby mirrors"],{"exit_position":{"absolute_tolerance":0,"unit":"grid position"},"near_miss_mirror_count":{"absolute_tolerance":0,"unit":"count"}})
  return out(p,{"reflection_count":r["num_reflections"],"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]},["laser path"],{"reflection_count":{"absolute_tolerance":0,"unit":"count"},"exit_position":{"absolute_tolerance":0,"unit":"grid position"}})
 if n=="line_intersection_dataset_3000":return out(p,{"crossing_count":r["total_intersections"],"left_edge_higher_colour":"red" if r["red_above_blue_at_start"] else "blue"},["red polyline","blue polyline"],{"crossing_count":{"absolute_tolerance":0,"unit":"count"}})
 if n.startswith("nested_"):
  k=n.split("_dataset_")[0].removeprefix("nested_");m={"triangles":120,"squares":90,"hexagons":60}[k];q="Work outward from the innermost shape to the outermost: count how many shapes are nested inside one another, decide whether each step shrinks by roughly the same factor or by a changing one, and estimate through how many degrees the innermost shape has been turned relative to the outermost, giving a value from 0 to {MODULUS} degrees to the nearest 10. State your conclusion, justify it by describing how you matched corresponding corners between the innermost and outermost shapes, and end with a confidence score from 0 to 1.".replace("{MODULUS}",str(m));return out(q,{"shape_count":r[f"num_{k}"],"shrink_pattern":r["factor_progression_direction"],"rotation_degrees_nearest_10":near(r["cumulative_rotation_degrees"],10)},[f"nested {k}"],{"shape_count":{"absolute_tolerance":0,"unit":"count"},"rotation_degrees_nearest_10":{"absolute_tolerance":10,"unit":"degrees"}})
 if n=="occluded_pattern_dataset_3000":return out(p,{"pattern_type":r["pattern_type"],"hidden_object_count":r["occluded_object_count"]},["visible objects","occluder"],{"hidden_object_count":{"absolute_tolerance":0,"unit":"count"}})
 if n=="optical_illusion_dataset_3000":
  true="equal" if r["are_actually_equal"] else ("A" if r["element_a_true_value"]>r["element_b_true_value"] else "B");return out(p,{"true_size_relation":true,"perceived_larger":r["illusion_appears_larger_element"]},["A","B"])
 if n=="orthographic_dataset_3000":return out(p,{"minimum_cube_count":r["minimum_possible_cube_count"],"uniqueness":"unique" if r["is_uniquely_determined"] else "not unique"},["top","front","side"],{"minimum_cube_count":{"absolute_tolerance":0,"unit":"count"}})
 if n=="overlap_circles_dataset_3000":return out(p,{"circle_count":r["total_circle_count"],"above_average_radius_count":r["above_average_radius_count"]},["all circles"],{k:{"absolute_tolerance":0,"unit":"count"} for k in ("circle_count","above_average_radius_count")})
 if n=="physical_stability_dataset_3000":return out(p,{"stability_conclusion":{"status":"stable" if r["is_stable"] else "tips","lowest_failing_joint":r["tipping_joint"] if r["tipping_joint"] is not None else "none"}},["block stack"])
 if n=="polyhedron_dataset_3000":return out(p,{"face_shapes":r["face_shape_types"],"convexity":"convex" if r["is_convex"] else "non-convex"},["solid"])
 if n=="projectile_motion_dataset_1000":return out(p,{"peak_horizontal_distance_m_nearest_1":near(r["horizontal_position_at_peak_m"],1),"peak_above_13_m":"yes" if r["max_height_m"]>13 else "no"},["trajectory","printed launch values"],{"peak_horizontal_distance_m_nearest_1":{"absolute_tolerance":2,"unit":"metres"}})
 if n=="rotation_matching_dataset_3000":return out(p,{"rotation_candidate":r["correct_answer_choice"],"reflection_candidate":r["reflection_answer_choice"]},["reference","candidates"])
 if n=="route_dataset_3000":
  d={x:sum(x in (z["start"],z["end"]) for z in r["routes"]) for x in r["endpoint_letters"]};c=[x for x in r["endpoint_letters"] if d[x] in (2,3)] or [x for x in r["endpoint_letters"] if d[x]>0];t=pick(r,c,"route-target");inc=[z for z in r["routes"] if t in (z["start"],z["end"])];ends=[z["end"] if z["start"]==t else z["start"] for z in inc];un=sorted(set(r["endpoint_letters"])-{t}-set(ends));pt=next(z["points"][0] if z["start"]==t else z["points"][-1] for z in inc);w,h=r["canvas_size"];pos="at the top" if pt[1]<h/4 else ("at the bottom" if pt[1]>3*h/4 else ("at the left" if pt[0]<w/4 else "at the right"));q=ROUTE_TEMPLATE.replace("{TARGET}",t).replace("{POSITION}",pos);return out(q,{"connectivity":{"connected_to_all_other_labels":"yes" if not un else "no","far_end_labels":ends,"unreached_labels":un}},[t])
 if n=="rpm_dataset_3000":return out(p,{"correct_choice":r["correct_answer_index"],"attributes_changed_together":sorted((x["attribute"] for x in r["active_rules"]),key=("shape","size","color","rotation","count").index)},["matrix","numbered choices"])
 if n=="shadow_inference_dataset_3000":
  v=r["light_azimuth_degrees"];direction=["north","east","south","west"][int((v+45)%360//90)];return out(p,{"light_direction":direction,"light_height":"high" if r["light_elevation_degrees"]>=45 else "low"},["objects","shadows"])
 if n=="surface_topology_dataset_3000":return out(p,{"genus":r["genus"],"orientability":"orientable" if r["is_orientable"] else "non-orientable"},["surface"],{"genus":{"absolute_tolerance":0,"unit":"count"}})
 if n=="symmetry_pattern_dataset_3000":return out(p,{"pattern_status":"broken" if r["is_broken"] else "fully symmetric","symmetry_type":r["symmetry_type"]},["whole pattern"])
 raise KeyError(n)

DATASETS=sorted([*P,"cube_net_dataset_3000","hex_pathfinding_dataset_3000","nested_hexagons_dataset_3000","nested_squares_dataset_3000","nested_triangles_dataset_3000","route_dataset_3000"])
DERIVERS={n:(lambda r,name=n:derive(name,r)) for n in DATASETS}
def records(f):return [json.loads(x) for x in (f/"annotations.jsonl").read_text(encoding="utf-8-sig").splitlines() if x]
def write_csv(p,cols,rows):
 with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=cols,lineterminator="\n",extrasaction="ignore");w.writeheader();w.writerows(rows)
def build_domain(f):
 public=[];answers=[];annotations=[];fields=[];ex=Counter()
 for r in records(f):
  skip,reason=excluded(f.name,r)
  if skip:ex[reason]+=1;continue
  x=derive(f.name,r);qid=f"{r['id']}_open_q1";image=Path(r["image_path"]).name;pub={"question_id":qid,"image":image,"prompt":x["prompt"]};public.append(pub)
  for k in x["facts"]:
   if k not in fields:fields.append(k)
  answers.append({"question_id":qid,"image":image,"acceptance_set":compact(x["acceptance_set"]),"tolerances":compact(x["tolerances"]),"targets":compact(x["targets"]),**{k:compact(v) if isinstance(v,(list,dict)) else v for k,v in x["facts"].items()}})
  annotations.append({**pub,**x["facts"],"acceptance_set":x["acceptance_set"],"tolerances":x["tolerances"],"targets":x["targets"],"dataset_version":r.get("dataset_version"),"derivation":x["derivation"],"scoring":{"partial_credit_fields":list(x["facts"]),"confidence_range":[0,1]}})
 write_csv(f/"open_questions.csv",PUBLIC_COLUMNS,public);write_csv(f/"open_answer_key.csv",COMMON_PRIVATE+fields,answers)
 with (f/"open_annotations.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for x in annotations:h.write(compact(x)+"\n")
 return len(public),dict(ex),fields
def main():
 a=argparse.ArgumentParser();a.add_argument("--domain",action="append");z=a.parse_args();report={}
 report_path=ROOT/"open_question_build_report.json"
 if z.domain and report_path.is_file():report=json.loads(report_path.read_text(encoding="utf-8"))
 for n in z.domain or DATASETS:
  count,ex,fields=build_domain(ROOT/n);report[n]={"included":count,"excluded":sum(ex.values()),"exclusion_reasons":ex,"subfacts":fields};print(f"{n}: {count} included, {sum(ex.values())} excluded")
 report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()
