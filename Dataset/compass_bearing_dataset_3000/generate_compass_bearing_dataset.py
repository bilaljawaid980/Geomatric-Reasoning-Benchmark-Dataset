"""Generate deterministic compass-bearing and map-navigation puzzles."""
from __future__ import annotations
import argparse,json,math,random
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BACKGROUND="#FDFAF4";MAP_FILL="#FFFDF9";INK="#1D3B4F";MUTED="#73808A";LANDMARK="#B6423C";PATH="#147D78"

def font(size,bold=False):
 try:return ImageFont.truetype(str(Path("C:/Windows/Fonts")/("arialbd.ttf" if bold else "arial.ttf")),size)
 except OSError:return ImageFont.load_default()
def compute_bearing(point_from,point_to):
 dx=point_to[0]-point_from[0];north=point_from[1]-point_to[1];return math.degrees(math.atan2(dx,north))%360
def compute_distance(a,b):return math.hypot(b[0]-a[0],b[1]-a[1])
def point_segment_distance(point,start,end):
 dx,dy=end[0]-start[0],end[1]-start[1];length_sq=dx*dx+dy*dy
 if not length_sq:return compute_distance(point,start)
 t=max(0,min(1,((point[0]-start[0])*dx+(point[1]-start[1])*dy)/length_sq));projection=[start[0]+t*dx,start[1]+t*dy];return compute_distance(point,projection)
def compute_turn_angle(bearing1,bearing2):
 clockwise=(bearing2-bearing1)%360
 if abs(clockwise-180)<1e-10:return 180.0,"either"
 return (clockwise,"clockwise") if clockwise<180 else (360-clockwise,"counterclockwise")
def project_point(origin,bearing,distance):
 radians=math.radians(bearing);return [origin[0]+distance*math.sin(radians),origin[1]-distance*math.cos(radians)]
def round_half_up(value):return int(math.floor(value+0.5))
def rounded_bearing(value):return (round_half_up(value/10)*10)%360
def bearing_text(value):return f"{value:03d}"
def make_landmarks(rng,canvas,count):
 for _ in range(300):
  points=[]
  for _label in range(count):
   for _attempt in range(200):
    point=[rng.randint(72,canvas-72),rng.randint(72,canvas-72)]
    if point[0]>canvas-205 and point[1]<175:continue
    if all(compute_distance(point,other)>=82 for other in points):points.append(point);break
   else:break
  if len(points)==count:return {chr(65+i):points[i] for i in range(count)}
 raise RuntimeError("could not place landmarks")
def derive_level5(landmarks,origin_label,reference_label,given_bearing):
 origin=landmarks[origin_label];distance=compute_distance(origin,landmarks[reference_label]);projected=project_point(origin,given_bearing,distance);candidates=[label for label in landmarks if label!=origin_label];distances={label:compute_distance(projected,landmarks[label]) for label in candidates};ordered=sorted(candidates,key=lambda label:(distances[label],label));winner=ordered[0];margin=distances[ordered[1]]-distances[winner];bearing_difference=abs((compute_bearing(origin,landmarks[winner])-given_bearing+180)%360-180)
 return projected,distances,winner,margin,bearing_difference
