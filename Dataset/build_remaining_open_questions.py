"""Build one concise open-ended visual question per image for all 34 domains."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
COMMON_PRIVATE = ["question_id", "image", "acceptance_set", "targets", "tolerances"]
CONFIDENCE = " Explain briefly what you used in the image, then end with a confidence score from 0 to 1."


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def seeded_index(record, count, salt="open"):
    digest = hashlib.sha256(f"{record['id']}:{record.get('seed')}:{salt}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % count


def nearest(value, step):
    return int(math.floor(float(value) / step + 0.5 + 1e-9) * step)


def acceptance(facts):
    return ["; ".join(f"{key}={compact(value) if isinstance(value, (list, dict)) else value}" for key, value in facts.items())]


def result(prompt, facts, targets, derivation, tolerances=None):
    return {"prompt": prompt + CONFIDENCE, "facts": facts, "targets": targets,
            "tolerances": tolerances or {}, "acceptance_set": acceptance(facts), "derivation": derivation}


def angle_class(value):
    if value < 90: return "acute"
    if value == 90: return "right"
    if value < 180: return "obtuse"
    return "reflex"


def derive_angle(r):
    if r["scene_type"] == "single":
        label, value = "marked angle", r["angle_degrees"]
    elif r["scene_type"] == "comparison":
        index = seeded_index(r, 2, "angle"); label, value = f"Angle {index + 1}", r[f"angle_{index + 1}_degrees"]
    else:
        index = seeded_index(r, 3, "angle"); label, value = "ABC"[index], r["interior_angles_degrees"][index]
    facts = {"angle_degrees_nearest_5": nearest(value, 5), "angle_class": angle_class(value)}
    prompt = f"Look at {label}. Estimate its measure to the nearest 5 degrees, and classify it as acute, right, obtuse, or reflex."
    return result(prompt, facts, [label], {"source_angle_degrees": value},
                  {"angle_degrees_nearest_5": {"absolute_tolerance": 2.5, "unit": "degrees"}})


def derive_clock(r):
    facts = {"time": r["time"], "smaller_angle_degrees_nearest_5": nearest(r["angle_between_hands"], 5)}
    return result("Read the time on the clock, then estimate the smaller angle between the hands to the nearest 5 degrees.",
                  facts, ["clock hands"], {"hour": r["hour"], "minute": r["minute"], "angle": r["angle_between_hands"]},
                  {"smaller_angle_degrees_nearest_5": {"absolute_tolerance": 2.5, "unit": "degrees"}})


def derive_combination(r, is3d):
    invalid = [c for c in r["candidates"] if not c["is_valid_assembly"]]
    candidate = invalid[seeded_index(r, len(invalid), "invalid-candidate")]
    words = {"gap_or_overlap": "gap or overlap", "wrong_count": "wrong cube count", "wrong_area": "wrong cell count",
             "requires_3d_tumble": "requires a forbidden 3D tumble", "requires_reflection": "requires a reflection"}
    noun = "cube" if is3d else "cell"
    choices = f"gap or overlap, wrong {noun} count, " + ("or requires a forbidden 3D tumble" if is3d else "or requires a reflection")
    facts = {"blocking_reason": words[candidate["failure_reason"]]}
    prompt = f"Candidate {candidate['choice_label']} does not make the target using the allowed moves. Choose its single blocking reason from: {choices}."
    return result(prompt, facts, [candidate["choice_label"]], {"candidate": candidate})


def bearing_word(value):
    names = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
    return names[int((value + 22.5) // 45) % 8]


def derive_compass(r):
    labels = sorted(r["landmarks"]); target = labels[seeded_index(r, len(labels), "landmark")]
    pairs = [(x, r["all_pairwise_distances"]["-".join(sorted((target, x)))], r["all_pairwise_bearings"][f"{target}-to-{x}"]) for x in labels if x != target]
    low, high = min(x[1] for x in pairs), max(x[1] for x in pairs)
    nearest_labels = sorted(x[0] for x in pairs if abs(x[1] - low) < 1e-8)
    bearing = next(x[2] for x in pairs if x[0] == nearest_labels[0])
    facts = {"nearest_landmarks": nearest_labels, "farthest_landmarks": sorted(x[0] for x in pairs if abs(x[1] - high) < 1e-8),
             "direction_to_first_nearest": bearing_word(bearing)}
    prompt = f"From landmark {target}, name the nearest and farthest landmarks. Then give the direction to the alphabetically first nearest landmark using one of eight equal 45-degree sectors centred on north, north-east, east, south-east, south, south-west, west, and north-west."
    return result(prompt, facts, [target], {"pair_values": pairs, "sector_boundaries_degrees": [22.5,67.5,112.5,157.5,202.5,247.5,292.5,337.5]})


def derive_coordinate(r):
    labels = sorted(r["points"]); target = labels[seeded_index(r, len(labels), "point")]
    pairs = [(x, r["all_pairwise_distances"]["-".join(sorted((target, x)))]) for x in labels if x != target]
    low, high = min(x[1] for x in pairs), max(x[1] for x in pairs)
    facts = {"target_coordinates": r["points"][target], "nearest_points": sorted(x for x,v in pairs if abs(v-low)<1e-8),
             "farthest_points": sorted(x for x,v in pairs if abs(v-high)<1e-8)}
    return result(f"Read the exact grid coordinates of point {target} (tolerance 0), then name the point or points nearest to it and the point or points farthest from it.", facts, [target], {"points": r["points"], "distances": pairs}, {"target_coordinates":{"absolute_tolerance":0,"unit":"grid unit per coordinate"}})


def derive_cube_net(r):
    labels = sorted(r["net_edge_neighbors"]); target = labels[seeded_index(r, len(labels), "face")]
    opposite = next(b if a == target else a for a,b in r["opposite_pairs"] if target in (a,b))
    facts = {"opposite_face": opposite, "flat_edge_neighbours": sorted(r["net_edge_neighbors"][target])}
    return result(f"For face {target}, name the face opposite it after folding and list the faces that share an edge with it while the net is still flat.", facts, [target], {"opposite_pairs": r["opposite_pairs"], "net_edge_neighbors": r["net_edge_neighbors"]})


def derive_cube_structure(r):
    columns = Counter((c["x"], c["y"]) for c in r["cubes"])
    facts = {"occupied_columns": len(columns), "tallest_column_height": max(columns.values())}
    return result("Count the occupied vertical columns and give the height of the tallest column. Give both counts exactly (tolerance 0).", facts, ["whole cube structure"], {"column_heights": sorted(columns.values())}, {k:{"absolute_tolerance":0,"unit":"count"} for k in facts})


def derive_depth(r):
    if r["scene_type"] == "stack_height":
        stacks = sorted(r["stacks"], key=lambda x:x["position_x"]); target = stacks[seeded_index(r,len(stacks),"stack")]
        maximum = max(x["block_count"] for x in stacks)
        facts = {"block_count": target["block_count"], "tallest_stack_colors": sorted(x["color"] for x in stacks if x["block_count"]==maximum)}
        return result(f"Count the blocks in the {target['color']} stack and name every colour tied for tallest. Give the block count exactly (tolerance 0).", facts, [target["color"]], {"stacks":stacks}, {"block_count":{"absolute_tolerance":0,"unit":"count"}})
    facts = {"nearest_object_color": r["closest_object_color"], "farthest_object_color": r["farthest_object_color"]}
    return result("Using the depth cues in the scene, name the nearest object colour and the farthest object colour.", facts, ["all coloured objects"], {"objects":r["objects"],"depth_ordering":r["depth_ordering"]})


def derive_embedded(r):
    facts = {"target_shape": r["target_shape_type"], "matching_candidate": r["correct_answer_choice"]}
    return result("Name the shape hidden in the line drawing, then give the letter of the candidate with the same outline under rotation and scaling.", facts, ["hidden outline","candidate panel"], {"target_edges":r["target_edges"],"candidate_choices":r["candidate_choices"]})


def math_direction8(value):
    names=["right","upper-right","up","upper-left","left","lower-left","down","lower-right"]
    return names[int(((360-value)%360+22.5)//45)%8]


def derive_fbd(r):
    shown=r["shown_forces"]; force=shown[seeded_index(r,len(shown),"shown-arrow")]; ranks=sorted({x["magnitude"] for x in shown},reverse=True)
    facts={"force_type_as_drawn":force["type"],"direction_as_drawn":math_direction8(force["direction_degrees"]),"magnitude_rank_largest_first":ranks.index(force["magnitude"])+1}
    prompt=f"For arrow {force['arrow_label']} in the diagram as drawn, name its force type, give its direction as up, upper-right, right, lower-right, down, lower-left, left, or upper-left, and give its exact rank by arrow length from largest to smallest (tolerance 0), with ties sharing a rank."
    return result(prompt,facts,[force["arrow_label"]],{"shown_forces":shown},{"magnitude_rank_largest_first":{"absolute_tolerance":0,"unit":"rank"}})


def derive_fold(r):
    facts={"fold_directions":[x["direction"] for x in r["fold_sequence"]],"unfolded_hole_count":len(r["unfolded_hole_positions"])}
    return result("State the fold directions in the order shown, then give the exact number of holes after the paper is fully unfolded (tolerance 0).",facts,["fold panels","punched hole"],{"fold_sequence":r["fold_sequence"],"unfolded_hole_positions":r["unfolded_hole_positions"]},{"unfolded_hole_count":{"absolute_tolerance":0,"unit":"count"}})


def derive_gauge(r):
    facts={"instrument":r["instrument_type"],"reading_nearest_tick":r["rounded_tick_value"]}
    return result(f"Name the instrument and read the needle to the nearest minor tick in {r['unit']}; answers within half a minor-tick interval are accepted.",facts,["needle","dial labels"],{"needle_value":r["needle_value"],"tick_interval":r["tick_interval"]},{"reading_nearest_tick":{"absolute_tolerance":r["tick_interval"]/2,"unit":r["unit"]}})


def graph_dist(edges,start):
    adjacency=defaultdict(list)
    for a,b in edges: adjacency[a].append(b);adjacency[b].append(a)
    queue,seen=deque([(start,[start])]),{start}
    while queue:
        node,path=queue.popleft();yield node,path
        for nxt in sorted(adjacency[node]):
            if nxt not in seen: seen.add(nxt);queue.append((nxt,path+[nxt]))


def derive_gear(r):
    paths=[x for x in graph_dist(r["mesh_edges"],r["driver_label"]) if x[0]!=r["driver_label"]];target,path=paths[seeded_index(r,len(paths),"gear")]
    rotation=r["computed_rotation"][target];facts={"rotation_direction":rotation["direction"],"speed_rpm_nearest_whole":nearest(rotation["rpm"],1)}
    return result(f"Trace the meshing gears from driver {r['driver_label']} to gear {target}. Give gear {target}'s rotation direction as CW or CCW and its speed to the nearest whole rpm.",facts,[r["driver_label"],target],{"mesh_path":path,"gears":r["gears"],"computed_rotation":r["computed_rotation"]},{"speed_rpm_nearest_whole":{"absolute_tolerance":0.5,"unit":"rpm"}})


HEX_DIRECTIONS=[("upper-left",(0,-1)),("upper-right",(1,-1)),("left",(-1,0)),("right",(1,0)),("lower-left",(-1,1)),("lower-right",(0,1))]
def derive_hex(r):
    tiles={tuple(x["coordinate"]):x["color"] for x in r["all_tiles"]};q,s=r["home_coordinate"]
    neighbours=[tiles[(q+dq,s+ds)] for _,(dq,ds) in HEX_DIRECTIONS if (q+dq,s+ds) in tiles]
    facts={"grey_holes_touching_home":sum(x=="grey" for x in neighbours),"walkable_hexes_touching_home":sum(x!="grey" for x in neighbours)}
    return result("Look at the hexes directly touching HOME. Count the grey holes and the walkable hexes separately; give both counts exactly (tolerance 0).",facts,["HOME"],{"home_coordinate":r["home_coordinate"],"neighbour_colours":neighbours},{k:{"absolute_tolerance":0,"unit":"count"} for k in facts})


def derive_impossible(r):
    crossings=r["crossings"]; crossing=crossings[seeded_index(r,len(crossings),"crossing")];facts={"front_beam":crossing["front_beam"],"total_crossings":len(crossings)}
    return result(f"At crossing {crossing['crossing_id']}, name the beam drawn in front, then count all labelled crossings exactly (tolerance 0).",facts,[crossing["crossing_id"]],{"selected_crossing":crossing,"crossings":crossings},{"total_crossings":{"absolute_tolerance":0,"unit":"count"}})


def derive_laser(r):
    mirrors={tuple(x["cell"]):x for x in r["mirrors"]};hits=[mirrors[tuple(cell)]["cell_label"] for cell in r["path_cells"] if tuple(cell) in mirrors]
    facts={"mirrors_hit_in_order":hits,"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]}
    return result("Trace the laser through the grid. List the printed mirror-cell labels it hits in order, then give its exit edge and exact numbered exit position (tolerance 0).",facts,[f"{r['entry_edge']} entry {r['entry_position']}"],{"path_cells":r["path_cells"],"mirrors":r["mirrors"]},{"exit_position":{"absolute_tolerance":0,"unit":"grid position"}})


def derive_line(r):
    facts={"red_at_left":"above" if r["red_above_blue_at_start"] else "below","red_at_right":"above" if r["red_above_blue_at_end"] else "below","total_crossings":r["total_intersections"]}
    return result("Follow the red and blue lines from left to right. Say whether red is above or below blue at each end, and count their crossings exactly (tolerance 0).",facts,["red and blue lines"],{"intersections":r["intersections"]},{"total_crossings":{"absolute_tolerance":0,"unit":"count"}})


def derive_nested(r,key):
    facts={"shape_count":r[f"num_{key}"],"cumulative_rotation_degrees_nearest_5":nearest(r["cumulative_rotation_degrees"],5),"shrink_pattern":r["factor_progression_direction"]};noun=key[:-1]
    prompt=f"Count the nested {key} exactly (tolerance 0), estimate the cumulative rotation from the outermost to the innermost {noun} to the nearest 5 degrees, and say whether the shrink factor is constant, increasing, or decreasing inward."
    return result(prompt,facts,[f"nested {key}"],{"shapes":r[key],"cumulative_rotation_degrees":r["cumulative_rotation_degrees"],"factor_progression_direction":r["factor_progression_direction"]},{"shape_count":{"absolute_tolerance":0,"unit":"count"},"cumulative_rotation_degrees_nearest_5":{"absolute_tolerance":2.5,"unit":"degrees"}})


def derive_occluded(r):
    facts={"pattern_type":r["pattern_type"],"visible_count":r["visible_object_count"],"hidden_count":r["occluded_object_count"]}
    return result("Name the repeated pattern, count the visible objects exactly, and infer the hidden objects exactly (tolerance 0 for both counts).",facts,["repeated objects","occluder"],{"pattern_params":r["pattern_params"],"object_positions":r["object_positions"]},{"visible_count":{"absolute_tolerance":0,"unit":"count"},"hidden_count":{"absolute_tolerance":0,"unit":"count"}})


def derive_optical(r):
    a,b=r["element_a_true_value"],r["element_b_true_value"];facts={"true_relation":"equal" if a==b else ("A larger" if a>b else "B larger")}
    return result("Compare the actual central elements A and B, ignoring apparent size. Answer A larger, B larger, or equal.",facts,["A","B"],{"element_a_true_value":a,"element_b_true_value":b})


def derive_orthographic(r):
    counts=r["view_filled_counts"];facts={"top_filled":counts["top"],"front_filled":counts["front"],"side_filled":counts["side"]}
    return result("Count the filled cells in the TOP, FRONT, and SIDE views. Give all three counts exactly (tolerance 0).",facts,["TOP","FRONT","SIDE"],{"view_cells":{"top":r["top_view_cells"],"front":r["front_view_cells"],"side":r["side_view_cells"]}},{k:{"absolute_tolerance":0,"unit":"count"} for k in facts})


def derive_overlap(r):
    largest=r["largest_circle_index"];degree=sum(largest in (x["circle_i"],x["circle_j"]) for x in r["pairwise_overlaps"])
    facts={"largest_circle_direct_overlaps":degree,"total_overlap_pairs":r["total_overlapping_pairs"],"isolated_after_largest_removal":r["isolated_after_largest_removal"]}
    return result("For the largest circle, count its direct overlaps, count all overlapping pairs, and say how many circles would be isolated if the largest were removed. Give all counts exactly (tolerance 0).",facts,["largest circle"],{"largest_circle_index":largest,"pairwise_overlaps":r["pairwise_overlaps"]},{k:{"absolute_tolerance":0,"unit":"count"} for k in facts})


def derive_physical(r):
    joints=r["per_joint_stability"];unstable=[x for x in joints if not x["is_stable_at_this_joint"]];joint=unstable[0] if unstable else joints[seeded_index(r,len(joints),"joint")]
    low,high=joint["supporting_base_range"];value=joint["combined_com_x"];relation="inside" if low<=value<=high else ("left" if value<low else "right")
    facts={"blocks_above_contact":joint["blocks_above"],"combined_centre_of_mass":relation}
    return result(f"At the contact below block {joint['upper_block']}, list the blocks above that contact and say whether their combined centre of mass lies left of, inside, or right of the supporting base.",facts,[joint["upper_block"]],{"selected_joint":joint})


def derive_polyhedron(r):
    facts={"solid_name":r["solid_name"],"face_count":r["face_count"],"face_shapes":r["face_shape_types"]}
    return result("Identify the solid, give its exact total number of faces (tolerance 0), and name the face shape or shapes.",facts,["polyhedron"],{"vertices":r["vertices"],"edges":r["edges"],"faces":r["faces"]},{"face_count":{"absolute_tolerance":0,"unit":"count"}})


def derive_projectile(r):
    facts={"maximum_height_m_nearest_whole":nearest(r["max_height_m"],1),"range_m_nearest_whole":nearest(r["range_m"],1)}
    return result("Read the plotted trajectory and estimate its maximum height and horizontal range to the nearest whole metre.",facts,["trajectory","plot axes"],{"max_height_m":r["max_height_m"],"range_m":r["range_m"]},{k:{"absolute_tolerance":0.5,"unit":"metres"} for k in facts})


def derive_rotation(r):
    facts={"matching_rotation_candidate":r["correct_answer_choice"],"reflection_candidate":r["reflection_answer_choice"]}
    return result("Name the candidate that is a true rotation of the reference and the candidate that is its reflection.",facts,["reference","candidate panel"],{"candidates":r["candidates"]})


def derive_route(r):
    degrees={x:sum(x in (route["start"],route["end"]) for route in r["routes"]) for x in r["endpoint_letters"]};preferred=[x for x in r["endpoint_letters"] if degrees[x] in (2,3)] or [x for x in r["endpoint_letters"] if degrees[x]>0]
    target=preferred[seeded_index(r,len(preferred),"route-target")];routes=[x for x in r["routes"] if target in (x["start"],x["end"])]
    far_ends=[{"color":x["color"],"label":x["end"] if x["start"]==target else x["start"]} for x in routes];facts={"far_ends_by_colour":far_ends,"total_bends":sum(x["num_bends"] for x in routes)}
    return result(f"Trace every coloured line touching label {target}. For each colour, name its far-end label, then give the exact total number of bends across those lines (tolerance 0).",facts,[target],{"incident_routes":routes},{"total_bends":{"absolute_tolerance":0,"unit":"count"}})


def derive_rpm(r):
    missing=next(x for x in r["grid_panels"] if not x["shown_in_image"])["attributes"];facts={"shape":missing["shape"],"count":missing["count"],"rotation_degrees":missing["rotation"]}
    return result("Complete the empty panel: name the shape, give the exact number of copies (tolerance 0), and give its rotation to the nearest 5 degrees.",facts,["empty panel"],{"active_rules":r["active_rules"],"missing_attributes":missing},{"count":{"absolute_tolerance":0,"unit":"count"},"rotation_degrees":{"absolute_tolerance":2.5,"unit":"degrees"}})


def screen_direction8(value):
    names=["right","upper-right","up","upper-left","left","lower-left","down","lower-right"]
    return names[int(((value%360)+22.5)//45)%8]


def derive_shadow(r):
    objects=r["objects"];target=max(objects,key=lambda x:(x["height_px"],x["color"]));longest=max(x["shadow_length"] for x in objects)
    facts={"tallest_object_type":target["type"],"its_shadow_direction":screen_direction8(target["shadow_screen_angle_degrees"]),"longest_shadow_colours":sorted(x["color"] for x in objects if abs(x["shadow_length"]-longest)<1e-8)}
    return result(f"For the tallest object, the {target['color']} one, name its object type and its shadow direction using eight compass-like screen directions. Then name every colour tied for the longest shadow.",facts,[target["color"]],{"objects":objects})


def derive_surface(r):
    names={"sphere_handles":"sphere with handles","polyhedral_mesh":"polyhedral mesh","mobius_vs_cylinder":"Möbius strip or cylinder","klein_vs_torus":"Klein bottle or torus"};facts={"surface_family":names[r["surface_type"]],"euler_characteristic":r["euler_characteristic"]}
    return result("Identify the surface family, then give its exact Euler characteristic (tolerance 0).",facts,["rendered surface"],{"surface_type":r["surface_type"],"genus":r["genus"],"boundary_count":r["boundary_count"],"is_orientable":r["is_orientable"]},{"euler_characteristic":{"absolute_tolerance":0,"unit":"integer"}})


def derive_symmetry(r):
    names={"rotational_2":"2-fold rotation","rotational_3":"3-fold rotation","rotational_4":"4-fold rotation","rotational_6":"6-fold rotation","mirror_horizontal":"horizontal mirror","mirror_vertical":"vertical mirror","mirror_both":"horizontal and vertical mirrors"};facts={"symmetry_type":names[r["symmetry_type"]],"pattern_status":"broken" if r["is_broken"] else "intact"}
    return result("Name the pattern's intended symmetry and say whether the visible pattern is intact or broken.",facts,["whole pattern"],{"shapes":r["shapes"],"is_broken":r["is_broken"]})


DERIVERS={
"angle_estimation_dataset_3000":derive_angle,"clock_reading_dataset_3000":derive_clock,
"combination3d_dataset_3000":lambda r:derive_combination(r,True),"combination_dataset_3000":lambda r:derive_combination(r,False),
"compass_bearing_dataset_3000":derive_compass,"coordinate_geometry_dataset_3000":derive_coordinate,
"cube_net_dataset_3000":derive_cube_net,"cube_structure_dataset_3000":derive_cube_structure,"depth_height_dataset_3000":derive_depth,
"embedded_figures_dataset_3000":derive_embedded,"fbd_dataset_3000":derive_fbd,"fold_punch_dataset_3000":derive_fold,
"gauge_reading_dataset_3000":derive_gauge,"gear_train_dataset_3000":derive_gear,"hex_pathfinding_dataset_3000":derive_hex,
"impossible_object_dataset_3000":derive_impossible,"laser_mirror_dataset_3000":derive_laser,"line_intersection_dataset_3000":derive_line,
"nested_hexagons_dataset_3000":lambda r:derive_nested(r,"hexagons"),"nested_squares_dataset_3000":lambda r:derive_nested(r,"squares"),"nested_triangles_dataset_3000":lambda r:derive_nested(r,"triangles"),
"occluded_pattern_dataset_3000":derive_occluded,"optical_illusion_dataset_3000":derive_optical,"orthographic_dataset_3000":derive_orthographic,
"overlap_circles_dataset_3000":derive_overlap,"physical_stability_dataset_3000":derive_physical,"polyhedron_dataset_3000":derive_polyhedron,
"projectile_motion_dataset_1000":derive_projectile,"rotation_matching_dataset_3000":derive_rotation,"route_dataset_3000":derive_route,
"rpm_dataset_3000":derive_rpm,"shadow_inference_dataset_3000":derive_shadow,"surface_topology_dataset_3000":derive_surface,"symmetry_pattern_dataset_3000":derive_symmetry}


def read_records(folder):
    with (folder/"annotations.jsonl").open(encoding="utf-8-sig") as handle: return [json.loads(line) for line in handle if line.strip()]


def write_csv(path,columns,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=columns,lineterminator="\n",extrasaction="ignore");writer.writeheader();writer.writerows(rows)


def build_domain(folder):
    records,derive=read_records(folder),DERIVERS[folder.name];public=[];answers=[];annotations=[];fact_columns=[]
    for record in records:
        out=derive(record);qid,image=f"{record['id']}_open_q1",Path(record["image_path"]).name
        public_row={"question_id":qid,"image":image,"prompt":out["prompt"]};public.append(public_row)
        for key in out["facts"]:
            if key not in fact_columns: fact_columns.append(key)
        answers.append({"question_id":qid,"image":image,"acceptance_set":compact(out["acceptance_set"]),"targets":compact(out["targets"]),"tolerances":compact(out["tolerances"]),**{k:compact(v) if isinstance(v,(list,dict)) else v for k,v in out["facts"].items()}})
        annotations.append({**public_row,**out["facts"],"acceptance_set":out["acceptance_set"],"targets":out["targets"],"tolerances":out["tolerances"],"dataset_version":record.get("dataset_version"),"derivation":out["derivation"],"scoring":{"partial_credit_fields":list(out["facts"]),"confidence_range":[0,1]}})
    expected=int(folder.name.rsplit("_",1)[1])
    if len(records)!=expected: raise RuntimeError(f"{folder.name}: expected {expected}, found {len(records)}")
    write_csv(folder/"open_questions.csv",PUBLIC_COLUMNS,public);write_csv(folder/"open_answer_key.csv",COMMON_PRIVATE+fact_columns,answers)
    with (folder/"open_annotations.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
        for row in annotations: handle.write(compact(row)+"\n")
    return len(records),fact_columns


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--domain",action="append");args=parser.parse_args()
    for name in args.domain or sorted(DERIVERS):
        count,fields=build_domain(ROOT/name);print(f"{name}: {count} rows; {len(fields)} sub-facts")


if __name__=="__main__": main()
