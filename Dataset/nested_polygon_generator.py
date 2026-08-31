"""Shared v8 generator engine for nested squares, triangles, and hexagons."""
from __future__ import annotations
import json,math,random
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw
import nested_polygon_common as common
BACKGROUND="#FDFAF4";CHARCOAL="#2C2C2A";ALT_PAIRS=(("#2C2C2A","#16697A"),("#263238","#8A4F7D"),("#30343F","#8A6D1D"));RENDER_SCALE=3;CONTRACTIONS=(1,.9,.82,.74,.66,.58,.5,.42,.34,.26,.18,.1,0)
def point_inside(point,polygon,tolerance=1e-7):
 px,py=point;signs=[]
 for i in range(len(polygon)):
  ax,ay=polygon[i];bx,by=polygon[(i+1)%len(polygon)];cross=(bx-ax)*(py-ay)-(by-ay)*(px-ax)
  if abs(cross)>tolerance:signs.append(cross>0)
 return not signs or all(value==signs[0] for value in signs)
def nested_without_crossing(shapes,vertex_fn):
 for i in range(len(shapes)-1):
  outer=vertex_fn(shapes[i]["center"],shapes[i]["side_length"],shapes[i]["rotation_angle"]);inner=vertex_fn(shapes[i+1]["center"],shapes[i+1]["side_length"],shapes[i+1]["rotation_angle"])
  if not all(point_inside(vertex,outer,1e-5) for vertex in inner):return False
 return True
def point_segment_distance(point,a,b):
 px,py=point;ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay;den=dx*dx+dy*dy
 if not den:return math.hypot(px-ax,py-ay)
 t=max(0.0,min(1.0,((px-ax)*dx+(py-ay)*dy)/den));return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
def adjacent_outline_clearances(shapes,vertex_fn,line_width):
 values=[]
 for i in range(len(shapes)-1):
  outer=vertex_fn(shapes[i]["center"],shapes[i]["side_length"],shapes[i]["rotation_angle"]);inner=vertex_fn(shapes[i+1]["center"],shapes[i+1]["side_length"],shapes[i+1]["rotation_angle"])
  centerline=min(point_segment_distance(vertex,outer[j],outer[(j+1)%len(outer)]) for vertex in inner for j in range(len(outer)))
  values.append(centerline-line_width)
 return values
def clearance_aware_rotation_sequence(base,sides,target,spec,vertex_fn,line_width,required_clearance):
 signed=float(target if target<=spec.modulus/2 else target-spec.modulus);needed=abs(signed)
 if not needed:return [base]*len(sides)
 capacities=[]
 for outer_side,inner_side in zip(sides,sides[1:]):
  lo,hi=0.0,spec.modulus/2
  for _ in range(28):
   mid=(lo+hi)/2;pair=[{"center":(0,0),"side_length":outer_side,"rotation_angle":0},{"center":(0,0),"side_length":inner_side,"rotation_angle":mid}]
   valid=nested_without_crossing(pair,vertex_fn) and adjacent_outline_clearances(pair,vertex_fn,line_width)[0]>=required_clearance
   if valid:lo=mid
   else:hi=mid
  capacities.append(lo*.995)
 if sum(capacities)+1e-6<needed:return None
 weights=[1+.30*math.sin((i+1)*1.731) for i in range(len(capacities))];increments=[0.0]*len(capacities);active=set(range(len(capacities)));remaining=needed
 while active:
  scale=remaining/sum(weights[i] for i in active);violators=[i for i in active if weights[i]*scale>capacities[i]]
  if not violators:
   for i in active:increments[i]=weights[i]*scale
   break
  for i in violators:increments[i]=capacities[i];remaining-=capacities[i];active.remove(i)
 sign=1 if signed>=0 else -1;angles=[base]
 for increment in increments:angles.append(angles[-1]+sign*increment)
 angles[-1]=base+signed
 return angles
def contained_on_canvas(shapes,size,vertex_fn,margin=20):
 w,h=size;return all(all(margin<=x<=w-margin and margin<=y<=h-margin for x,y in vertex_fn(shape["center"],shape["side_length"],shape["rotation_angle"])) for shape in shapes)
