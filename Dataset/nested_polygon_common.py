"""Canonical v8 logic for the GRIP nested-polygon family."""
from __future__ import annotations
import hashlib,json,math,random,subprocess
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

DATASET_VERSION="8.0.0";VERSION_SLUG="v8";DRIFT_FLOOR=Fraction(3,100)
# V7 medians (6.78%, 7.85%, 6.92%) suggested moving upward. A full guard-
# intersection calibration then found that 12% is the lowest shared rounded
# threshold whose 9.6% lower margin permits 10-12 triangle outlines while
# retaining both the 15 px inner-size and 3 px clear-background floors.
LEVEL5_THRESHOLD=Fraction(12,100)
LEVEL5_LOWER_GUARD=Fraction(96,1000);LEVEL5_UPPER_GUARD=Fraction(144,1000)
TARGET_NO_RANGE=(Fraction(93,1000),Fraction(95,1000));TARGET_YES_RANGE=(Fraction(150,1000),Fraction(170,1000))
FIXED_MODE_CAP=Fraction(15,100);CHANGING_FACTOR_SPAN_MIN=Fraction(135,100);CHANGING_FACTOR_SPAN_MAX=Fraction(147,100)
MIN_INNER_SIDE_PX=15.0;MIN_CLEAR_BACKGROUND_PX=3.0
RATIO_ANSWER_FORMAT="number rounded to 1 decimal in curly brackets, graded within ±10% relative"

@dataclass(frozen=True)
class PolygonSpec:
 key:str;singular:str;plural:str;vertex_count:int;modulus:int;rotation_tolerance:int;gap_margin:Fraction;seed_namespace:int;constant_capture_target:Fraction
 @property
 def rotation_margin(self):return 2*self.rotation_tolerance
 @property
 def dataset_version(self):return f"nested-{self.plural}-{DATASET_VERSION}"
 @property
 def valid_rotation_values(self):return tuple(range(self.rotation_margin,self.modulus-self.rotation_margin+1))
SPECS={
 "square":PolygonSpec("square","square","squares",4,90,6,Fraction(5,100),31_000_000,Fraction(20,100)),
 "triangle":PolygonSpec("triangle","triangle","triangles",3,120,8,Fraction(4,100),47_000_000,Fraction(20,100)),
 "hexagon":PolygonSpec("hexagon","hexagon","hexagons",6,60,5,Fraction(12,1000),61_000_000,Fraction(27,100)),
}
def exact_decimal(value):return Fraction(str(value))
def fraction_text(value):return f"{value.numerator}/{value.denominator}"
def round_half_up(value):return (2*value.numerator+value.denominator)//(2*value.denominator)
def centroid_spread_fraction(shapes):
 spread=max(math.dist(shapes[0]["center"],shape["center"]) for shape in shapes[1:]);return exact_decimal(round(spread,4))/exact_decimal(shapes[0]["side_length"])
def drift_label(shapes):return "offset" if centroid_spread_fraction(shapes)>=DRIFT_FLOOR else "concentric"
def cumulative_rotation(shapes,spec):return (exact_decimal(shapes[-1]["rotation_angle"])-exact_decimal(shapes[0]["rotation_angle"]))%spec.modulus
def _selected(spec,salt,count):return frozenset(random.Random(spec.seed_namespace+salt).sample(range(1,3001),count))
@lru_cache(maxsize=None)
def changing_indices(spec):return _selected(spec,811,1500)
@lru_cache(maxsize=None)
def reduction_rank_map(spec):
 changing=sorted(changing_indices(spec));constant=sorted(set(range(1,3001))-changing_indices(spec));return {index:rank for pool in (changing,constant) for rank,index in enumerate(pool)}
def reduction_rank(index,spec):
 return reduction_rank_map(spec)[index]
