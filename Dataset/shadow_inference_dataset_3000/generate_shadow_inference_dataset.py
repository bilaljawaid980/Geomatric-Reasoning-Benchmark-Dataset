from __future__ import annotations
import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw
BG=(26,26,26);GROUND=(142,147,149);FLOOR_TOP=(58,58,58);FLOOR_BOTTOM=(74,74,74);SHADOW=(42,42,42);AA=3
DATASET_VERSION="shadow-inference-2.0.0";AZIMUTH_EXCLUSION_DEGREES=30.0
PALETTE=[("blue",(76,139,181)),("orange",(215,121,65)),("teal",(65,156,148)),("purple",(142,105,178))]
TYPES=("cube","sphere","cone","cylinder")
def direction_bucket(a):
 a=a%360
 return "front" if a>=315 or a<45 else "right" if a<135 else "back" if a<225 else "left"
def shadow_geometry(x,ground,height,width,azimuth,elevation):
 # Top-point projection plus the object's footprint radius gives the full visible cast length.
 projected=height/math.tan(math.radians(elevation))*.55;base=width/2;length=projected+base
 rad=math.radians(azimuth);dx=-math.sin(rad)*length
 # The ground plane is drawn above the baseline. Front/back remain distinguishable by depth compression.
 depth_factor=.14+.26*((math.cos(rad)+1)/2);dy=-depth_factor*length
 endpoint=[round(x+dx,4),round(ground+dy,4)];screen_length=math.hypot(dx,dy)
 return endpoint,round(screen_length,4),round(math.degrees(math.atan2(dy,dx)),4),round(base,4)