def structural_choices(index,spec):
 rank=common.reduction_rank(index,spec);rng=random.Random(spec.seed_namespace+7_000_000+rank);reduction=common.reduction_mode(index,spec);mode=common.choose_rotation_mode(index,spec);size_plan=common.size_axis_plan(spec)[rank];offset_requested=(rng.random()<.5 and spec.key!="triangle" and mode=="fixed" and size_plan["count"]<=8 and size_plan["band"]=="high");alternating=rng.random()<.3;thin=(spec.key=="triangle" or rng.random()<.2 or (size_plan["band"]=="low" and size_plan["count"]>=8))
 inner=size_plan["target_inner_fraction"]
 total_root=inner**(1/(size_plan["count"]-1))
 clearance_rng=random.Random(spec.seed_namespace+1_700_000+rank);clearance_target=clearance_rng.uniform(3.0001,3.0010)
 return {"count":size_plan["count"],"offset_requested":offset_requested,"mode":mode,"alternating":alternating,"thin":thin,"desired_yes":size_plan["target_level5"]=="yes","target_rotation":common.target_rotation(index,spec,mode),"reduction_mode":reduction,"factor_span":size_plan["factor_span"] if reduction=="changing" else 1.0,"factor_direction":size_plan["factor_direction"] if reduction=="changing" else "constant","paired_rank":rank,"size_band":size_plan["band"],"size_pair_rank":size_plan["pair_rank"],"total_root":total_root,"target_inner_fraction":inner,"matched_clearance_target_px":clearance_target}
def make_shapes(centers,sides,angles,colors,vertex_fn):return [{"index":i,"center":[round(center[0],4),round(center[1],4)],"side_length":round(side,4),"rotation_angle":round(angle,4),"stroke_color":colors[i%2],"vertices":[[round(x,4),round(y,4)] for x,y in vertex_fn(center,side,angle)]} for i,(center,side,angle) in enumerate(zip(centers,sides,angles))]
def match_clearance(shapes,target,size,vertex_fn,line_width,colors):
 """Add a tiny progressive center drift until minimum clearance hits target."""
 sides=[s["side_length"] for s in shapes];angles=[s["rotation_angle"] for s in shapes];base_centers=[tuple(s["center"]) for s in shapes];count=len(shapes)
 if min(adjacent_outline_clearances(shapes,vertex_fn,line_width))<target:return None
 best=None
 for step in range(4):
  phase=2*math.pi*step/4
  def candidate(amplitude):
   # Endpoints stay fixed; only intermediate centers move. This matches the
   # clearance nuisance distribution without creating an innermost-center cue.
   centers=[(c[0]+amplitude*math.sin(math.pi*i/(count-1))*math.cos(phase),c[1]+amplitude*math.sin(math.pi*i/(count-1))*math.sin(phase)) for i,c in enumerate(base_centers)]
   return make_shapes(centers,sides,angles,colors,vertex_fn)
  lo=0.0;hi=1.0;probe=candidate(hi)
  while hi<max(sides[0],100) and nested_without_crossing(probe,vertex_fn) and contained_on_canvas(probe,size,vertex_fn) and min(adjacent_outline_clearances(probe,vertex_fn,line_width))>target:
   lo=hi;hi*=1.6;probe=candidate(hi)
  if min(adjacent_outline_clearances(probe,vertex_fn,line_width))>target:continue
  for _ in range(22):
   mid=(lo+hi)/2;probe=candidate(mid);valid=nested_without_crossing(probe,vertex_fn) and contained_on_canvas(probe,size,vertex_fn);clear=min(adjacent_outline_clearances(probe,vertex_fn,line_width)) if valid else -1
   if valid and clear>target:lo=mid
   else:hi=mid
  probe=candidate(lo);clear=min(adjacent_outline_clearances(probe,vertex_fn,line_width))
  error=abs(clear-target)
  if best is None or error<best[0]:best=(error,probe)
  if error<.0005:break
 return best[1] if best and best[0]<.003 else None