def build_scene(index):
 rng=random.Random(index);canvas=rng.randint(500,550);count=3+(index%2);labels=[chr(65+i) for i in range(count)];has_path=index%4 in (0,1)
 for scene_attempt in range(100):
  landmarks=make_landmarks(rng,canvas,count)
  l2_x,l2_y=rng.sample(labels,2)
  if index%10==0:
   landmarks[l2_y][1]=landmarks[l2_x][1]
   if any(compute_distance(landmarks[l2_y],landmarks[label])<70 for label in labels if label!=l2_y):continue
  elif abs(landmarks[l2_y][1]-landmarks[l2_x][1])<=5:continue
  l3_x,l3_y=rng.sample(labels,2)
  triples=list(__import__('itertools').permutations(labels,3));rng.shuffle(triples);l4=None
  for x,y,z in triples:
   angle,direction=compute_turn_angle(compute_bearing(landmarks[x],landmarks[y]),compute_bearing(landmarks[x],landmarks[z]))
   if 3<=angle<=177:l4=(x,y,z,angle,direction);break
  if l4 is None:continue
  l5_x,l5_y=rng.sample(labels,2);offset=rng.choice((-120,-90,-60,-30,30,60,90,120));given=(round_half_up(compute_bearing(landmarks[l5_x],landmarks[l5_y]))+offset)%360;projected,projected_distances,winner,margin,bearing_diff=derive_level5(landmarks,l5_x,l5_y,given)
  if margin<18:continue
  if has_path:
   path_pairs=[(a,b) for a in labels for b in labels if a!=b and all(point_segment_distance(landmarks[other],landmarks[a],landmarks[b])>=38 for other in labels if other not in (a,b))];rng.shuffle(path_pairs)
   if not path_pairs:continue
   path_start,path_end=path_pairs[0]
  else:path_start=path_end=None
  break
 else:raise RuntimeError(f"could not create safe scene {index}")
 bearings={f"{a}-to-{b}":round(compute_bearing(landmarks[a],landmarks[b]),8) for a in labels for b in labels if a!=b};distances={f"{a}-{b}":round(compute_distance(landmarks[a],landmarks[b]),8) for i,a in enumerate(labels) for b in labels[i+1:]}
 path_bearing=compute_bearing(landmarks[path_start],landmarks[path_end]) if has_path else None
 l2_delta=landmarks[l2_y][1]-landmarks[l2_x][1];l2_answer="same latitude" if abs(l2_delta)<=5 else ("north" if l2_delta<0 else "south")
 l3_answer=bearing_text(rounded_bearing(compute_bearing(landmarks[l3_x],landmarks[l3_y])))
 x,y,z,turn,turn_direction=l4;turn_answer=f"{round_half_up(turn)} degrees {turn_direction}"
 endpoint_distance=projected_distances[winner];level5_answer=f"{winner}; projected endpoint is closest to {winner} ({endpoint_distance:.1f} map units away; bearing difference {bearing_diff:.1f} degrees)"
 iid=f"compass_bearing_{index:04d}";candidate_text=", ".join(label for label in labels if label!=l5_x)
 questions=[
  {"question_id":f"{iid}_q1","difficulty_level":1,"question_type":"landmark_count","question_text":"How many landmarks are shown on this map?","ground_truth":str(count),"answer_format":"integer"},
  {"question_id":f"{iid}_q2","difficulty_level":2,"question_type":"north_south_relation","question_text":f"Is landmark {l2_y} located north or south of landmark {l2_x}? Answer 'north', 'south', or 'same latitude'.","ground_truth":l2_answer,"answer_format":"north, south, or same latitude"},
  {"question_id":f"{iid}_q3","difficulty_level":3,"question_type":"rounded_compass_bearing","question_text":f"What is the compass bearing from landmark {l3_x} to landmark {l3_y}, rounded to the nearest 10 degrees? Answer with a three-digit number in curly brackets, e.g. {{045}}.","ground_truth":l3_answer,"answer_format":"three-digit bearing in curly brackets"},
  {"question_id":f"{iid}_q4","difficulty_level":4,"question_type":"turn_angle_direction","question_text":f"If you are standing at landmark {x} facing landmark {y}, and then turn to face landmark {z} instead, how many degrees would you need to turn, and in which direction? Round the angle to the nearest degree and answer with the amount plus 'clockwise' or 'counterclockwise'.","ground_truth":turn_answer,"answer_format":"integer degrees plus direction"},
  {"question_id":f"{iid}_q5","difficulty_level":5,"question_type":"counterfactual_bearing_projection","question_text":f"If you traveled from landmark {l5_x} along a bearing of {given:03d} degrees for the same distance as {l5_x}-to-{l5_y}, which of these landmarks would the projected endpoint be closest to: {candidate_text}? Give the letter and briefly justify using endpoint distance and bearing difference.","ground_truth":level5_answer,"answer_format":"letter; endpoint distance and bearing difference"},]
 return {"id":iid,"image_path":f"images/{iid}.png","canvas_size":[canvas,canvas],"seed":index,"landmarks":landmarks,"num_landmarks":count,"all_pairwise_bearings":bearings,"all_pairwise_distances":distances,"distance_unit":"abstract map units","has_path":has_path,"path_start":path_start,"path_end":path_end,"path_bearing":None if path_bearing is None else round(path_bearing,8),"level2_pair":{"X":l2_x,"Y":l2_y,"same_latitude_tolerance_px":5},"level3_pair":{"X":l3_x,"Y":l3_y},"level4_triple":{"X":x,"Y":y,"Z":z,"bearing_XY":round(compute_bearing(landmarks[x],landmarks[y]),8),"bearing_XZ":round(compute_bearing(landmarks[x],landmarks[z]),8),"turn_angle":round(turn,8),"turn_direction":turn_direction},"level5_projection":{"X":l5_x,"Y":l5_y,"given_bearing":given,"travel_distance":round(compute_distance(landmarks[l5_x],landmarks[l5_y]),8),"projected_point":[round(v,8) for v in projected],"candidate_distances":{k:round(v,8) for k,v in projected_distances.items()},"nearest_landmark":winner,"nearest_margin":round(margin,8),"winner_bearing_difference":round(bearing_diff,8)},"difficulty_score":round(.35+.1*(count-3)+.08*has_path+.14*(l2_answer=="same latitude")+.18*(turn>120)+.12*(margin<35),4),"generation_attempt":scene_attempt,"questions":questions}