def questions(iid,row,rng):
 qs=[{"question_id":iid+"_q1","question_text":"How many objects are casting a shadow in this image?","question_type":"object_count","ground_truth":str(row["num_objects"]),"answer_format":"numeric","difficulty_level":1}]
 if row["has_inconsistent_shadow"]:text="Do all objects in this image appear to be lit by the same light source? Answer yes or no.";typ="same_light_source";gt="no";fmt="yes_no"
 else:text="From which general direction is the light coming — left, right, front, or back? Answer with one word.";typ="light_direction_bucket";gt=direction_bucket(row["light_azimuth_degrees"]);fmt="choice"
 qs.append({"question_id":iid+"_q2","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":2})
 if row["num_objects"]>=2 and rng.random()<.58:
  k=max(range(row["num_objects"]),key=lambda i:row["objects"][i]["shadow_length"]);o=row["objects"][k];text="Which object casts the LONGEST shadow? Answer with that object's color.";typ="longest_shadow";gt=o["color"]
 else:text="Is the light source high in the sky (steep angle) or low near the horizon (shallow angle)? Answer 'high' or 'low'.";typ="light_height_class";gt="high" if row["light_elevation_degrees"]>45 else "low"
 qs.append({"question_id":iid+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"color" if typ=="longest_shadow" else "choice","difficulty_level":3})
 if row["has_inconsistent_shadow"]:
  idx=row["inconsistent_object_index"];text="Which object's shadow does NOT match the lighting direction of the others? Answer with that object's color.";typ="inconsistent_shadow_object";gt=row["objects"][idx]["color"];fmt="color"
 elif rng.random()<.5:text="Estimate the light source's approximate elevation angle above the horizon, rounded to the nearest 15 degrees.";typ="elevation_nearest_15";gt=str(int(math.floor(row["light_elevation_degrees"]/15+.5)*15));fmt="numeric"
 else:text="If the light source moved to the exact opposite direction (180 degrees azimuth rotation), would the shadows lengthen, shorten, or stay the same length?";typ="opposite_azimuth_length_change";gt="same";fmt="choice"
 qs.append({"question_id":iid+"_q4","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":4})
 if int(iid[-4:])%2:text="If the light elevation increased by 20 degrees while remaining below 90 degrees and all object geometry stayed fixed, would each shadow become longer, shorter, or unchanged?";typ="raise_light_elevation";gt="shorter"
 else:text="If the light source moved to the exact opposite direction (180 degrees azimuth rotation), would the shadows lengthen, shorten, or stay the same length?";typ="opposite_azimuth_length_change";gt="same"
 qs.append({"question_id":iid+"_q5","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"choice","difficulty_level":5});return qs
def line(draw,pts,fill,width=1):draw.line([(round(x*AA),round(y*AA)) for x,y in pts],fill=fill,width=max(2,round(width*AA)),joint="curve")
def render_object(d,o,ground):
 x=o["position"][0];h=o["height_px"];w=o["width_px"];c=tuple(o["rgb"]);lw=max(2,round(.8*AA));X=lambda z:round(z*AA)
 if o["type"]=="sphere":d.ellipse((X(x-w/2),X(ground-h),X(x+w/2),X(ground)),outline=c,width=lw)
 elif o["type"]=="cone":line(d,[(x-w/2,ground),(x,ground-h),(x+w/2,ground)],c,.8);d.ellipse((X(x-w/2),X(ground-w*.22),X(x+w/2),X(ground)),outline=c,width=lw)
 elif o["type"]=="cylinder":
  d.rectangle((X(x-w/2),X(ground-h+w*.12),X(x+w/2),X(ground-w*.12)),outline=c,width=lw);d.ellipse((X(x-w/2),X(ground-h),X(x+w/2),X(ground-h+w*.24)),outline=c,width=lw);d.arc((X(x-w/2),X(ground-w*.24),X(x+w/2),X(ground)),0,180,fill=c,width=lw)
 else:
  top=ground-h;off=w*.27;line(d,[(x-w/2,ground),(x+w*.2,ground),(x+w/2,ground-off),(x-w*.2,ground-off),(x-w/2,ground)],c,.8);line(d,[(x-w/2,ground),(x-w/2,top+off),(x-w*.2,top),(x+w/2,top+off),(x+w/2,ground-off)],c,.8);line(d,[(x-w/2,top+off),(x+w*.2,top+off),(x+w/2,top+off)],c,.8);line(d,[(x+w*.2,top+off),(x+w*.2,ground)],c,.8)
def floor_horizon(ground,objects):
 # Put every projected silhouette on the lit floor while retaining a dark sky band.
 return max(18,round(min([ground]+[o["shadow_position"][1]-o["base_radius_px"]*.9 for o in objects])-18))
def render(path,size,ground,objects):
 w,h=size;horizon=floor_horizon(ground,objects);im=Image.new("RGBA",(w*AA,h*AA),BG+(255,));d=ImageDraw.Draw(im,"RGBA")
 for yy in range(horizon*AA,h*AA):
  t=(yy-horizon*AA)/max(1,(h-horizon)*AA-1);c=tuple(round(FLOOR_TOP[k]+(FLOOR_BOTTOM[k]-FLOOR_TOP[k])*t) for k in range(3));d.line((0,yy,w*AA,yy),fill=c+(255,))
 line(d,[(0,horizon),(w,horizon)],GROUND+(105,),.5);line(d,[(24,ground),(w-24,ground)],GROUND+(150,),.45)
 shadow_layer=Image.new("RGBA",im.size,(0,0,0,0));sd=ImageDraw.Draw(shadow_layer,"RGBA")
 for o in objects:
  x=o["position"][0];sx,sy=o["shadow_position"];base=o["base_radius_px"];vx=sx-x;vy=sy-ground
  if o["type"]=="cube":
   p=[(x-base,ground),(x+base,ground),(sx+base*.62,sy),(sx-base*.62,sy)]
  else:
   upper=[];lower=[]
   for k in range(25):
    t=k/24;cx=x+vx*t;cy=ground+vy*t;half=base*.78*math.sin(math.pi*t);upper.append((cx-half,cy));lower.append((cx+half,cy))
   p=upper+list(reversed(lower))
  sd.polygon([(round(px*AA),round(py*AA)) for px,py in p],fill=SHADOW+(150,));line(sd,p+[p[0]],SHADOW+(225,),.8)
 im=Image.alpha_composite(im,shadow_layer);d=ImageDraw.Draw(im,"RGBA")
 for o in objects:render_object(d,o,ground)
 im.convert("RGB").resize(size,Image.Resampling.LANCZOS).save(path)
def rerender_dataset(root):
 root=Path(root);rows=[json.loads(line) for line in (root/'annotations.jsonl').open(encoding='utf8')]
 for i,row in enumerate(rows,1):
  render(root/row['image_path'],tuple(row['canvas_size']),row['ground_y'],row['objects'])
  if i%250==0 or i==len(rows):print(f"Re-rendered {i}/{len(rows)}",flush=True)
def generate_one(i,images):
 rng=random.Random(i);w=rng.randint(650,700);h=rng.randint(350,400);ground=round(h*rng.uniform(.75,.8));inconsistent=rng.random()<.2;n=rng.randint(2,3) if inconsistent else rng.randint(1,3);interval=rng.choice(((40.0,140.0),(220.0,320.0)));az=rng.uniform(*interval);el=rng.uniform(20,70);colors=rng.sample(PALETTE,n);margin=215;xs=[margin+j*(w-2*margin)/(n-1) if n>1 else w/2 for j in range(n)];xs=[x+rng.uniform(-8,8) for x in xs];bad=rng.randrange(n) if inconsistent else None;objects=[]
 for j in range(n):
  typ=rng.choice(TYPES);height=rng.uniform(62,108);width=rng.uniform(48,75);eff=(az+rng.choice((-1,1))*rng.uniform(75,145))%360 if j==bad else az;sp,sl,sa,br=shadow_geometry(xs[j],ground,height,width,eff,el)
  while abs(sp[0]-xs[j])<18:
   eff=(eff+37)%360;sp,sl,sa,br=shadow_geometry(xs[j],ground,height,width,eff,el)
  objects.append({"index":j,"type":typ,"color":colors[j][0],"rgb":list(colors[j][1]),"position":[round(xs[j],4),ground],"height_px":round(height,4),"width_px":round(width,4),"base_radius_px":br,"effective_light_azimuth_degrees":round(eff,4),"shadow_position":sp,"shadow_length":sl,"shadow_screen_angle_degrees":sa,"consistent":j!=bad})
 iid=f"shadow_inference_{i:04d}";render(images/f"{iid}.png",(w,h),ground,objects);row={"id":iid,"dataset_version":DATASET_VERSION,"image_path":f"images/{iid}.png","canvas_size":[w,h],"ground_y":ground,"coordinate_frame":"screen_x_right_screen_y_down","azimuth_convention":"0=front, 90=right, 180=back, 270=left; shadow projects away from light","azimuth_exclusion_degrees":AZIMUTH_EXCLUSION_DEGREES,"light_azimuth_degrees":round(az,4),"light_elevation_degrees":round(el,4),"objects":objects,"num_objects":n,"has_inconsistent_shadow":inconsistent,"inconsistent_object_index":bad,"seed":i,"difficulty_score":round(.2+.16*(n-1)+.34*inconsistent+.15*(el<32)+.15*(n==3),4)};row["questions"]=questions(iid,row,rng);return row
def generate_dataset(n,out):
 out=Path(out);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 with (out/"annotations.jsonl").open("w",encoding="utf8",newline="\n") as f:
  for i in range(1,n+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
   if i%250==0 or i==n:print(f"Generated {i}/{n}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--output-dir",default="shadow_inference_dataset_3000");p.add_argument("--sample",action="store_true");p.add_argument("--rerender-only",action="store_true");a=p.parse_args();rerender_dataset(a.output_dir) if a.rerender_only else generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=="__main__":main()