def build_geometry(index,attempt,spec,vertex_fn,structure):
 parameter_seed=spec.seed_namespace+9_000_000+structure["paired_rank"]+attempt*10_000_019;rng=random.Random(parameter_seed);size=(rng.randint(580,600),rng.randint(580,600));w,h=size;count=structure["count"];thin_range=(.50,.70) if spec.key=="triangle" and count>=9 else (.75,1);line_width=round(rng.uniform(*thin_range) if structure["thin"] else rng.uniform(1.5,2),2);base=rng.uniform(-18,18);outer_center=(w/2+rng.uniform(-8,8),h/2+rng.uniform(-8,8));unit=vertex_fn((0,0),1,base);bounds=[]
 for ux,uy in unit:
  if ux>0:bounds.append((w-20-outer_center[0])/ux)
  if ux<0:bounds.append((outer_center[0]-20)/(-ux))
  if uy>0:bounds.append((h-20-outer_center[1])/uy)
  if uy<0:bounds.append((outer_center[1]-20)/(-uy))
 outer_range=(258,268) if spec.key=="hexagon" else ((500,505) if spec.key=="triangle" else (410,505));outer=min(min(bounds)-4,rng.uniform(*outer_range));total_root=structure["total_root"]
 if structure["reduction_mode"]=="constant":factors=[total_root]*(count-1)
 else:factors=common.changing_factors_for_total(total_root,structure["factor_span"],count,structure["factor_direction"])
 sides=[outer]
 for factor in factors:sides.append(sides[-1]*factor)
 sides[-1]=outer*(total_root**(count-1))
 colors=rng.choice(ALT_PAIRS) if structure["alternating"] else (CHARCOAL,CHARCOAL)
 angles=[base]*count if structure["mode"]=="fixed" else clearance_aware_rotation_sequence(base,sides,structure["target_rotation"],spec,vertex_fn,line_width,structure["matched_clearance_target_px"])
 if angles is None:return None,"containment"
 phase=rng.uniform(0,2*math.pi);target_drift=rng.uniform(.18,.28)*outer if structure["offset_requested"] else 0
 if structure["reduction_mode"]=="changing":
  clearance=[max(.001,1-factor) for factor in factors];total=sum(clearance);positions=[0];running=0
  for value in clearance:running+=value;positions.append(running/total)
 else:positions=[i/(count-1) for i in range(count)]
 phases=[phase] if not structure["offset_requested"] else [phase+step*math.pi/12 for step in range(12)];shapes=None;saw_contained=False;saw_gap_safe=False
 for candidate_phase in phases:
  raw_centers=[(outer_center[0]+target_drift*position*math.cos(candidate_phase),outer_center[1]+target_drift*position*math.sin(candidate_phase)) for position in positions]
  for contraction in CONTRACTIONS:
   centers=[(outer_center[0]+(center[0]-outer_center[0])*contraction,outer_center[1]+(center[1]-outer_center[1])*contraction) for center in raw_centers];candidate=make_shapes(centers,sides,angles,colors,vertex_fn)
   if nested_without_crossing(candidate,vertex_fn) and contained_on_canvas(candidate,size,vertex_fn):
    saw_contained=True
    if structure["offset_requested"] and not common.gap_value_is_safe(common.gap_separation(candidate,vertex_fn),spec):continue
    saw_gap_safe=True
    if min(adjacent_outline_clearances(candidate,vertex_fn,line_width))<structure["matched_clearance_target_px"]:continue
    matched=match_clearance(candidate,structure["matched_clearance_target_px"],size,vertex_fn,line_width,colors)
    if matched is None:continue
    if structure["offset_requested"] and not common.gap_value_is_safe(common.gap_separation(matched,vertex_fn),spec):continue
    shapes=matched;break
  if shapes is not None:break
 if shapes is None:return None,("minimum_outline_clearance" if saw_gap_safe else ("gap_margin" if saw_contained else "containment"))
 actual_factors=common.step_factors(shapes);clearances=adjacent_outline_clearances(shapes,vertex_fn,line_width);metadata={"center_drift":common.drift_label(shapes)=="offset","offset_requested_pre_containment":structure["offset_requested"],"rotation_mode":structure["mode"],"target_cumulative_rotation_degrees":int(structure["target_rotation"]),"reduction_mode":structure["reduction_mode"],"factor_progression_direction":structure["factor_direction"],"step_reduction_factors":[round(value,8) for value in actual_factors],"reduction_factor_span":max(actual_factors)/min(actual_factors),"extrapolation_reduction_factor":actual_factors[-1],"size_reduction_factor":actual_factors[-1],"sampled_total_reduction_root":total_root,"sampled_total_inner_fraction":total_root**(count-1),"size_axis_band":structure["size_band"],"size_axis_pair_rank":structure["size_pair_rank"],"color_alternation":structure["alternating"],"line_width_px":line_width,"matched_clearance_target_px":structure["matched_clearance_target_px"],"minimum_adjacent_clear_background_px":min(clearances),"parameter_seed":parameter_seed,"symmetry_modulus_degrees":spec.modulus,"drift_floor_applied_as_rejection":False,"paired_nuisance_rank":structure["paired_rank"]}
 return (size,shapes,metadata),None
