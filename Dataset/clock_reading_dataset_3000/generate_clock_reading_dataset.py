"""Generate the GRIP analog-clock reading and hand-angle dataset."""

from __future__ import annotations

import argparse
import json
import math
import random
from fractions import Fraction
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont


CANVAS=600;BACKGROUND="#FDFAF4";INK="#18344B";HOUR_COLOR="#2F6F68";MINUTE_COLOR="#B43E35"
CENTER=(300,300);RADIUS=240;HOUR_LENGTH=120;MINUTE_LENGTH=178


def font(size,bold=False):
    path=Path("C:/Windows/Fonts")/("arialbd.ttf" if bold else "arial.ttf")
    try:return ImageFont.truetype(str(path),size)
    except OSError:return ImageFont.load_default()


def hand_angles(hour:int,minute:int):
    return Fraction((hour%12)*30)+Fraction(minute,2),Fraction(minute*6)


def smaller_angle(hour_angle:Fraction,minute_angle:Fraction):
    difference=abs(hour_angle-minute_angle)%360
    return min(difference,Fraction(360)-difference)


def round_half_up(value:Fraction):
    return (2*value.numerator+value.denominator)//(2*value.denominator)


def advance_time(hour:int,minute:int,delta:int=20):
    total=((hour%12)*60+minute+delta)%(12*60)
    new_hour_24=total//60
    return (12 if new_hour_24==0 else new_hour_24),total%60


def make_scene(index:int):
    rng=random.Random(index);hour=rng.randint(1,12)
    # Parameter-directed 50/50 relation balance; minute 30 is excluded because
    # it is exactly at the 6 and is neither before nor after half past. Times
    # whose hands are less than 12 degrees apart are also excluded so the
    # shorter hand remains visibly distinguishable in the rendered benchmark.
    relation_minutes=range(0,30) if index%2==0 else range(31,60)
    minute_candidates=[]
    for candidate in relation_minutes:
        candidate_angles=hand_angles(hour,candidate)
        if smaller_angle(*candidate_angles)>=12:
            minute_candidates.append(candidate)
    minute=rng.choice(minute_candidates)
    hour_angle,minute_angle=hand_angles(hour,minute);angle=smaller_angle(hour_angle,minute_angle)
    new_hour,new_minute=advance_time(hour,minute);new_ha,new_ma=hand_angles(new_hour,new_minute);new_angle=smaller_angle(new_ha,new_ma)
    iid=f"clock_reading_{index:04d}"
    questions=[
        {"question_id":f"{iid}_q1","difficulty_level":1,"question_type":"hour_recently_passed","question_text":"Which hour has the short hand most recently passed? Answer with a number from 1 to 12.","ground_truth":str(hour),"answer_format":"integer 1-12"},
        {"question_id":f"{iid}_q2","difficulty_level":2,"question_type":"minute_before_after_six","question_text":"Is the minute hand pointing before or after the 6 (half past)? Answer 'before' or 'after'.","ground_truth":"before" if minute<30 else "after","answer_format":"before or after"},
        {"question_id":f"{iid}_q3","difficulty_level":3,"question_type":"exact_clock_time","question_text":"What is the exact time shown? Answer in HH:MM format.","ground_truth":f"{hour:02d}:{minute:02d}","answer_format":"HH:MM"},
        {"question_id":f"{iid}_q4","difficulty_level":4,"question_type":"smaller_hand_angle","question_text":"What is the smaller angle between the hour and minute hands, rounded to the nearest degree?","ground_truth":str(round_half_up(angle)),"answer_format":"integer degrees using half-up rounding"},
        {"question_id":f"{iid}_q5","difficulty_level":5,"question_type":"angle_after_twenty_minutes","question_text":"If 20 minutes were added to the current time, what would the new smaller angle between the hands be, rounded to the nearest degree?","ground_truth":str(round_half_up(new_angle)),"answer_format":"integer degrees using half-up rounding"},
    ]
    difficulty=.28+.12*(minute%5!=0)+.12*(angle.denominator!=1)+.16*(minute>=40)+.12*((hour%12)*60+minute+20>=720)
    return {"id":iid,"image_path":f"images/{iid}.png","canvas_size":[CANVAS,CANVAS],"seed":index,"hour":hour,"minute":minute,"time":f"{hour:02d}:{minute:02d}","hour_angle":float(hour_angle),"hour_angle_fraction":f"{hour_angle.numerator}/{hour_angle.denominator}","minute_angle":float(minute_angle),"minute_angle_fraction":f"{minute_angle.numerator}/{minute_angle.denominator}","angle_between_hands":float(angle),"angle_between_hands_fraction":f"{angle.numerator}/{angle.denominator}","minute_relation_to_six":"before" if minute<30 else "after","after_twenty_minutes":{"hour":new_hour,"minute":new_minute,"time":f"{new_hour:02d}:{new_minute:02d}","hour_angle":float(new_ha),"hour_angle_fraction":f"{new_ha.numerator}/{new_ha.denominator}","minute_angle":float(new_ma),"minute_angle_fraction":f"{new_ma.numerator}/{new_ma.denominator}","angle_between_hands":float(new_angle),"angle_between_hands_fraction":f"{new_angle.numerator}/{new_angle.denominator}"},"difficulty_score":round(min(difficulty,.98),4),"questions":questions}


