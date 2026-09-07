"""Build one supplementary, metadata-derived open question for every remaining domain."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXCLUDED = {"route_dataset_3000", "hex_pathfinding_dataset_3000"}
PUBLIC_COLUMNS = ["question_id", "image", "prompt"]
COMMON_PRIVATE = ["question_id", "image", "acceptance_set", "targets"]
CONFIDENCE = " End with a confidence score from 0 to 1."


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fmt(value, digits=2):
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    return str(round(float(value), digits))


def seeded_index(record, count, salt="open"):
    digest = hashlib.sha256(f"{record['id']}:{record.get('seed')}:{salt}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % count


def position_name(x, y, width, height):
    vertical = "top" if y < height / 3 else ("bottom" if y > 2 * height / 3 else "middle")
    horizontal = "left" if x < width / 3 else ("right" if x > 2 * width / 3 else "centre")
    return f"{vertical}-{horizontal}"


def acceptance(facts):
    return ["; ".join(f"{key}={value}" for key, value in facts.items())]


def result(prompt, facts, targets, derivation, acceptance_set=None):
    return {
        "prompt": prompt + CONFIDENCE,
        "facts": facts,
        "targets": targets,
        "acceptance_set": acceptance_set or acceptance(facts),
        "derivation": derivation,
    }


def derive_angle(r):
    scene = r["scene_type"]
    if scene == "single":
        a = r["angle_degrees"]
        facts = {"scene_form": "one marked angle", "primary_label": "marked angle", "primary_measure_degrees": round(a), "secondary_label": "none", "secondary_measure_degrees": "none", "comparison_summary": r["marked_sweep"]}
        start = "the marked arc"
        request_clause = "classify the marked sweep as minor or reflex, give its rounded measure, and use the marked-angle label as the primary result"
    elif scene == "comparison":
        vals = [r["angle_1_degrees"], r["angle_2_degrees"]]
        wider="Angle 1" if vals[0] > vals[1] else "Angle 2"; narrower="Angle 2" if wider=="Angle 1" else "Angle 1"
        facts = {"scene_form": "two labelled angles", "primary_label": wider, "primary_measure_degrees": round(max(vals)), "secondary_label": narrower, "secondary_measure_degrees": round(min(vals)), "comparison_summary": f"wider-to-narrower ratio {fmt(max(vals)/min(vals),2)}"}
        start = "the printed label Angle 1"
        request_clause = "name the wider and narrower labels, give both rounded measures, and report the wider-to-narrower ratio to two decimals"
    else:
        vals = r["interior_angles_degrees"]
        facts = {"scene_form": "labelled triangle", "primary_label": r["largest_angle_vertex"], "primary_measure_degrees": round(max(vals)), "secondary_label": r["smallest_angle_vertex"], "secondary_measure_degrees": round(min(vals)), "comparison_summary": f"middle vertex {next(k for k in 'ABC' if k not in {r['largest_angle_vertex'],r['smallest_angle_vertex']})}"}
        start = "the printed vertex A"
        request_clause = "name the largest and smallest-angle vertices with their rounded measures and identify the remaining middle-angle vertex"
    prompt = f"Start at {start} and inspect the whole angular construction: identify the scene form, then {request_clause}. Justify the result by explaining how you followed the rays or triangle sides and overcame the misleading effect of orientation and unequal ray lengths. Use only labels printed in the image and degrees for measures."
    return result(prompt, facts, [start], {"scene_type": scene, "source_values": vals if scene != "single" else [a]})


def derive_clock(r):
    h, m = r["hour"], r["minute"]
    minute_ticks = m
    hour_past = (m / 60) * 5
    nearer = "hour hand" if min(r["hour_angle"] % 360, 360 - r["hour_angle"] % 360) < min(r["minute_angle"] % 360, 360 - r["minute_angle"] % 360) else "minute hand"
    facts = {"read_time": r["time"], "minute_hand_ticks_from_12": minute_ticks, "hour_hand_ticks_past_hour": fmt(hour_past, 2), "nearer_to_12": nearer, "smaller_separation_degrees": fmt(r["angle_between_hands"], 1)}
    prompt = "Start at the printed 12 and trace both hands from the centre: read the time, count the minute-hand tick displacement from 12, estimate how far the hour hand has advanced beyond its numbered hour in five-minute tick units, identify which hand tip is nearer to 12, and give their smaller angular separation. Justify how the tick marks resolved the misleading hand lengths and near-alignment."
    return result(prompt, facts, ["12"], {"hour_angle": r["hour_angle"], "minute_angle": r["minute_angle"]})


def derive_combination(r, is3d):
    invalid = [c for c in r["candidates"] if not c["is_valid_assembly"]]
    c = invalid[seeded_index(r, len(invalid), "invalid-candidate")]
    key = "total_cube_count" if is3d else "total_cell_count"
    target = r["target_cube_count"] if is3d else r["target_cell_count"]
    counts = [len(piece) for piece in c["pieces"]]
    reason_words = {"gap_or_overlap": "gap or overlap", "wrong_count": "wrong cube count", "wrong_area": "wrong cell count", "requires_3d_tumble": "requires a forbidden 3D tumble", "requires_reflection": "requires a reflection"}
    facts = {"candidate": c["choice_label"], "piece_counts": counts, "candidate_total": c[key], "target_total": target, "blocking_reason": reason_words[c["failure_reason"]]}
    noun = "cubes" if is3d else "cells"
    difficulty = "occluded cube faces and the drawn vertical z direction" if is3d else "rotated outlines and apparent near-fits"
    prompt = f"Start at candidate {c['choice_label']} and compare each of its separated pieces with the target: count the {noun} in every piece, combine those counts, decide whether the pieces can reproduce the target under the rotations allowed by the drawing, and name the single blocking reason using only: gap or overlap, wrong {noun[:-1]} count, " + ("requires a forbidden 3D tumble" if is3d else "requires a reflection") + f". Justify the verdict by describing the fit and how you overcame {difficulty}."
    return result(prompt, facts, [c["choice_label"]], {"candidate": c, "target_count": target})


def derive_compass(r):
    labels = sorted(r["landmarks"])
    target = labels[seeded_index(r, len(labels), "landmark")]
    pairs = [(b, r["all_pairwise_distances"]["-".join(sorted((target,b)))], r["all_pairwise_bearings"][f"{target}-to-{b}"]) for b in labels if b != target]
    mind, maxd = min(x[1] for x in pairs), max(x[1] for x in pairs)
    nearest, farthest = sorted(x[0] for x in pairs if abs(x[1]-mind)<1e-8), sorted(x[0] for x in pairs if abs(x[1]-maxd)<1e-8)
    bearing = next(x[2] for x in pairs if x[0] == nearest[0])
    sectors = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
    sector = sectors[int((bearing + 22.5)//45)%8]
    facts = {"target": target, "nearest_labels": nearest, "nearest_distance": fmt(mind, 2), "farthest_labels": farthest, "farthest_distance": fmt(maxd, 2), "bearing_to_first_nearest": sector}
    prompt = f"Start at landmark {target} and compare every straight-line displacement to the other printed landmarks: name all nearest and all farthest landmarks, give both distances to two decimals, and classify the direction from {target} to the alphabetically first nearest landmark using only north, north-east, east, south-east, south, south-west, west, or north-west. Justify the comparison using the compass rose and explain how you resisted judging distance from horizontal or vertical separation alone."
    return result(prompt, facts, [target], {"pair_values": pairs})


def derive_coordinate(r):
    labels = sorted(r["points"])
    target = labels[seeded_index(r, len(labels), "point")]
    pairs = [(b, r["all_pairwise_distances"]["-".join(sorted((target,b)))]) for b in labels if b != target]
    mind, maxd = min(v for _,v in pairs), max(v for _,v in pairs)
    facts = {"target": target, "target_coordinates": r["points"][target], "nearest_labels": sorted(k for k,v in pairs if abs(v-mind)<1e-8), "nearest_distance": fmt(mind,2), "farthest_labels": sorted(k for k,v in pairs if abs(v-maxd)<1e-8), "farthest_distance": fmt(maxd,2)}
    prompt = f"Start at point {target} on the printed coordinate grid, read its ordered pair, then compare its displacement to every other labelled point and name all nearest and all farthest points with the corresponding Euclidean distances to two decimals. Justify using horizontal and vertical grid differences and explain how you avoided the misleading visual shortcut of judging only one axis."
    return result(prompt, facts, [target], {"points": r["points"], "distances_from_target": pairs})


def derive_cube_net(r):
    labels = sorted(r["net_edge_neighbors"])
    preferred = [x for x in labels if len(r["net_edge_neighbors"][x]) in (2,3)] or labels
    target = preferred[seeded_index(r, len(preferred), "face")]
    opposite = next(b if a == target else a for a,b in r["opposite_pairs"] if target in (a,b))
    facts = {"target_face": target, "flat_net_neighbours": sorted(r["net_edge_neighbors"][target]), "opposite_after_folding": opposite, "adjacent_after_folding": sorted(r["cube_adjacent_faces"][target])}
    prompt = f"Start at face {target} in the labelled net and work outward across shared edges: list its edge-neighbours while flat, then mentally fold the net and name its opposite face and all four faces adjacent to it on the cube. Justify the fold path and explain how you avoided treating a corner touch or a distant flat square as a folded edge contact."
    return result(prompt, facts, [target], {"net": r["net_edge_neighbors"], "folded": r["cube_adjacent_faces"]})


def derive_cube_structure(r):
    columns = Counter((c["x"], c["y"]) for c in r["cubes"])
    hist = Counter(columns.values())
    facts = {"visible_vertical_columns": len(columns), "height_histogram": {str(k): hist[k] for k in sorted(hist)}, "tallest_column_height": max(columns.values()), "cube_total_from_columns": sum(columns.values())}
    prompt = "Start at the visibly tallest vertical stack and scan the structure column by column in the renderer's drawn vertical z direction: report how many occupied columns there are, give a histogram stating how many columns have each height, identify the tallest height, and sum the histogram to recover the cube total. Justify how you separated stacked cubes from cubes merely offset in depth despite occluded faces. Use z as the vertical axis."
    return result(prompt, facts, ["visibly tallest vertical stack"], {"column_heights": sorted(columns.values())})


def derive_depth(r):
    width, height = r["canvas_size"]
    if r["scene_type"] == "stack_height":
        stacks=sorted(r["stacks"],key=lambda o:o["position_x"])
        target=stacks[seeded_index(r,len(stacks),"visible-object")]
        heights=[o["block_count"] for o in stacks]; rank=1+sorted(heights,reverse=True).index(target["block_count"])
        facts={"target_color":target["color"],"target_shape":"block stack","target_position":"left" if target is stacks[0] else ("right" if target is stacks[-1] else "middle"),"height_units":target["block_count"],"height_rank_tallest_first":rank,"tallest_colors":sorted(o["color"] for o in stacks if o["block_count"]==max(heights))}
        prompt=f"Start at the {target['color']} stack and compare it with every other coloured stack: identify its plain-language image position, count its blocks, rank it from tallest to shortest, and name every colour tied for tallest. Justify from the visible block boundaries and how you overcame overlap and unequal base placement rather than relying on overall pixel height."
        return result(prompt,facts,[target["color"]],{"scene_type":r["scene_type"],"stacks":stacks})
    objects = r["objects"]
    ordered = sorted(objects, key=lambda o:o["canvas_position"][0])
    target = ordered[seeded_index(r, len(ordered), "visible-object")]
    if r["scene_type"] == "depth_ordering":
        rank = r["depth_ordering"].index(target["color"])+1
        facts = {"target_color": target["color"], "target_shape": target["shape_type"], "target_position": position_name(*target["canvas_position"], width, height), "depth_rank_nearest_first": rank, "rendered_size": fmt(target["rendered_size"],1), "nearest_color": r["closest_object_color"], "farthest_color": r["farthest_object_color"]}
        action = "rank it from nearest to farthest and report the nearest and farthest colours"
        visual = "perspective size and vertical-position cues"
    prompt = f"Start at the {target['color']} element and compare it with every other coloured element: identify its shape and plain-language image position, {action}. Justify which visible cues support the ordering and how you overcame {visual} rather than relying on a single cue."
    return result(prompt, facts, [target["color"]], {"scene_type": r["scene_type"], "objects": objects})


def derive_embedded(r):
    invalid = [c for c in r["candidate_choices"] if not c["is_correct"]]
    c = invalid[seeded_index(r,len(invalid),"candidate")]
    signature=f"{c['description']}; side difference {c['side_count']-len(r['target_vertices']):+d}"
    facts = {"candidate": c["label"], "target_sides": len(r["target_vertices"]), "candidate_sides": c["side_count"], "side_difference": c["side_count"]-len(r["target_vertices"]), "mismatch_signature": signature}
    prompt = f"Start at candidate {c['label']} and compare its complete outline with the shape hidden in the dense line drawing: report the side count of each, their signed side-count difference, decide whether they are the same shape up to rotation and scale, and name the mismatch. Justify by tracing a closed boundary through the clutter and explaining how you separated target edges from crossing distractor segments."
    return result(prompt, facts, [c["label"]], {"candidate":c,"target_vertices":r["target_vertices"]})


def direction8(deg):
    names=["right","upper-right","up","upper-left","left","lower-left","down","lower-right"]
    return names[int(((360-deg)%360+22.5)//45)%8]


def math_direction8(deg):
    names=["right","upper-right","up","upper-left","left","lower-left","down","lower-right"]
    return names[int(((deg%360)+22.5)//45)%8]


def derive_fbd(r):
    shown=r["shown_forces"]
    f=shown[seeded_index(r,len(shown),"shown-arrow")]
    mags=sorted({x["magnitude"] for x in shown},reverse=True)
    same=sorted(x["arrow_label"] for x in shown if abs(((x["direction_degrees"]-f["direction_degrees"]+180)%360)-180)<1e-8)
    facts={"target_arrow":f["arrow_label"],"force_type_as_drawn":f["type"],"direction_as_drawn":math_direction8(f["direction_degrees"]),"magnitude_rank_largest_first":mags.index(f["magnitude"])+1,"same_direction_arrow_labels":same,"shown_arrow_count":len(shown)}
    prompt=f"Treat only the diagram as drawn, including any deliberately incorrect arrows, and start at arrow {f['arrow_label']}: identify its displayed force type, classify its arrow direction using only up, upper-right, right, lower-right, down, lower-left, left, or upper-left, rank its drawn magnitude from largest to smallest with ties sharing a rank, and list every arrow label drawn in the same direction. Justify from the arrowheads and relative lengths, explaining how you kept the drawn frame separate from the physically correct scenario."
    return result(prompt,facts,[f["arrow_label"]],{"shown_forces":shown,"physical_frame_not_used":True})


def derive_fold(r):
    axes=[x["axis"] for x in r["fold_sequence"]]
    directions=[x["direction"] for x in r["fold_sequence"]]
    xs={round(x,6) for x,_ in r["unfolded_hole_positions"]}; ys={round(y,6) for _,y in r["unfolded_hole_positions"]}
    facts={"fold_directions":directions,"horizontal_folds":axes.count("horizontal"),"vertical_folds":axes.count("vertical"),"unfolded_holes":len(r["unfolded_hole_positions"]),"distinct_hole_columns":len(xs),"distinct_hole_rows":len(ys)}
    prompt="Start at the punched hole in the final folded panel and read the fold arrows backward: state the fold directions in displayed order, count horizontal and vertical folds, then predict the number of holes after full unfolding and how many distinct rows and columns those holes occupy. Justify each reflection and explain how you kept overlapping fold layers separate. Use only horizontal, vertical, left over right, right over left, top over bottom, and bottom over top."
    return result(prompt,facts,["punched hole"],{"fold_sequence":r["fold_sequence"],"unfolded_holes":r["unfolded_hole_positions"]})


def derive_gauge(r):
    v,step=r["needle_value"],r["tick_interval"]
    lower=math.floor((v-r["min_value"])/step)*step+r["min_value"]
    upper=min(lower+step,r["max_value"])
    frac=0 if upper==lower else (v-lower)/(upper-lower)
    facts={"instrument":r["instrument_type"],"unit":r["unit"],"lower_bracketing_tick":fmt(lower),"upper_bracketing_tick":fmt(upper),"fraction_from_lower_tick":fmt(frac,2),"exact_needle_value":fmt(v,2)}
    prompt="Start at the needle tip and locate the two labelled scale ticks that bracket it: name the instrument and unit, give both bracketing values, state the fraction of that interval traversed from the lower tick to two decimals, and use that interpolation to report the exact reading. Justify from the minor ticks and explain how you avoided snapping the needle to the visually nearest labelled mark."
    return result(prompt,facts,["needle tip"],{"min":r["min_value"],"max":r["max_value"],"tick_interval":step,"needle_value":v})


def graph_dist(edges,start):
    adj=defaultdict(list)
    for a,b in edges: adj[a].append(b);adj[b].append(a)
    q=deque([(start,[start])]);seen={start}
    while q:
        node,path=q.popleft()
        yield node,path
        for nxt in sorted(adj[node]):
            if nxt not in seen:seen.add(nxt);q.append((nxt,path+[nxt]))


def derive_gear(r):
    paths=list(graph_dist(r["mesh_edges"],r["driver_label"]))
    preferred=[x for x in paths if len(x[1]) in (3,4)] or [x for x in paths if x[0]!=r["driver_label"]]
    target,path=preferred[seeded_index(r,len(preferred),"gear")]
    gear=next(x for x in r["gears"] if x["label"]==target); rot=r["computed_rotation"][target]
    facts={"target_gear":target,"mesh_path":path,"target_teeth":gear["tooth_count"],"target_direction":rot["direction"],"target_rpm":fmt(rot["rpm"],2)}
    prompt=f"Start at the arrowed driver gear {r['driver_label']} and trace tooth contacts to gear {target}: list the printed gear labels along the shortest mesh path, count the contacts, read the target tooth count, and derive its rotation direction and speed in rpm. Justify every direction reversal and tooth-ratio step, explaining how touching outlines and unequal gear sizes can mislead the eye. Use only CW or CCW for direction."
    return result(prompt,facts,[r["driver_label"],target],{"path":path,"computed_rotation":r["computed_rotation"]})


def derive_impossible(r):
    crossings=r["crossings"]
    choices=[x for x in crossings if x["crossing_id"]!=r.get("reference_crossing_id")] or crossings
    x=choices[seeded_index(r,len(choices),"crossing")]
    facts={"crossing":x["crossing_id"],"crossing_beams":sorted([x["beam_a"],x["beam_b"]]),"front_beam":x["front_beam"],"back_beam":x["back_beam"],"total_crossings":len(crossings),"front_beam_wins":sum(y["front_beam"]==x["front_beam"] for y in crossings)}
    prompt=f"Start at printed crossing {x['crossing_id']} and trace both labelled beams through the full drawing: name the two beams there, state which is in front and which is behind, count all printed crossings, and count how many crossings place that same front beam in front. Justify using the visible interruptions at overlaps and explain how you kept local over-under cues attached to the correct long beam."
    return result(prompt,facts,[x["crossing_id"]],{"selected_crossing":x,"crossings":crossings})


def derive_laser(r):
    hits=[]
    mirror_by_cell={tuple(x["cell"]):x for x in r["mirrors"]}
    for cell in r["path_cells"]:
        if tuple(cell) in mirror_by_cell: hits.append(mirror_by_cell[tuple(cell)])
    facts={"entry_edge":r["entry_edge"],"entry_position":r["entry_position"],"mirrors_hit_in_order":[x["cell_label"] for x in hits],"mirror_orientations":[x["orientation"] for x in hits],"reflection_count":len(hits),"exit_edge":r["exit_edge"],"exit_position":r["exit_position"]}
    prompt="Start where the laser enters the labelled grid and trace the beam cell by cell: state the entry edge and numbered position, list every printed mirror-cell label hit in order with its slash orientation, count reflections, and give the final exit edge and numbered position. Justify each change of direction and explain how you distinguished mirrors crossed by the beam from nearby unused mirrors. Use top, right, bottom, or left and / or \\ for orientations."
    return result(prompt,facts,[f"{r['entry_edge']} {r['entry_position']}"],{"path_cells":r["path_cells"],"hit_mirrors":hits})


def derive_line(r):
    crossings=r["intersections"]
    transition="red changes from above to below" if r["red_above_blue_at_start"] and not r["red_above_blue_at_end"] else ("red changes from below to above" if not r["red_above_blue_at_start"] and r["red_above_blue_at_end"] else "the start and end order is the same")
    facts={"red_at_left":"above" if r["red_above_blue_at_start"] else "below","red_at_right":"above" if r["red_above_blue_at_end"] else "below","total_crossings":len(crossings),"order_transition":transition,"red_segments_with_crossings":len({x["red_segment_index"] for x in crossings}),"blue_segments_with_crossings":len({x["blue_segment_index"] for x in crossings})}
    prompt="Start at the left endpoints of the red and blue polylines and follow both to the right: state whether red begins above or below blue and where it ends, count their mutual crossings, describe the resulting order transition, and count how many red segments and blue segments participate in at least one crossing. Justify by tracing through every bend and explain how you excluded self-bends and near touches. Use only above or below for endpoint order."
    return result(prompt,facts,["left red and blue endpoints"],{"intersections":crossings})


def derive_nested(r,name):
    shapes=r[name]
    outer,inner=shapes[0],shapes[-1]
    deltas=[((b["rotation_angle"]-a["rotation_angle"]+180)%360)-180 for a,b in zip(shapes,shapes[1:])]
    ratios=[b["side_length"]/a["side_length"] for a,b in zip(shapes,shapes[1:])]
    facts={"shape_count":len(shapes),"outer_to_inner_size_ratio":fmt(outer["side_length"]/inner["side_length"],2),"clockwise_steps":sum(d>1e-6 for d in deltas),"counterclockwise_steps":sum(d<-1e-6 for d in deltas),"largest_shrink_step":1+max(range(len(ratios)),key=lambda i:1-ratios[i])}
    singular=name[:-1]
    prompt=f"Start at the outermost {singular} and work inward one outline at a time: count the outlines, compare outer and inner side length as a ratio to two decimals, count clockwise and counterclockwise rotation steps, and identify the numbered outer-to-inner transition with the largest proportional shrink. Justify by following adjacent corners through the nesting and explain how centre drift and changing gaps can imitate rotation or scale change. Number transitions from 1 at the outside."
    return result(prompt,facts,[f"outermost {singular}"],{"rotation_deltas":deltas,"adjacent_size_ratios":ratios})


def derive_occluded(r):
    facts={"pattern_type":r["pattern_type"],"repeated_shape":r["shape_type"],"visible_count":r["visible_object_count"],"hidden_count":r["occluded_object_count"],"completed_total":r["total_object_count"],"occluder_style":r["occluder_style"]}
    prompt="Start at the coloured repeated element nearest the occluder edge and reconstruct the full arrangement: name the pattern type and repeated shape, count visible elements, infer the hidden count and completed total, and identify the occluder style. Justify the continuation from spacing and alignment on both sides and explain how you separated genuinely hidden elements from empty pattern positions."
    return result(prompt,facts,["coloured element nearest the occluder edge"],{"pattern_params":r["pattern_params"],"object_positions":r["object_positions"]})


def derive_optical(r):
    a,b=r["element_a_true_value"],r["element_b_true_value"]
    relation="equal" if a==b else ("A larger" if a>b else "B larger")
    facts={"illusion_type":r["illusion_type"],"element_A_true_value":fmt(a,2),"element_B_true_value":fmt(b,2),"true_relation":relation,"absolute_difference":fmt(abs(a-b),2),"percent_difference":fmt(r["percent_difference"],2)}
    prompt="Start at the central measurable element labelled A and compare only its actual endpoint-to-endpoint geometry with B: report both true lengths or diameters, their true relation using only A larger, B larger, or equal, the absolute difference, and the stated percent difference. Justify from the matching endpoints or circle boundaries and explain how you ignored the surrounding illusion context that biases apparent size."
    return result(prompt,facts,["A","B"],{"construction":r["construction"],"definition":r["percent_difference_definition"]})


def derive_orthographic(r):
    counts=r["view_filled_counts"]; mx=max(counts.values())
    facts={"top_filled":counts["top"],"front_filled":counts["front"],"side_filled":counts["side"],"largest_views":sorted(k for k,v in counts.items() if v==mx),"cube_total":r["total_cube_count"]}
    prompt="Start at the panel labelled TOP and compare it with FRONT and SIDE: count filled cells in each view, name every view tied for the largest silhouette, then reconcile the three silhouettes with the pictured solid to give the cube total. Justify the reconciliation and explain how you avoided counting the same vertical-z stack once in every projection. Use z as vertical."
    return result(prompt,facts,["TOP","FRONT","SIDE"],{"view_filled_counts":counts,"target_cubes":r["target_cubes"]})


def derive_overlap(r):
    idx=r["largest_circle_index"]
    degree=sum(idx in (x["circle_i"],x["circle_j"]) for x in r["pairwise_overlaps"])
    facts={"direct_overlap_degree":degree,"total_overlap_pairs":r["total_overlapping_pairs"],"above_average_radius_count":r["above_average_radius_count"],"circles_isolated_after_removal":r["isolated_after_largest_removal"],"three_plus_overlap_percent":fmt(r["three_plus_overlap_percent"],2)}
    prompt="Start at the visibly largest circle and trace every boundary it crosses: count how many circles overlap it directly, count all overlapping pairs in the scene, count circles whose radii are above the scene average, predict how many become isolated if the largest circle is removed, and report the percentage of the canvas covered by three or more circles. Justify how you distinguished pairwise crossings from deeper stacks and tangent-looking near misses."
    return result(prompt,facts,["largest circle"],{"largest_circle_index":idx,"overlap_pairs":r["pairwise_overlaps"]})


def derive_physical(r):
    joints=r["per_joint_stability"]
    unstable=[x for x in joints if not x["is_stable_at_this_joint"]]
    if unstable: joint=unstable[0]
    else:
        def margin(x):
            lo,hi=x["supporting_base_range"]; c=x["combined_com_x"]; return min(c-lo,hi-c)
        joint=min(joints,key=margin)
    lo,hi=joint["supporting_base_range"]; c=joint["combined_com_x"]
    relation="inside" if lo<=c<=hi else ("left" if c<lo else "right")
    facts={"supporting_block":joint["block_below"],"upper_block":joint["upper_block"],"blocks_above":joint["blocks_above"],"combined_com_relation":relation,"joint_stable":joint["is_stable_at_this_joint"],"whole_stack_stable":r["is_stable"]}
    prompt=f"Start at the contact supporting block {joint['upper_block']} and consider that block together with every labelled block above it: list those labels, locate their combined centre of mass relative to the supporting base using only left, inside, or right, decide whether this joint is stable, and then conclude whether the whole stack is stable. Justify from visible block widths and offsets, explaining how a dramatic single-block overhang can mislead compared with the combined mass."
    return result(prompt,facts,[joint["upper_block"]],{"selected_joint":joint})


def derive_polyhedron(r):
    face_sizes=Counter(len(x) for x in r["faces"])
    facts={"solid_name":r["solid_name"],"vertices":len(r["vertices"]),"edges":len(r["edges"]),"faces":len(r["faces"]),"face_size_histogram":{str(k):v for k,v in sorted(face_sizes.items())}}
    prompt="Start at one clearly visible polygonal face and trace shared edges around the entire solid: identify the solid, report its vertex, edge, and face totals, and give a histogram of faces by number of sides. Justify how hidden rear elements were inferred from repeated symmetry, reconcile the counts with the closed mesh, and explain how you avoided treating projected line crossings as vertices."
    return result(prompt,facts,["one clearly visible face"],{"stored_counts":[r["vertex_count"],r["edge_count"],r["face_count"]],"face_sizes":dict(face_sizes)})


def derive_projectile(r):
    vx,vy=r["initial_velocity_x_m_s"],r["initial_velocity_y_m_s"]
    facts={"launch_speed_m_s":fmt(r["initial_speed_m_s"]),"launch_angle_degrees":fmt(r["launch_angle_degrees"]),"horizontal_component_m_s":fmt(vx,2),"vertical_component_m_s":fmt(vy,2),"larger_component":"horizontal" if vx>vy else ("vertical" if vy>vx else "equal"),"time_to_peak_s":fmt(vy/r["gravity_m_s2"],2)}
    prompt="Start at the launch arrow and read its displayed speed and angle: resolve it into horizontal and vertical velocity components, identify the larger component using only horizontal, vertical, or equal, and derive the time to the trajectory peak to two decimals. Justify with the arrow direction and trajectory shape, explaining how the stretched plot axes can mislead visual estimates of angle and component size."
    return result(prompt,facts,["launch arrow"],{"speed":r["initial_speed_m_s"],"angle":r["launch_angle_degrees"],"gravity":r["gravity_m_s2"]})


def derive_rotation(r):
    cands=r["candidates"]
    pool=[c for c in cands if c["transformation_type"] in ({"reflection"} if seeded_index(r,2,"kind")==0 else {"wrong_angle_rotation"})] or cands
    c=pool[seeded_index(r,len(pool),"candidate")]
    angle=c["applied_angle"]%360
    kind="reflection" if c["transformation_type"]=="reflection" else "rotation"
    facts={"candidate":c["choice_label"],"transformation_type":kind,"clockwise_degrees":fmt(angle) if kind=="rotation" else "not applicable","counterclockwise_equivalent_degrees":fmt((360-angle)%360) if kind=="rotation" else "not applicable"}
    prompt=f"Start at candidate {c['choice_label']} and match distinctive corners back to the reference polygon: decide whether it is a rotation or reflection, and if it is a rotation report both its clockwise angle and equivalent counterclockwise angle; then state whether rotation alone makes it match. Justify by tracking vertex order and explain how near-symmetry and page orientation can disguise a reflection. Use only rotation or reflection."
    return result(prompt,facts,[c["choice_label"]],{"candidate":c})


COLOR_NAMES={"#246EB9":"blue","#7040A0":"purple","#B23A2E":"red","#C65D00":"orange","#8A6800":"olive","#147A68":"teal"}
def derive_rpm(r):
    missing=next(x for x in r["grid_panels"] if not x["shown_in_image"])
    a=missing["attributes"]
    facts={"shape":a["shape"],"color":COLOR_NAMES.get(a["color"],a["color"]),"count":a["count"],"size":a["size"],"rotation_degrees":a["rotation"]}
    prompt="Start at the empty bottom-right panel and scan complete rows and columns of the matrix: infer the missing shape, colour, count, size, and rotation in degrees. Justify each attribute from its own repeating or progressing rule and explain how answer choices that violate only one attribute can look convincing. Use only star, circle, triangle, square, hexagon, or pentagon for shape; blue, purple, red, orange, olive, or teal for colour; and small, medium, or large for size."
    return result(prompt,facts,["empty bottom-right panel"],{"active_rules":r["active_rules"],"missing_attributes":a})


def derive_shadow(r):
    objs=r["objects"]; target=max(objs,key=lambda x:(x["height_px"],x["color"])); longest=max(x["shadow_length"] for x in objs)
    facts={"target_color":target["color"],"target_type":target["type"],"target_shadow_direction":direction8(target["shadow_screen_angle_degrees"]),"target_shadow_length":fmt(target["shadow_length"],1),"longest_shadow_colors":sorted(x["color"] for x in objs if abs(x["shadow_length"]-longest)<1e-8)}
    prompt=f"Start at the tallest visible object, the {target['color']} one, and compare all objects and their ground shadows: identify its object type, classify its shadow direction using only up, upper-right, right, lower-right, down, lower-left, left, or upper-left, give its shadow length to one decimal, and name every colour tied for the longest shadow. Justify by matching each shadow to its base and explain how perspective and overlapping silhouettes can mislead height and length comparisons."
    return result(prompt,facts,[target["color"]],{"objects":objs})


def derive_surface(r):
    orientation="orientable" if r["is_orientable"] else "non-orientable"
    signature=f"{orientation} genus {r['genus']} with {r['boundary_count']} boundary loops"
    family_names={"sphere_handles":"sphere with handles","polyhedral_mesh":"polyhedral mesh","mobius_vs_cylinder":"Möbius-or-cylinder","klein_vs_torus":"Klein-or-torus"}
    facts={"surface_type":family_names[r["surface_type"]],"handle_or_crosscap_genus":r["genus"],"euler_characteristic":r["euler_characteristic"],"topological_signature":signature}
    prompt="Start at the most prominent hole or twist in the rendered surface and inspect the whole connected sheet: identify its family using only sphere with handles, polyhedral mesh, Möbius-or-cylinder, or Klein-or-torus; count its handles or crosscaps; derive the Euler characteristic; and give the signature in the exact form 'orientable genus N with B boundary loops' or 'non-orientable genus N with B boundary loops'. Justify how you followed the surface through occlusion and distinguished a true handle, crosscap, or boundary opening from one caused only by viewing angle."
    return result(prompt,facts,["most prominent hole or twist"],{"genus_kind":r["genus_kind"],"surface_variant":r["surface_variant"]})


def derive_symmetry(r):
    symmetry_names={"rotational_2":"2-fold rotation","rotational_3":"3-fold rotation","rotational_4":"4-fold rotation","rotational_6":"6-fold rotation","mirror_horizontal":"horizontal mirror","mirror_vertical":"vertical mirror","mirror_both":"horizontal and vertical mirrors"}
    if r["is_broken"]:
        facts={"symmetry_type":symmetry_names[r["symmetry_type"]],"orbit_count":len({x["orbit_id"] for x in r["shapes"]}),"partnered_shape_count":r["symmetric_partner_count"],"pattern_status":"broken","break_location":r["broken_location"],"break_type":r["break_type"]}
    else:
        facts={"symmetry_type":symmetry_names[r["symmetry_type"]],"orbit_count":len({x["orbit_id"] for x in r["shapes"]}),"partnered_shape_count":r["symmetric_partner_count"],"pattern_status":"intact","break_location":"none","break_type":"none"}
    prompt="Start at the topmost shape and pair every visible shape under the pattern's symmetry: name the symmetry using only 2-fold rotation, 3-fold rotation, 4-fold rotation, 6-fold rotation, horizontal mirror, vertical mirror, or horizontal and vertical mirrors; count the symmetry orbits and partnered shapes; decide whether the pattern is intact or broken; and if broken name the defect location and type. Justify by following partners around the centre or across the axis and explain how rotation, fill, and small size differences can hide the mismatch. Use intact or broken; top-left, top-right, bottom-left, bottom-right, center, or none for location; and fill, rotation, position, size, or none for type."
    return result(prompt,facts,["topmost shape"],{"shapes":r["shapes"],"broken_shape_index":r["broken_shape_index"]})


DERIVERS={
    "angle_estimation_dataset_3000":derive_angle,
    "clock_reading_dataset_3000":derive_clock,
    "combination3d_dataset_3000":lambda r:derive_combination(r,True),
    "combination_dataset_3000":lambda r:derive_combination(r,False),
    "compass_bearing_dataset_3000":derive_compass,
    "coordinate_geometry_dataset_3000":derive_coordinate,
    "cube_net_dataset_3000":derive_cube_net,
    "cube_structure_dataset_3000":derive_cube_structure,
    "depth_height_dataset_3000":derive_depth,
    "embedded_figures_dataset_3000":derive_embedded,
    "fbd_dataset_3000":derive_fbd,
    "fold_punch_dataset_3000":derive_fold,
    "gauge_reading_dataset_3000":derive_gauge,
    "gear_train_dataset_3000":derive_gear,
    "impossible_object_dataset_3000":derive_impossible,
    "laser_mirror_dataset_3000":derive_laser,
    "line_intersection_dataset_3000":derive_line,
    "nested_hexagons_dataset_3000":lambda r:derive_nested(r,"hexagons"),
    "nested_squares_dataset_3000":lambda r:derive_nested(r,"squares"),
    "nested_triangles_dataset_3000":lambda r:derive_nested(r,"triangles"),
    "occluded_pattern_dataset_3000":derive_occluded,
    "optical_illusion_dataset_3000":derive_optical,
    "orthographic_dataset_3000":derive_orthographic,
    "overlap_circles_dataset_3000":derive_overlap,
    "physical_stability_dataset_3000":derive_physical,
    "polyhedron_dataset_3000":derive_polyhedron,
    "projectile_motion_dataset_1000":derive_projectile,
    "rotation_matching_dataset_3000":derive_rotation,
    "rpm_dataset_3000":derive_rpm,
    "shadow_inference_dataset_3000":derive_shadow,
    "surface_topology_dataset_3000":derive_surface,
    "symmetry_pattern_dataset_3000":derive_symmetry,
}


def read_records(folder):
    with (folder/"annotations.jsonl").open(encoding="utf-8-sig") as h:
        return [json.loads(line) for line in h if line.strip()]


def write_csv(path, columns, rows):
    with path.open("w",encoding="utf-8-sig",newline="") as h:
        w=csv.DictWriter(h,fieldnames=columns,lineterminator="\n",extrasaction="ignore");w.writeheader();w.writerows(rows)


def build_domain(folder):
    records=read_records(folder); derive=DERIVERS[folder.name]
    public=[]; answers=[]; annotations=[]; fact_columns=[]
    for r in records:
        out=derive(r); qid=f"{r['id']}_open_q1"; image=Path(r["image_path"]).name
        p={"question_id":qid,"image":image,"prompt":out["prompt"]}; public.append(p)
        for key in out["facts"]:
            if key not in fact_columns: fact_columns.append(key)
        a={"question_id":qid,"image":image,"acceptance_set":compact(out["acceptance_set"]),"targets":compact(out["targets"]),**{k:(compact(v) if isinstance(v,(list,dict)) else v) for k,v in out["facts"].items()}}
        answers.append(a)
        annotations.append({**p,**out["facts"],"acceptance_set":out["acceptance_set"],"targets":out["targets"],"dataset_version":r.get("dataset_version"),"derivation":out["derivation"],"scoring":{"partial_credit_fields":list(out["facts"]),"confidence_range":[0,1]}})
    expected=int(folder.name.rsplit("_",1)[1]);
    if len(records)!=expected: raise RuntimeError(f"{folder.name}: expected {expected}, found {len(records)}")
    write_csv(folder/"open_questions.csv",PUBLIC_COLUMNS,public)
    write_csv(folder/"open_answer_key.csv",COMMON_PRIVATE+fact_columns,answers)
    with (folder/"open_annotations.jsonl").open("w",encoding="utf-8",newline="\n") as h:
        for row in annotations:h.write(compact(row)+"\n")
    return len(records),fact_columns


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--domain",action="append");args=parser.parse_args()
    names=args.domain or sorted(DERIVERS)
    for name in names:
        count,fields=build_domain(ROOT/name);print(f"{name}: {count} rows; {len(fields)} sub-facts")


if __name__=="__main__":main()
