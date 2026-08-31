"""Generate deterministic free-body-diagram reasoning images and annotations."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


G = 9.81
SIZE = 800
BACKGROUND = "#FDFAF4"
INK = "#213547"
MUTED = "#71808B"
OBJECT_FILL = "#DCE8EC"
MAX_ARROW_LENGTH = 128.0
SCENARIOS = ("incline", "hanging_mass", "atwood_machine", "wall_push", "elevator", "banked_curve")
PRESETS = ("equilibrium", "accelerating", "missing_force", "wrong_diagram")
DATASET_VERSION = "free-body-diagram-2.0.0"
COLORS = {"weight":"#C63D37", "normal":"#1976A3", "friction":"#2D8A57", "tension":"#8A55B5", "applied":"#D27A12", "drag":"#61727C"}
SYMBOLS = {"weight":"W", "normal":"N", "friction":"F", "tension":"T", "applied":"A", "drag":"D"}
CENTERS = {
    "incline":{"body":(400,390)}, "hanging_mass":{"body":(400,390)},
    "atwood_machine":{"left_mass":(275,420),"right_mass":(525,420)},
    "wall_push":{"body":(430,390)}, "elevator":{"body":(400,400)},
    "banked_curve":{"body":(400,390)},
}


def font(size, bold=False):
    path = Path("C:/Windows/Fonts")/("arialbd.ttf" if bold else "arial.ttf")
    try:return ImageFont.truetype(str(path), size)
    except OSError:return ImageFont.load_default()


def force(force_id, force_type, magnitude, direction, target="body", label=None):
    return {
        "force_id":force_id, "type":force_type, "magnitude":round(float(magnitude),6),
        "direction_degrees":round(float(direction)%360,6), "arrow_label":label or SYMBOLS[force_type],
        "target":target, "render_color":COLORS[force_type],
    }


def components(item):
    angle=math.radians(item["direction_degrees"])
    return item["magnitude"]*math.cos(angle), item["magnitude"]*math.sin(angle)


def vector_sum(items, target=None):
    chosen=[item for item in items if target is None or item["target"]==target]
    x=sum(components(item)[0] for item in chosen);y=sum(components(item)[1] for item in chosen)
    magnitude=math.hypot(x,y);direction=0.0 if magnitude<1e-8 else math.degrees(math.atan2(y,x))%360
    return x,y,magnitude,direction


def solve_incline(mass, angle, mu, applied, dynamic):
    theta=math.radians(angle);weight=mass*G;normal=weight*math.cos(theta);down_component=weight*math.sin(theta)-applied
    friction=mu*normal if dynamic else abs(down_component)
    friction_direction=angle if down_component>=0 else angle+180
    forces=[force("weight","weight",weight,270),force("normal","normal",normal,angle+90),force("friction","friction",friction,friction_direction),force("applied","applied",applied,angle)]
    return forces,{"required_friction_coefficient":abs(down_component)/normal}


def solve_hanging_mass(mass, acceleration):
    weight=mass*G;tension=mass*(G-acceleration)
    return [force("weight","weight",weight,270),force("tension","tension",tension,90)],{"tension_magnitude":tension}


def solve_atwood(mass1,mass2):
    tension=2*mass1*mass2*G/(mass1+mass2)
    return [force("weight_left","weight",mass1*G,270,"left_mass","W1"),force("tension_left","tension",tension,90,"left_mass","T1"),force("weight_right","weight",mass2*G,270,"right_mass","W2"),force("tension_right","tension",tension,90,"right_mass","T2")],{"tension_magnitude":tension}


def solve_wall_push(mass, applied_force, mu, dynamic):
    weight=mass*G;friction=mu*applied_force if dynamic else weight
    return [force("weight","weight",weight,270),force("normal","normal",applied_force,180),force("friction","friction",friction,90),force("applied","applied",applied_force,0)],{"minimum_friction_coefficient":weight/applied_force}


def solve_elevator(mass, acceleration):
    weight=mass*G;normal=mass*(G+acceleration)
    return [force("weight","weight",weight,270),force("normal","normal",normal,90)],{"support_force_magnitude":normal}


def solve_banked_curve(mass,speed,radius,angle,parked):
    theta=math.radians(angle);weight=mass*G
    if parked:
        normal=weight*math.cos(theta);signed_friction=weight*math.sin(theta)
    else:
        radial=speed*speed/radius
        normal=mass*(G*math.cos(theta)+radial*math.sin(theta))
        signed_friction=mass*(G*math.sin(theta)-radial*math.cos(theta))
    friction_direction=180-angle if signed_friction>=0 else 360-angle
    forces=[force("weight","weight",weight,270),force("normal","normal",normal,90-angle),force("friction","friction",abs(signed_friction),friction_direction)]
    return forces,{"required_friction_coefficient":abs(signed_friction)/normal}


def physical_scene(index):
    rng=random.Random(index);scenario=SCENARIOS[(index-1)%len(SCENARIOS)];preset=PRESETS[((index-1)//len(SCENARIOS))%len(PRESETS)];dynamic=preset=="accelerating"
    mass=round(rng.uniform(6,22),2);params={"mass_kg":mass};derived={};analysis_target="body"
    if scenario=="incline":
        angle=rng.randint(25,38);weight=mass*G;applied=round(weight*math.sin(math.radians(angle))*rng.uniform(.08,.18),2)
        mu=round(rng.uniform(.08,min(.22,math.tan(math.radians(angle))-.12)),3) if dynamic else 0.0
        if not dynamic:mu=round(abs(weight*math.sin(math.radians(angle))-applied)/(weight*math.cos(math.radians(angle)))+rng.uniform(.08,.18),3)
        params.update({"incline_angle_degrees":angle,"friction_coefficient":mu,"applied_force_N":applied});forces,derived=solve_incline(mass,angle,mu,applied,dynamic)
    elif scenario=="hanging_mass":
        acceleration=round(rng.uniform(1.0,3.2),2) if dynamic else 0.0;params["acceleration_command_m_s2"]=-acceleration;forces,derived=solve_hanging_mass(mass,acceleration)
    elif scenario=="atwood_machine":
        mass1=mass;mass2=mass if not dynamic else round(mass+rng.uniform(3,10),2);params={"mass1_kg":mass1,"mass2_kg":mass2};forces,derived=solve_atwood(mass1,mass2);analysis_target="left_mass";mass=mass1
    elif scenario=="wall_push":
        applied=round(mass*G*rng.uniform(1.35,1.9),2);mu=round(rng.uniform(.22,.42),3) if dynamic else round(mass*G/applied+rng.uniform(.08,.16),3);params.update({"applied_force_N":applied,"friction_coefficient":mu});forces,derived=solve_wall_push(mass,applied,mu,dynamic)
    elif scenario=="elevator":
        acceleration=round(rng.choice((-1,1))*rng.uniform(1.0,3.0),2) if dynamic else 0.0;params["elevator_acceleration_m_s2"]=acceleration;forces,derived=solve_elevator(mass,acceleration)
    else:
        angle=rng.randint(16,30);radius=round(rng.uniform(35,75),2);radial=0.0 if not dynamic else G*rng.uniform(.16,.30);speed=0.0 if not dynamic else round(math.sqrt(radial*radius),3);params.update({"bank_angle_degrees":angle,"speed_m_s":speed,"radius_m":radius});forces,derived=solve_banked_curve(mass,speed,radius,angle,not dynamic)
        params["friction_coefficient"]=round(derived["required_friction_coefficient"]+rng.uniform(.06,.14),3)
    return scenario,preset,mass,params,forces,derived,analysis_target


def diagram_variant(index,preset,forces,analysis_target):
    shown=deepcopy(forces);missing_type=None;missing_id=None;wrong=None
    focus=[f for f in shown if f["target"]==analysis_target]
    preferred=next((f for f in focus if f["type"] in {"friction","tension","normal"}),focus[0])
    if preset=="missing_force":
        missing_id=preferred["force_id"];missing_type=preferred["type"];shown=[f for f in shown if f["force_id"]!=missing_id]
    elif preset=="wrong_diagram":
        target=next(f for f in shown if f["force_id"]==preferred["force_id"]);correct={"magnitude":target["magnitude"],"direction_degrees":target["direction_degrees"]}
        if index%2:
            target["direction_degrees"]=round((target["direction_degrees"]+35)%360,6);kind="direction";description="direction is rotated 35 degrees from its physically required direction"
        else:
            target["magnitude"]=round(target["magnitude"]*1.4,6);kind="magnitude";description="magnitude is 40% larger than the physically required value"
        wrong={"which_force":target["force_id"],"arrow_label":target["arrow_label"],"whats_wrong":description,"error_kind":kind,"correct_value":correct,"shown_value":{"magnitude":target["magnitude"],"direction_degrees":target["direction_degrees"]}}
    return shown,missing_id,missing_type,wrong


def ranked_forces(shown):
    ordered=sorted(shown,key=lambda f:(-f["magnitude"],f["arrow_label"]));groups=[]
    for item in ordered:
        if groups and abs(item["magnitude"]-groups[-1][0]["magnitude"])<.005:groups[-1].append(item)
        else:groups.append([item])
    return [sorted([item["arrow_label"] for item in group]) for group in groups]


def clean_direction(value):
    value=round(value%360,1);names={0.0:"right",90.0:"upward",180.0:"left",270.0:"downward"}
    return f"{names.get(value,'direction')} ({value:g} degrees; 0=right, 90=up)"


def question_set(iid,row,shown,derived):
    focus=row["analysis_target"];_,shown_y,shown_mag,_=vector_sum(shown,focus);rank=ranked_forces(shown)
    vertical_balanced=abs(shown_y)<=max(.02,0.002*sum(f["magnitude"] for f in shown if f["target"]==focus))
    candidates=[f for f in shown if f["target"]==focus];query=candidates[row["seed"]%len(candidates)]
    q2_text=f"Which labeled arrow represents the {query['type']} force on the analyzed body? Answer with the arrow label."
    q2_truth=query["arrow_label"];q2_format="arrow_label"
    if row["preset"]=="missing_force":
        q2_text+= " Also identify which required force is missing from the diagram."
        q2_truth={"arrow_label":query["arrow_label"],"missing_force":row["missing_force_type"]};q2_format="arrow_label_and_missing_force"
    l3={"magnitude_ranking":rank,"shown_vertical_forces_balanced":"yes" if vertical_balanced else "no","physical_equilibrium":"yes" if row["is_equilibrium"] else "no"}
    name,value=next(iter(derived.items()));l4={"net_force_N":round(row["net_force_magnitude"],2),name:round(value,2)}
    q4_text=f"Using the physically correct force model (not any intentionally incorrect arrow as drawn), what is the physical net force magnitude in newtons, and what is the {name.replace('_',' ')} for this scenario? Give both values."
    if row["preset"]=="wrong_diagram":
        q4_text+=" Separately, inspect the rendered diagram: one drawn force is incorrect; identify that drawn arrow and explain its error relative to the physically correct model."
        l4["wrong_force_details"]=row["wrong_force_details"]
    if row["scenario_type"]=="incline":
        p=row["physics_parameters"];angle=40;normal=row["analysis_mass_kg"]*G*math.cos(math.radians(angle));required=abs(row["analysis_mass_kg"]*G*math.sin(math.radians(angle))-p["applied_force_N"]);slip=required>p["friction_coefficient"]*normal
        q5_text="If the incline angle were increased to 40 degrees while mass, applied force, and friction coefficient stayed unchanged, would the block slip? Answer yes or no."
        q5_truth="yes" if slip else "no";q5_type="incline_40_slip";q5_format="yes_no"
    else:
        removable=next((f for f in row["forces"] if f["target"]==focus and f["type"] in {"tension","normal","friction"}),next(f for f in row["forces"] if f["target"]==focus))
        remaining=[f for f in row["forces"] if f["force_id"]!=removable["force_id"]];*_,direction=vector_sum(remaining,focus)
        q5_text=f"If force {removable['arrow_label']} were removed while all other physical forces stayed unchanged, what direction would the resulting acceleration point? Use 0 degrees for right and 90 degrees for up."
        q5_truth=clean_direction(direction);q5_type="force_removed_direction";q5_format="direction_degrees"
    return [
        {"question_id":iid+"_q1","question_text":"How many force arrows are shown in this diagram?","question_type":"shown_force_count","ground_truth":len(shown),"answer_format":"integer","difficulty_level":1},
        {"question_id":iid+"_q2","question_text":q2_text,"question_type":"identify_force" if row["preset"]!="missing_force" else "identify_force_and_omission","ground_truth":q2_truth,"answer_format":q2_format,"difficulty_level":2},
        {"question_id":iid+"_q3","question_text":"Using only the arrows as drawn in this diagram, rank their shown magnitudes from largest to smallest, grouping ties, and state whether their shown vertical components are balanced. Then, as a separate judgment using the physically correct version of the scenario, state whether the body is in equilibrium overall. Give all three answers and keep the drawn-diagram and physically-correct frames separate.","question_type":"rank_balance_equilibrium","ground_truth":l3,"answer_format":{"type":"structured_tie_groups","ordering_within_tie_group":"any","fields":["magnitude_ranking","shown_vertical_forces_balanced","physical_equilibrium"]},"difficulty_level":3},
        {"question_id":iid+"_q4","question_text":q4_text,"question_type":"compound_force_calculation" if row["preset"]!="wrong_diagram" else "compound_force_and_error_detection","ground_truth":l4,"answer_format":{"type":"numeric_tolerance","tolerance_percent":2},"difficulty_level":4},
        {"question_id":iid+"_q5","question_text":q5_text,"question_type":q5_type,"ground_truth":q5_truth,"answer_format":q5_format,"difficulty_level":5},
    ]


def arrow(draw,start,direction,length,color,width=7):
    rad=math.radians(direction);end=(start[0]+length*math.cos(rad),start[1]-length*math.sin(rad));draw.line((start,end),fill=color,width=width)
    head=16;wing=math.radians(25)
    for sign in (-1,1):
        back=math.radians(direction+180)+sign*wing;p=(end[0]+head*math.cos(back),end[1]-head*math.sin(back));draw.line((end,p),fill=color,width=width)
    return end


def display_starts(scenario, shown):
    """Give coincident same-direction arrows small perpendicular offsets."""
    groups={}
    for item in shown:groups.setdefault((item["target"],round(item["direction_degrees"],3)),[]).append(item)
    result={}
    for (_,direction),items in groups.items():
        radians=math.radians(direction+90)
        offsets=[0] if len(items)==1 else [(position-(len(items)-1)/2)*18 for position in range(len(items))]
        for item,offset in zip(items,offsets):
            center=CENTERS[scenario][item["target"]];result[item["force_id"]]=(center[0]+offset*math.cos(radians),center[1]-offset*math.sin(radians))
    return result


def environment(draw,row):
    scenario=row["scenario_type"];p=row["physics_parameters"];centers=CENTERS[scenario]
    if scenario=="incline":
        c=centers["body"];a=math.radians(p["incline_angle_degrees"]);dx,dy=280*math.cos(a),280*math.sin(a);draw.line((c[0]-dx,c[1]+dy,c[0]+dx,c[1]-dy),fill=MUTED,width=6);draw.rectangle((c[0]-42,c[1]-28,c[0]+42,c[1]+28),fill=OBJECT_FILL,outline=INK,width=4)
    elif scenario=="hanging_mass":
        c=centers["body"];draw.line((c[0],130,c[0],c[1]-38),fill=MUTED,width=5);draw.rectangle((c[0]-45,c[1]-35,c[0]+45,c[1]+35),fill=OBJECT_FILL,outline=INK,width=4)
    elif scenario=="atwood_machine":
        l,r=centers["left_mass"],centers["right_mass"];draw.ellipse((335,145,465,275),outline=INK,width=6);draw.line((l[0],210,l[0],l[1]-35),fill=MUTED,width=5);draw.line((r[0],210,r[0],r[1]-35),fill=MUTED,width=5)
        for c,label in ((l,"m1"),(r,"m2")):draw.rectangle((c[0]-42,c[1]-32,c[0]+42,c[1]+32),fill=OBJECT_FILL,outline=INK,width=4);draw.text(c,label,fill=INK,font=font(22,True),anchor="mm")
    elif scenario=="wall_push":
        c=centers["body"];draw.line((500,130,500,650),fill=MUTED,width=8);draw.rectangle((c[0]-45,c[1]-38,c[0]+45,c[1]+38),fill=OBJECT_FILL,outline=INK,width=4)
    elif scenario=="elevator":
        c=centers["body"];draw.rectangle((245,160,555,625),outline=MUTED,width=6);draw.line((400,90,400,160),fill=MUTED,width=5);draw.rectangle((c[0]-46,c[1]-36,c[0]+46,c[1]+36),fill=OBJECT_FILL,outline=INK,width=4)
    else:
        c=centers["body"];a=math.radians(p["bank_angle_degrees"]);dx,dy=270*math.cos(a),270*math.sin(a);draw.line((c[0]-dx,c[1]+dy,c[0]+dx,c[1]-dy),fill=MUTED,width=7);draw.rectangle((c[0]-48,c[1]-25,c[0]+48,c[1]+25),fill=OBJECT_FILL,outline=INK,width=4)


def parameter_lines(row):
    p=row["physics_parameters"];s=row["scenario_type"]
    if s=="atwood_machine":return [f"m1 = {p['mass1_kg']:.2f} kg",f"m2 = {p['mass2_kg']:.2f} kg"]
    lines=[f"mass = {p['mass_kg']:.2f} kg"]
    mappings=(("incline_angle_degrees","incline angle","°"),("bank_angle_degrees","bank angle","°"),("friction_coefficient","μ",""),("applied_force_N","applied"," N"),("elevator_acceleration_m_s2","lift a"," m/s²"),("speed_m_s","speed"," m/s"),("radius_m","radius"," m"))
    for key,label,suffix in mappings:
        if key in p:lines.append(f"{label} = {p[key]}{suffix}")
    return lines


def render(path,row):
    image=Image.new("RGB",(SIZE,SIZE),BACKGROUND);draw=ImageDraw.Draw(image);environment(draw,row);shown=row["shown_forces"];max_m=max(f["magnitude"] for f in shown);scale=MAX_ARROW_LENGTH/max_m;starts=display_starts(row["scenario_type"],shown)
    for item in shown:
        start=starts[item["force_id"]];end=arrow(draw,start,item["direction_degrees"],item["magnitude"]*scale,item["render_color"])
        dx=12 if end[0]>=start[0] else -12;dy=-12 if end[1]<=start[1] else 12
        text=f"{item['arrow_label']}  {item['magnitude']:.1f} N";draw.text((end[0]+dx,end[1]+dy),text,fill=item["render_color"],font=font(18,True),anchor="lm" if dx>0 else "rm")
    lines=parameter_lines(row);box=(24,24,245,45+28*len(lines));draw.rounded_rectangle(box,8,fill="#F2F4F3",outline="#B8C1C5",width=2)
    for n,text in enumerate(lines):draw.text((38,40+28*n),text,fill=INK,font=font(18))
    draw.text((SIZE-24,28),row["scenario_type"].replace("_"," ").upper(),fill=INK,font=font(19,True),anchor="ra")
    image.save(path,optimize=True)


def generate_one(index,images,render_image=True):
    scenario,preset,mass,params,forces,derived,target=physical_scene(index);shown,missing_id,missing_type,wrong=diagram_variant(index,preset,forces,target)
    _,_,net_mag,net_dir=vector_sum(forces,target);_,_,shown_mag,shown_dir=vector_sum(shown,target);iid=f"fbd_{index:04d}"
    row={"dataset_version":DATASET_VERSION,"physical_frame":"forces: physically correct scenario vectors","rendered_frame":"shown_forces: arrows actually drawn in the PNG","question_frame_policy":"drawn quantities use shown_forces; physical equilibrium, Level 4 calculations, and Level 5 use forces; wrong-diagram identification compares both","id":iid,"image_path":f"images/{iid}.png","seed":index,"scenario_type":scenario,"preset":preset,"physics_parameters":params,"analysis_target":target,"analysis_mass_kg":mass,"forces":forces,"shown_forces":shown,"net_force_magnitude":round(net_mag,6),"net_force_direction_degrees":round(net_dir,6),"shown_net_force_magnitude":round(shown_mag,6),"shown_net_force_direction_degrees":round(shown_dir,6),"resulting_acceleration_m_s2":round(net_mag/mass,6),"is_equilibrium":net_mag<1e-5,"missing_force_id":missing_id,"missing_force_type":missing_type,"wrong_force_details":wrong,"derived_quantities":{k:round(v,6) for k,v in derived.items()},"difficulty_score":round(.38+SCENARIOS.index(scenario)*.035+PRESETS.index(preset)*.09,4)}
    row["questions"]=question_set(iid,row,shown,derived)
    if render_image:render(images/f"{iid}.png",row)
    return row


def generate_dataset(count=3000,output=None,start=1,render_images=True):
    output=Path(output or Path(__file__).resolve().parent);images=output/"images";images.mkdir(parents=True,exist_ok=True);counts=Counter();presets=Counter()
    with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
        for position,index in enumerate(range(start,start+count),1):
            row=generate_one(index,images,render_images);handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n");counts[row["scenario_type"]]+=1;presets[row["preset"]]+=1
            if render_images and (position%100==0 or position==count):print(f"Rendered {position}/{count}",flush=True)
    stats={"images":count,"scenario_distribution":counts,"preset_distribution":presets};(output/"generation_stats.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8");print(json.dumps(stats,default=dict,sort_keys=True))


def generate_sample(output):
    """Five high-priority cases spanning all presets and the risky scenarios."""
    indices=(1,8,15,22,30);output=Path(output);images=output/"images";images.mkdir(parents=True,exist_ok=True);rows=[]
    for index in indices:rows.append(generate_one(index,images,True))
    with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
        for row in rows:handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n")
    print("Sample indices:",", ".join(map(str,indices)))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--n","--count",dest="count",type=int,default=3000);parser.add_argument("--start-index",type=int,default=1);parser.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent);parser.add_argument("--sample",action="store_true");parser.add_argument("--metadata-only",action="store_true");args=parser.parse_args();output=args.output_dir/"sample_test" if args.sample else args.output_dir
    if args.sample:generate_sample(output)
    else:generate_dataset(args.count,output,args.start_index,not args.metadata_only)


if __name__=="__main__":main()