@lru_cache(maxsize=None)
def size_axis_plan(spec):
 """Return label-independent contraction targets with non-degenerate spans.

 Each rank is used once by each Level-2 label, so count and total contraction
 are exactly matched.  The changing member receives a shape-namespaced span.
 """
 counts=[count for count in range(4,12) for _ in range(166)]+[12]*172
 random.Random(spec.seed_namespace+701).shuffle(counts)
 # Select exactly half of every count bucket for each Level-5 answer.  Each
 # rank is used once by each Level-2 label, so this yields 1,500/1,500 labels
 # and removes count/answer association by construction.
 selected=set()
 for count in range(4,13):
  bucket=[rank for rank,value in enumerate(counts) if value==count]
  random.Random(spec.seed_namespace+704+count).shuffle(bucket)
  selected.update(bucket[:len(bucket)//2])
 plan={};orders={}
 for count in range(4,13):
  for yes in (False,True):
   bucket=[rank for rank,value in enumerate(counts) if value==count and (rank in selected)==yes]
   order=list(range(len(bucket)));random.Random(spec.seed_namespace+705+count*10+int(yes)).shuffle(order)
   orders[(count,yes)]={rank:(order[pos]+.5)/len(bucket) for pos,rank in enumerate(bucket)}
 for rank,count in enumerate(counts):
  yes=rank in selected;rng=random.Random(spec.seed_namespace+707+rank)
  quantile=orders[(count,yes)][rank]
  if yes:next_min,next_max=map(float,TARGET_YES_RANGE)
  elif spec.key=="triangle" and count<=8:next_min,next_max=.040,.090
  else:next_min,next_max=map(float,TARGET_NO_RANGE)
  target_next=next_min+(next_max-next_min)*quantile
  # For a constant sequence, next = inner * inner**(1/(count-1)).
  inner=target_next**((count-1)/count)
  total_root=inner**(1/(count-1));span_rng=random.Random(spec.seed_namespace+1_300_000+rank)
  span=span_rng.uniform(float(CHANGING_FACTOR_SPAN_MIN),float(CHANGING_FACTOR_SPAN_MAX))
  # Decrease factors inward so the final visible outline never becomes the
  # closest pair; the constant/changing distinction remains the target itself.
  direction="changing"
  plan[rank]={"count":count,"band":"high" if yes else "low","total_root":total_root,"target_inner_fraction":inner,"factor_span":span,"factor_direction":direction,"target_level5":"yes" if yes else "no","pair_rank":rank}
 return plan
@lru_cache(maxsize=None)
def fixed_ranks(spec):
 if spec.key=="triangle":
  pool=[rank for rank in range(1500) if size_axis_plan(spec)[rank]["target_level5"]=="yes"]
  pool.sort(key=lambda rank:(-size_axis_plan(spec)[rank]["count"],rank))
  return frozenset(pool[:225])
 return frozenset(random.Random(spec.seed_namespace+101).sample(range(1500),225))
@lru_cache(maxsize=None)
def fixed_indices(spec):return frozenset(index for index in range(1,3001) if reduction_rank(index,spec) in fixed_ranks(spec))
def choose_rotation_mode(index,spec):
 if index in fixed_indices(spec):return "fixed"
 # v6 applies the v4 uniform->per-shape representation identically to both
 # Level-2 labels. This makes the observed mode distribution exactly matched.
 return "per_shape_independent"
def reduction_mode(index,spec):return "changing" if index in changing_indices(spec) else "constant"
def nonfixed_rank(index,spec):
 rank=reduction_rank(index,spec);return rank-sum(candidate in fixed_ranks(spec) for candidate in range(rank))
def _raw_target_by_nonfixed_position(position,spec):
 values=spec.valid_rotation_values;n=len(values);full_cycles=1275//n;cycle,within=divmod(position,n);stride=max(1,n//2)
 if cycle<full_cycles:index=(within*stride+cycle*7)%n
 else:
  remainder=1275-full_cycles*n;index=round(within*n/remainder)%n
 return Fraction(values[index])
@lru_cache(maxsize=None)
def triangle_rotation_rank_map(spec):
 ranks=[rank for rank in range(1500) if rank not in fixed_ranks(spec)];values=[_raw_target_by_nonfixed_position(i,spec) for i in range(len(ranks))]
 ranks.sort(key=lambda rank:(_triangle_rotation_capacity(rank,spec),rank))
 values.sort(key=lambda value:(abs(float(value if value<=spec.modulus/2 else value-spec.modulus)),float(value)))
 return dict(zip(ranks,values))
@lru_cache(maxsize=None)
def _triangle_rotation_capacity(rank,spec):
 plan=size_axis_plan(spec)[rank];sides=[500.0]
 for _ in range(plan["count"]-1):sides.append(sides[-1]*plan["total_root"])
 def vertices(side,angle):
  radius=side/math.sqrt(3);start=math.radians(angle-90)
  return [(radius*math.cos(start+2*math.pi*i/3),radius*math.sin(start+2*math.pi*i/3)) for i in range(3)]
 def inside(point,polygon):
  signs=[]
  for i in range(3):
   ax,ay=polygon[i];bx,by=polygon[(i+1)%3];cross=(bx-ax)*(point[1]-ay)-(by-ay)*(point[0]-ax)
   if abs(cross)>1e-7:signs.append(cross>0)
  return not signs or all(value==signs[0] for value in signs)
 def segdist(point,a,b):
  px,py=point;ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay;den=dx*dx+dy*dy;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/den));return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
 total=0.0
 for outer_side,inner_side in zip(sides,sides[1:]):
  outer=vertices(outer_side,0);lo,hi=0.0,60.0
  for _ in range(22):
   mid=(lo+hi)/2;inner=vertices(inner_side,mid);clear=min(segdist(v,outer[j],outer[(j+1)%3]) for v in inner for j in range(3))-.70
   if all(inside(v,outer) for v in inner) and clear>=3.001:lo=mid
   else:hi=mid
  total+=lo*.995
 return total