def render(path,size,shapes,width,vertex_fn):
 w,h=size;image=Image.new("RGB",(w*RENDER_SCALE,h*RENDER_SCALE),BACKGROUND);draw=ImageDraw.Draw(image)
 for shape in shapes:
  points=[(round(x*RENDER_SCALE),round(y*RENDER_SCALE)) for x,y in vertex_fn(shape["center"],shape["side_length"],shape["rotation_angle"])];draw.line(points+[points[0]],fill=shape["stroke_color"],width=max(2,round(width*RENDER_SCALE)),joint="curve")
 image.resize((w,h),Image.Resampling.LANCZOS).save(path,"PNG")
def render_existing_dataset(output_dir,shape_field,vertex_fn):
 output=Path(output_dir);annotations=output/"annotations.jsonl";images=output/"images";images.mkdir(parents=True,exist_ok=True);rendered=0
 with annotations.open("r",encoding="utf-8") as handle:
  for line in handle:
   if not line.strip():continue
   record=json.loads(line);render(images/Path(record["image_path"]).name,tuple(record["canvas_size"]),record[shape_field],record["line_width_px"],vertex_fn);rendered+=1
   if rendered%100==0:print(f"Rendered existing {rendered}",flush=True)
 print(f"Rendered {rendered} accepted v8 images from {annotations}")