def draw_dashed_arrow(draw,start,end,scale):
 dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
 for begin in range(10,max(11,int(length)-14),18):
  finish=min(begin+10,length-15);draw.line([(round((start[0]+ux*begin)*scale),round((start[1]+uy*begin)*scale)),(round((start[0]+ux*finish)*scale),round((start[1]+uy*finish)*scale))],fill=PATH,width=3*scale)
 angle=math.atan2(dy,dx);tip=(end[0]-ux*9,end[1]-uy*9);left=(tip[0]-15*math.cos(angle-.55),tip[1]-15*math.sin(angle-.55));right=(tip[0]-15*math.cos(angle+.55),tip[1]-15*math.sin(angle+.55));draw.polygon([(round(tip[0]*scale),round(tip[1]*scale)),(round(left[0]*scale),round(left[1]*scale)),(round(right[0]*scale),round(right[1]*scale))],fill=PATH)
def render(scene,destination):
 scale=2;canvas=scene["canvas_size"][0];image=Image.new("RGB",(canvas*scale,canvas*scale),BACKGROUND);draw=ImageDraw.Draw(image);S=lambda p:tuple(round(v*scale) for v in p)
 draw.rounded_rectangle([S((24,24)),S((canvas-24,canvas-24))],radius=12*scale,fill=MAP_FILL,outline=INK,width=2*scale)
 cx,cy=canvas-90,88;draw.ellipse([S((cx-38,cy-38)),S((cx+38,cy+38))],outline=MUTED,width=2*scale);draw.line([S((cx,cy+30)),S((cx,cy-30))],fill=INK,width=3*scale);draw.polygon([S((cx,cy-36)),S((cx-6,cy-22)),S((cx+6,cy-22))],fill=INK);draw.line([S((cx-30,cy)),S((cx+30,cy))],fill=MUTED,width=2*scale)
 rose_font=font(13*scale,True)
 for text,point in (("N",(cx,cy-50)),("S",(cx,cy+50)),("W",(cx-50,cy)),("E",(cx+50,cy))):draw.text(S(point),text,fill=INK,font=rose_font,anchor="mm")
 if scene["has_path"]:draw_dashed_arrow(draw,scene["landmarks"][scene["path_start"]],scene["landmarks"][scene["path_end"]],scale)
 label_font=font(17*scale,True)
 for label,point in scene["landmarks"].items():
  x,y=point;draw.ellipse([S((x-7,y-7)),S((x+7,y+7))],fill=LANDMARK,outline="#7F2625",width=2*scale);draw.text(S((x+16,y-15)),label,fill=INK,font=label_font,anchor="mm")
 image.resize((canvas,canvas),Image.Resampling.LANCZOS).save(destination,"PNG",optimize=True)
def generate(output,count,start_index,render_images=True):
 output.mkdir(parents=True,exist_ok=True);images=output/"images";images.mkdir(exist_ok=True);records=[]
 for position,index in enumerate(range(start_index,start_index+count),1):
  row=build_scene(index);records.append(row)
  if render_images:render(row,images/Path(row["image_path"]).name)
  if render_images and (position%100==0 or position==count):print(f"Rendered {position}/{count}",flush=True)
 with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for row in records:h.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
 stats={"images":len(records),"landmark_counts":dict(Counter(r["num_landmarks"] for r in records)),"path_presence":dict(Counter(r["has_path"] for r in records)),"same_latitude_cases":sum(r["questions"][1]["ground_truth"]=="same latitude" for r in records)};(output/"generation_stats.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8");print(json.dumps(stats,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument("--count",type=int,default=3000);p.add_argument("--start-index",type=int,default=1);p.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent);p.add_argument("--metadata-only",action="store_true");p.add_argument("--sample",action="store_true");a=p.parse_args()
 if a.sample:a.output_dir=Path(__file__).resolve().parent/"sample_test";a.count=5
 generate(a.output_dir,a.count,a.start_index,not a.metadata_only)
if __name__=="__main__":main()