def target_rotation(index,spec,mode):
 if mode=="fixed":return Fraction(0)
 rank=reduction_rank(index,spec)
 if spec.key=="triangle":return triangle_rotation_rank_map(spec)[rank]
 return _raw_target_by_nonfixed_position(nonfixed_rank(index,spec),spec)
def rotation_sequence(rng,base,count,mode,spec,target,step_reduction_factors=None):
 if mode=="fixed":return [base]*count
 signed=float(target if target<=spec.modulus/2 else target-spec.modulus)
 if mode=="uniform_whole_nest":return [base+i*signed/(count-1) for i in range(count)]
 weights=[rng.uniform(.55,1.45) for _ in range(count-1)]
 if step_reduction_factors is not None:
  scale_position=1.0;adjusted=[]
  for weight,factor in zip(weights,step_reduction_factors):adjusted.append(weight*(scale_position**1.3)*max(.001,(1-factor)**2));scale_position*=factor
  weights=adjusted
 scale=signed/sum(weights);angles=[base]
 for weight in weights:angles.append(angles[-1]+weight*scale)
 return angles
def rotation_is_margin_safe(delta,mode,spec):
 if mode=="fixed":return delta==0
 return Fraction(spec.rotation_margin)<=delta<=Fraction(spec.modulus-spec.rotation_margin)
def wrap_guard_injection_result(spec):
 lower=Fraction(spec.rotation_margin);upper=Fraction(spec.modulus-spec.rotation_margin)
 probes={"below_lower":lower-1,"lower_boundary":lower,"upper_boundary":upper,"above_upper":upper+1}
 results={name:rotation_is_margin_safe(value,"uniform_whole_nest",spec) for name,value in probes.items()}
 return {"thresholds":{"lower":float(lower),"upper":float(upper)},"probes":{name:{"delta":float(probes[name]),"accepted":accepted} for name,accepted in results.items()},"pass":not results["below_lower"] and results["lower_boundary"] and results["upper_boundary"] and not results["above_upper"]}
def changing_factors_for_total(total_root,span,count,direction):
 """Vary earlier steps while matching the paired constant scene's last step.

 The first m-1 log offsets are symmetric (product one) and the final offset is
 zero. Thus total contraction and the extrapolation factor both match the
 constant member, while the observed span remains exactly the sampled target.
 Larger factors occur while polygons are larger, protecting inner clearance.
 """
 m=count-1
 if m<=2:return [total_root]*m
 positive=math.log(span)/(m-1);negative=-(m-2)*positive
 offsets=[positive]*(m-2)+[negative]
 factors=[total_root*math.exp(value) for value in offsets]+[total_root]
 return factors