def generate_one(index,images,spec,shape_field,vertex_fn,render_image=True):
 structure=structural_choices(index,spec);rejections=Counter({"containment":0,"drift_floor":0,"gap_margin":0,"reduction_perceptibility":0,"rotation_wrap":0,"level5_margin":0,"minimum_inner_size":0,"minimum_outline_clearance":0});rejected=0;candidate_gaps=[];candidate_spans=[]
 for attempt in range(600):
  built,failure=build_geometry(index,attempt,spec,vertex_fn,structure)
  if built is None:rejections[failure]+=1;rejected+=1;continue
  size,shapes,metadata=built;violations=[]
  if structure["offset_requested"]:
   separation=common.gap_separation(shapes,vertex_fn);candidate_gaps.append(float(separation))
   if not common.gap_value_is_safe(separation,spec):violations.append("gap_margin")
  factors=common.step_factors(shapes);span=max(factors)/min(factors);candidate_spans.append(span) if structure["reduction_mode"]=="changing" else None
  if not common.reduction_factors_are_safe(factors,structure["reduction_mode"]):violations.append("reduction_perceptibility")
  delta=common.cumulative_rotation(shapes,spec)
  if not common.rotation_is_margin_safe(delta,metadata["rotation_mode"],spec) or delta!=structure["target_rotation"]:violations.append("rotation_wrap")
  if not common.level5_is_margin_safe(shapes):violations.append("level5_margin")
  if not common.inner_size_is_safe(shapes[-1]["side_length"]):violations.append("minimum_inner_size")
  if not common.outline_clearance_is_safe(metadata["minimum_adjacent_clear_background_px"]):violations.append("minimum_outline_clearance")
  if violations:rejections.update(violations);rejected+=1;continue
  break
 else:raise RuntimeError(f"no v8 safe {spec.singular} scene for {index}")
 iid=f"nested_{spec.plural}_{index:04d}";filename=iid+".png"
 if render_image:render(images/filename,size,shapes,metadata["line_width_px"],vertex_fn)
 delta=common.cumulative_rotation(shapes,spec);rotation_score={"fixed":0,"uniform_whole_nest":.5,"per_shape_independent":1}[metadata["rotation_mode"]];difficulty=round(min(1,.35*(len(shapes)-4)/8+.25*rotation_score+.1*metadata["center_drift"]),4);record={"id":iid,"dataset_version":spec.dataset_version,"image_path":"images/"+filename,"canvas_size":list(size),f"num_{spec.plural}":len(shapes),**metadata,"stroke_colors_used":sorted({shape["stroke_color"] for shape in shapes}),"seed":spec.seed_namespace+index,"source_index":index,"generation_attempt":attempt,"generation_rejections":dict(rejections),"rejected_candidates":rejected,"cumulative_rotation_degrees":int(delta) if delta.denominator==1 else float(delta),"cumulative_rotation_fraction":common.fraction_text(delta),shape_field:shapes,"difficulty_score":difficulty,"questions":common.build_questions(iid,shapes,spec)};return record,candidate_gaps,candidate_spans
def summary(values):
 values=sorted(values)
 if not values:return {"count":0,"min":None,"p25":None,"p50":None,"p75":None,"p95":None,"max":None}
 def at(p):return values[round((len(values)-1)*p)]
 return {"count":len(values),"min":at(0),"p25":at(.25),"p50":at(.5),"p75":at(.75),"p95":at(.95),"max":at(1)}
def pearson(xs,ys):
 mx=sum(xs)/len(xs);my=sum(ys)/len(ys);numerator=sum((x-mx)*(y-my) for x,y in zip(xs,ys));denominator=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys));return numerator/denominator if denominator else 0