def endpoint(angle,length,scale=1):
    radians=math.radians(float(angle));cx,cy=CENTER
    return ((cx+length*math.sin(radians))*scale,(cy-length*math.cos(radians))*scale)


def render(scene,destination):
    s=2;image=Image.new("RGB",(CANVAS*s,CANVAS*s),BACKGROUND);draw=ImageDraw.Draw(image)
    def S(p):return tuple(int(round(v*s)) for v in p)
    cx,cy=CENTER
    draw.ellipse(S((cx-RADIUS,cy-RADIUS,cx+RADIUS,cy+RADIUS)),fill="#FFFDF9",outline=INK,width=4*s)
    for tick in range(60):
        angle=math.radians(tick*6);major=tick%5==0;outer=RADIUS-8;inner=RADIUS-(26 if major else 15)
        p1=(cx+inner*math.sin(angle),cy-inner*math.cos(angle));p2=(cx+outer*math.sin(angle),cy-outer*math.cos(angle))
        draw.line([S(p1),S(p2)],fill=INK if major else "#8C989F",width=(4 if major else 2)*s)
    numeral_font=font(28*s,True)
    for number in range(1,13):
        angle=math.radians(number*30);radius=RADIUS-52;x=cx+radius*math.sin(angle);y=cy-radius*math.cos(angle)
        box=draw.textbbox((0,0),str(number),font=numeral_font);draw.text((x*s-(box[2]-box[0])/2,y*s-(box[3]-box[1])/2-2*s),str(number),fill=INK,font=numeral_font)
    ha=Fraction(scene["hour_angle_fraction"]);ma=Fraction(scene["minute_angle_fraction"])
    hour_end=endpoint(ha,HOUR_LENGTH,s);minute_end=endpoint(ma,MINUTE_LENGTH,s)
    # Small rear tails make the pivot and direction visually crisp.
    hour_back=endpoint(ha,-22,s);minute_back=endpoint(ma,-28,s)
    draw.line([hour_back,S(CENTER),hour_end],fill=HOUR_COLOR,width=11*s)
    draw.line([minute_back,S(CENTER),minute_end],fill=MINUTE_COLOR,width=6*s)
    draw.ellipse(S((cx-10,cy-10,cx+10,cy+10)),fill=INK,outline="#FFFDF9",width=2*s)
    image=image.resize((CANVAS,CANVAS),Image.Resampling.LANCZOS);destination.parent.mkdir(parents=True,exist_ok=True);image.save(destination,optimize=True)


def write_dataset(output,count,start,render_images=True):
    output.mkdir(parents=True,exist_ok=True);(output/"images").mkdir(parents=True,exist_ok=True);rows=[]
    for position,index in enumerate(range(start,start+count),1):
        scene=make_scene(index);path=output/scene["image_path"]
        if render_images:render(scene,path)
        elif not path.exists():raise FileNotFoundError(f"metadata-only pass requires {path}")
        rows.append(scene)
        if count>=100 and position%100==0:print(f"{'Rendered' if render_images else 'Processed'} {position}/{count}",flush=True)
    with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
        for row in rows:handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    print(f"Generated {len(rows)} {'images' if render_images else 'metadata rows'} in {output}")


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output-dir",type=Path);p.add_argument("--count",type=int,default=3000);p.add_argument("--start-index",type=int,default=1);p.add_argument("--sample",action="store_true");p.add_argument("--metadata-only",action="store_true");a=p.parse_args();root=Path(__file__).resolve().parent;output=a.output_dir or (root/"sample_test" if a.sample else root);write_dataset(output,5 if a.sample else a.count,a.start_index,not a.metadata_only)


if __name__=="__main__":main()