def step_factors(shapes):return [shapes[i+1]["side_length"]/shapes[i]["side_length"] for i in range(len(shapes)-1)]
def factor_span(shapes):
 factors=step_factors(shapes);return max(factors)/min(factors)
def classify_reduction_mode(shapes):return "changing" if factor_span(shapes)>=float(CHANGING_FACTOR_SPAN_MIN)-1e-5 else "constant"
def extrapolation_factor(shapes):return step_factors(shapes)[-1]
def extrapolated_fraction(shapes):return exact_decimal(shapes[-1]["side_length"])*exact_decimal(extrapolation_factor(shapes))/exact_decimal(shapes[0]["side_length"])
def level5_label(shapes):return "yes" if extrapolated_fraction(shapes)>LEVEL5_THRESHOLD else "no"
def level5_is_margin_safe(shapes):
 value=extrapolated_fraction(shapes);return level5_value_is_safe(value)
def level5_value_is_safe(value):return not LEVEL5_LOWER_GUARD<value<LEVEL5_UPPER_GUARD
def gap_value_is_safe(value,spec):return Fraction(value)>=spec.gap_margin
def reduction_factors_are_safe(factors,mode):
 if any(not 0<factor<1 for factor in factors):return False
 span=max(factors)/min(factors)
 return span>=float(CHANGING_FACTOR_SPAN_MIN)-1e-5 if mode=="changing" else span<=1.00005
def inner_size_is_safe(side_length):return float(side_length)>=MIN_INNER_SIDE_PX
def outline_clearance_is_safe(clearance):return float(clearance)>=MIN_CLEAR_BACKGROUND_PX
def point_line_distance(point,start,end):
 px,py=point;ax,ay=start;bx,by=end;return abs((bx-ax)*(ay-py)-(ax-px)*(by-ay))/math.hypot(bx-ax,by-ay)
def corresponding_side_gaps(outer,inner,vertex_fn):
 outer_vertices=vertex_fn(outer["center"],outer["side_length"],outer["rotation_angle"]);inner_vertices=vertex_fn(inner["center"],inner["side_length"],inner["rotation_angle"]);gaps=[]
 for index in range(len(outer_vertices)):
  a,b=inner_vertices[index],inner_vertices[(index+1)%len(inner_vertices)];midpoint=((a[0]+b[0])/2,(a[1]+b[1])/2);gaps.append(point_line_distance(midpoint,outer_vertices[index],outer_vertices[(index+1)%len(outer_vertices)]))
 return gaps
def gap_separation(shapes,vertex_fn):
 gaps=sorted(corresponding_side_gaps(shapes[0],shapes[-1],vertex_fn));return Fraction(str(gaps[1]-gaps[0]))/Fraction(str(gaps[1])) if gaps[1] else Fraction(0)
def rotation_answer_format(spec):return f"number in curly brackets, 0-{spec.modulus}, graded within ±{spec.rotation_tolerance} degrees"
def build_questions(item_id,shapes,spec):
 ratio=shapes[0]["side_length"]/shapes[-1]["side_length"];delta=cumulative_rotation(shapes,spec)
 return [
  {"question_id":item_id+"_q1","question_text":f"How many {spec.plural} are in this image? Please answer with a number in curly brackets, e.g. {{10}}.","question_type":f"count_{spec.plural}","ground_truth":str(len(shapes)),"answer_format":"numeric","difficulty_level":1},
  {"question_id":item_id+"_q2","question_text":"Do the shapes shrink by roughly the same factor at each step, or does the amount of shrinking change as you move inward? Answer 'constant' or 'changing'.","question_type":"size_progression_direction","ground_truth":classify_reduction_mode(shapes),"answer_format":"choice","difficulty_level":2},
  {"question_id":item_id+"_q3","question_text":f"What is the approximate ratio of the outermost {spec.singular}'s side length to the innermost {spec.singular}'s side length? Answer as a number rounded to 1 decimal in curly brackets, e.g. {{3.2}}.","question_type":"outer_inner_side_ratio","ground_truth":f"{ratio:.1f}","answer_format":RATIO_ANSWER_FORMAT,"difficulty_level":3},
  {"question_id":item_id+"_q4","question_text":f"Through approximately how many degrees has the innermost {spec.singular} been rotated relative to the outermost {spec.singular}? Because regular {spec.plural} have {spec.vertex_count}-fold symmetry, answer with a value from 0 to {spec.modulus} in curly brackets, e.g. {{{min(25,spec.modulus//3)}}}.","question_type":"cumulative_rotation","ground_truth":str(round_half_up(delta)),"answer_format":rotation_answer_format(spec),"difficulty_level":4},
  {"question_id":item_id+"_q5","question_text":f"If one more {spec.singular} were added inside the innermost one following the same size-reduction pattern, would its side length still be long enough to be visually distinguishable at this image resolution (i.e. greater than roughly 12% of the outermost {spec.singular}'s side length)? Answer yes or no.","question_type":f"next_{spec.singular}_visually_distinguishable","ground_truth":level5_label(shapes),"answer_format":"yes_no","difficulty_level":5},
 ]