def guard_injection_results(spec,vertex_fn):
 def shape(center,side):return {"center":center,"side_length":side,"rotation_angle":0}
 def gap_scene(offset):return [shape((0,0),1000),shape((offset,0),100)]
 lo,hi=0.0,400.0
 while common.gap_separation(gap_scene(hi),vertex_fn)<spec.gap_margin:hi*=1.25
 for _ in range(80):
  middle=(lo+hi)/2
  if common.gap_separation(gap_scene(middle),vertex_fn)>=spec.gap_margin:hi=middle
  else:lo=middle
 gap_violation=gap_scene(0);gap_boundary=gap_scene(hi);gap_violation_value=common.gap_separation(gap_violation,vertex_fn);gap_boundary_value=common.gap_separation(gap_boundary,vertex_fn)
 reduction_violation=[.6,.6*(float(common.CHANGING_FACTOR_SPAN_MIN)-.001)];reduction_boundary=[.6,.6*float(common.CHANGING_FACTOR_SPAN_MIN)]
 containment_boundary=[shape((0,0),100),shape((0,0),100)];containment_violation=[shape((0,0),100),shape((0,0),101)]
 result={
  "gap_margin":{"violating":{"metric":float(gap_violation_value),"accepted":common.gap_value_is_safe(gap_violation_value,spec)},"boundary":{"metric":float(gap_boundary_value),"accepted":common.gap_value_is_safe(gap_boundary_value,spec)}},
  "reduction_perceptibility":{"violating":{"metric":max(reduction_violation)/min(reduction_violation),"accepted":common.reduction_factors_are_safe(reduction_violation,"changing")},"boundary":{"metric":max(reduction_boundary)/min(reduction_boundary),"accepted":common.reduction_factors_are_safe(reduction_boundary,"changing")}},
  "level5_margin":{"violating":{"metric":float(common.LEVEL5_THRESHOLD),"accepted":common.level5_value_is_safe(common.LEVEL5_THRESHOLD)},"lower_boundary":{"metric":float(common.LEVEL5_LOWER_GUARD),"accepted":common.level5_value_is_safe(common.LEVEL5_LOWER_GUARD)},"upper_boundary":{"metric":float(common.LEVEL5_UPPER_GUARD),"accepted":common.level5_value_is_safe(common.LEVEL5_UPPER_GUARD)}},
  "containment":{"violating":{"inner_to_outer_side_ratio":1.01,"accepted":nested_without_crossing(containment_violation,vertex_fn)},"boundary":{"inner_to_outer_side_ratio":1.0,"accepted":nested_without_crossing(containment_boundary,vertex_fn)}},
  "minimum_inner_size":{"violating":{"metric_px":common.MIN_INNER_SIDE_PX-.01,"accepted":common.inner_size_is_safe(common.MIN_INNER_SIDE_PX-.01)},"boundary":{"metric_px":common.MIN_INNER_SIDE_PX,"accepted":common.inner_size_is_safe(common.MIN_INNER_SIDE_PX)}},
  "minimum_outline_clearance":{"violating":{"metric_px":common.MIN_CLEAR_BACKGROUND_PX-.01,"accepted":common.outline_clearance_is_safe(common.MIN_CLEAR_BACKGROUND_PX-.01)},"boundary":{"metric_px":common.MIN_CLEAR_BACKGROUND_PX,"accepted":common.outline_clearance_is_safe(common.MIN_CLEAR_BACKGROUND_PX)}}}
 result["pass"]=not result["gap_margin"]["violating"]["accepted"] and result["gap_margin"]["boundary"]["accepted"] and not result["reduction_perceptibility"]["violating"]["accepted"] and result["reduction_perceptibility"]["boundary"]["accepted"] and not result["level5_margin"]["violating"]["accepted"] and result["level5_margin"]["lower_boundary"]["accepted"] and result["level5_margin"]["upper_boundary"]["accepted"] and not result["containment"]["violating"]["accepted"] and result["containment"]["boundary"]["accepted"] and not result["minimum_inner_size"]["violating"]["accepted"] and result["minimum_inner_size"]["boundary"]["accepted"] and not result["minimum_outline_clearance"]["violating"]["accepted"] and result["minimum_outline_clearance"]["boundary"]["accepted"]
 return result
def generate_dataset(spec,shape_field,vertex_fn,generator_path,validator_path,count=3000,output_dir=None,start_index=1,render_images=True):
 output=Path(output_dir) if output_dir else Path(generator_path).resolve().parent;images=output/"images";images.mkdir(parents=True,exist_ok=True);totals=Counter();modes=Counter();mode_by_label=defaultdict(Counter);reductions=Counter();candidate_gaps=[];candidate_spans=[];accepted_spans=[];l4=[];counts=[];l5=[];rejected=0;sampled_numeric=defaultdict(list);sampled_categorical=defaultdict(Counter)
 with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
  for position,index in enumerate(range(start_index,start_index+count),1):
   record,gaps,spans=generate_one(index,images,spec,shape_field,vertex_fn,render_images);handle.write(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n");totals.update(record["generation_rejections"]);rejected+=record["rejected_candidates"];modes[record["rotation_mode"]]+=1;mode_by_label[record["reduction_mode"]][record["rotation_mode"]]+=1;reductions[record["reduction_mode"]]+=1;candidate_gaps.extend(gaps);candidate_spans.extend(spans);accepted_spans.append(record["reduction_factor_span"]) if record["reduction_mode"]=="changing" else None;counts.append(len(record[shape_field]));l5.append(1 if record["questions"][4]["ground_truth"]=="yes" else 0)
   for name,value in {"canvas_width":record["canvas_size"][0],"canvas_height":record["canvas_size"][1],"outer_side_length":record[shape_field][0]["side_length"],"innermost_side_length":record[shape_field][-1]["side_length"],"outer_inner_size_ratio":record[shape_field][0]["side_length"]/record[shape_field][-1]["side_length"],"sampled_total_inner_fraction":record["sampled_total_inner_fraction"],"sampled_total_reduction_root":record["sampled_total_reduction_root"],"reduction_factor_span":record["reduction_factor_span"],"extrapolation_reduction_factor":record["extrapolation_reduction_factor"],"line_width_px":record["line_width_px"],"matched_clearance_target_px":record["matched_clearance_target_px"],"minimum_adjacent_clear_background_px":record["minimum_adjacent_clear_background_px"],"outer_rotation_angle":record[shape_field][0]["rotation_angle"],"cumulative_rotation_degrees":record["cumulative_rotation_degrees"],"difficulty_score":record["difficulty_score"],"generation_attempt":record["generation_attempt"]}.items():sampled_numeric[name].append(value)
   for name,value in {"shape_count":len(record[shape_field]),"reduction_mode":record["reduction_mode"],"factor_progression_direction":record["factor_progression_direction"],"rotation_mode":record["rotation_mode"],"size_axis_band":record["size_axis_band"],"color_alternation":record["color_alternation"],"center_drift":record["center_drift"],"offset_requested_pre_containment":record["offset_requested_pre_containment"],"stroke_colors_used":tuple(record["stroke_colors_used"]),"level5_label":record["questions"][4]["ground_truth"]}.items():sampled_categorical[name][str(value)]+=1
   if record["rotation_mode"]!="fixed":l4.append(int(record["questions"][3]["ground_truth"]))
   if render_images and (position%100==0 or position==count):print(f"Rendered {position}/{count}",flush=True)
 injections=guard_injection_results(spec,vertex_fn);capture=max(sum(abs(value-answer)<=spec.rotation_tolerance for value in l4) for answer in spec.valid_rotation_values)/len(l4);stats={"accepted_scenes":count,"candidate_scenes_rejected":rejected,"rejection_cause_counts_may_overlap":True,"rejections_by_constraint":dict(sorted(totals.items())),"rotation_mode_distribution":dict(sorted(modes.items())),"rotation_mode_by_level2":{key:dict(sorted(value.items())) for key,value in sorted(mode_by_label.items())},"level2_distribution":dict(sorted(reductions.items())),"changing_factor_span_threshold":float(common.CHANGING_FACTOR_SPAN_MIN),"changing_factor_span_accepted":summary(accepted_spans),"changing_factor_span_all_candidates":summary(candidate_spans),"fixed_mode_count":modes["fixed"],"gap_separation_all_offset_candidates":summary(candidate_gaps),"level4_theoretical_uniform_baseline":float(common.theoretical_constant_capture(spec)),"level4_observed_max_constant_capture":capture,"level4_constant_capture_target":float(spec.constant_capture_target),"level5_threshold":float(common.LEVEL5_THRESHOLD),"level5_threshold_derivation":"v7 medians motivated an upward move; 12% is the lowest shared rounded threshold whose 9.6% lower guard is feasible for 10-12 triangles under both standing visibility floors","level5_exclusion_band":[float(common.LEVEL5_LOWER_GUARD),float(common.LEVEL5_UPPER_GUARD)],"level5_count_correlation":pearson(counts,l5),"level5_distribution":dict(sorted(Counter("yes" if value else "no" for value in l5).items())),"level5_extrapolation_rule":"reuse final observed per-step factor","wrap_guard_injection_test":common.wrap_guard_injection_result(spec),"guard_injection_tests":injections,"seed_namespace":spec.seed_namespace,"full_sampled_parameter_distributions":{"continuous":{name:summary(values) for name,values in sorted(sampled_numeric.items())},"categorical":{name:dict(sorted(values.items())) for name,values in sorted(sampled_categorical.items())}}}
 (output/"generation_stats.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8");common.write_build_manifest(output,spec,stats,generator_path,validator_path);print(json.dumps(stats,sort_keys=True));return stats