def theoretical_constant_capture(spec):return Fraction(min(2*spec.rotation_tolerance+1,len(spec.valid_rotation_values)),len(spec.valid_rotation_values))
def constraint_parameters(spec):return {"symmetry_modulus_degrees":spec.modulus,"rotation_tolerance_degrees":spec.rotation_tolerance,"rotation_rejection_margin_degrees":spec.rotation_margin,"relative_gap_margin":float(spec.gap_margin),"drift_floor_is_rejection_guard":False,"descriptive_drift_reference":float(DRIFT_FLOOR),"changing_factor_span_min":float(CHANGING_FACTOR_SPAN_MIN),"changing_factor_span_max":float(CHANGING_FACTOR_SPAN_MAX),"minimum_innermost_side_px":MIN_INNER_SIDE_PX,"minimum_clear_background_px":MIN_CLEAR_BACKGROUND_PX,"size_axis_sampling":"sample label-matched total contraction and final factor; vary earlier changing steps in log-product-neutral pairs","changing_level5_extrapolation":"reuse final observed per-step factor","level5_threshold":float(LEVEL5_THRESHOLD),"level5_threshold_derivation":"v7 medians motivated an upward move; 12% is the lowest shared rounded threshold whose 9.6% lower guard is feasible for 10-12 triangles under both standing visibility floors","level5_exclusion_band":[float(LEVEL5_LOWER_GUARD),float(LEVEL5_UPPER_GUARD)],"fixed_mode_cap":float(FIXED_MODE_CAP),"level4_constant_capture_target":float(spec.constant_capture_target),"level4_theoretical_uniform_baseline":float(theoretical_constant_capture(spec)),"seed_namespace":spec.seed_namespace,"level2_reduction_balance":"1500 constant / 1500 changing"}
def file_sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git_state(repo):
 try:return subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip(),bool(subprocess.check_output(["git","status","--porcelain"],cwd=repo,text=True).strip())
 except Exception:return "unavailable",None
def write_build_manifest(output,spec,stats,generator_path,validator_path):
 output=Path(output);commit,dirty=git_state(output.parents[1]);common_path=Path(__file__).resolve();visual_dependency=common_path.with_name("nested_polygon_visual_checks.py");generator_common=common_path.with_name("nested_polygon_generator.py");validator_common=common_path.with_name("nested_polygon_validator_common.py");flattener=common_path.with_name("flatten_nested_polygon_annotations.py");manifest={"dataset_version":spec.dataset_version,"version_slug":VERSION_SLUG,"shape":spec.key,"git_commit":commit,"working_tree_dirty_at_build":dirty,"constraints":constraint_parameters(spec),"wrap_guard_injection_test":wrap_guard_injection_result(spec),"guard_injection_tests":stats.get("guard_injection_tests"),"generation_stats":stats,"source_sha256":{"nested_polygon_common.py":file_sha256(common_path),"nested_polygon_generator.py":file_sha256(generator_common),"nested_polygon_validator_common.py":file_sha256(validator_common),"flatten_nested_polygon_annotations.py":file_sha256(flattener),"nested_polygon_visual_checks.py":file_sha256(visual_dependency),Path(generator_path).name:file_sha256(generator_path),Path(validator_path).name:file_sha256(validator_path) if Path(validator_path).exists() else None}}
 (output/"build_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8");return manifest
