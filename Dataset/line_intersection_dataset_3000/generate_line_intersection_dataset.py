"""Generate deterministic red/blue polyline intersection datasets."""
from __future__ import annotations
import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw
try:
 from tqdm import tqdm
except ImportError:
 def tqdm(x,**_):return x
BG="#FDFBF6";RED="#D7192D";BLUE="#1769B0";AA=3;EPS=1e-9
def segment_intersection(p1,p2,p3,p4):
 x1,y1=p1;x2,y2=p2;x3,y3=p3;x4,y4=p4;rx=x2-x1;ry=y2-y1;sx=x4-x3;sy=y4-y3;den=rx*sy-ry*sx
 if abs(den)<EPS:return None
 qx=x3-x1;qy=y3-y1;t=(qx*sy-qy*sx)/den;u=(qx*ry-qy*rx)/den
 if -EPS<=t<=1+EPS and -EPS<=u<=1+EPS:return (x1+t*rx,y1+t*ry,t,u)
 return None
def compute_intersections(red,blue,reject_degenerate=False):
 out=[]
 for i,(a,b) in enumerate(zip(red,red[1:])):
  for j,(c,d) in enumerate(zip(blue,blue[1:])):
   hit=segment_intersection(a,b,c,d)
   if hit is None:continue
   x,y,t,u=hit
   if t<=1e-7 or t>=1-1e-7 or u<=1e-7 or u>=1-1e-7:
    if reject_degenerate:raise ValueError("endpoint intersection")
    continue
   out.append({"x":round(x,6),"y":round(y,6),"red_segment_index":i,"blue_segment_index":j})
 unique=[]
 for p in sorted(out,key=lambda q:(q["x"],q["y"])):
  if not unique or abs(p["x"]-unique[-1]["x"])>1e-6 or abs(p["y"]-unique[-1]["y"])>1e-6:unique.append(p)
 return unique
def is_self_intersecting(points):
 for i in range(len(points)-1):
  for j in range(i+2,len(points)-1):
   if i==0 and j==len(points)-2:continue
   if segment_intersection(points[i],points[i+1],points[j],points[j+1]):return True
 return False
def generate_geometry(i):
 rng=random.Random(i);w=rng.randint(500,530);h=rng.randint(390,410);n=3 if rng.random()<.4 else rng.randint(4,6);segments=n-1;target=rng.randint(0,segments);xs=[55+k*(w-110)/(n-1) for k in range(n)]
 # Choose exactly target flip locations in the sign of red-blue separation.
 flips=set(rng.sample(range(1,n),target));sign=rng.choice([-1,1]);signs=[sign]
 for k in range(1,n):
  if k in flips:sign=-sign
  signs.append(sign)
 blue=[];red=[]
 for k,x in enumerate(xs):
  by=rng.uniform(95,h-95);gap=rng.uniform(30,70);ry=by+signs[k]*gap
  if ry<35:by+=35-ry;ry=35
  if ry>h-35:by-=ry-(h-35);ry=h-35
  blue.append([round(x,6),round(by,6)]);red.append([round(x,6),round(ry,6)])
 intersections=compute_intersections(red,blue,True);assert len(intersections)==target
 return rng,(w,h),red,blue,intersections
def questions(iid,meta,rng):
 if rng.random()<.5:text="How many line segments make up the red line?";gt=str(meta["num_red_segments"]);typ="red_segment_count"
 else:text="How many line segments make up the blue line?";gt=str(meta["num_blue_segments"]);typ="blue_segment_count"
 qs=[{"question_id":iid+"_q1","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"numeric","difficulty_level":1}]
 if rng.random()<.5:text="How many times do the blue and red lines touch each other? Answer with a number in curly brackets, e.g. {5}.";variant="touch_each_other"
 else:text="Count the intersection points where the blue and red lines meet. Put your answer in curly brackets, e.g. {2}.";variant="intersection_points"
 meta["wording_variant"]=variant;qs.append({"question_id":iid+"_q2","question_text":text,"question_type":"intersection_count","ground_truth":str(meta["total_intersections"]),"answer_format":"numeric","difficulty_level":2})
 choices=["start","end"]+(["leftmost"] if meta["total_intersections"] else []);t=rng.choice(choices)
 if t=="start":text="At the leftmost point of the image, which line is higher: red or blue?";gt="red" if meta["red_above_blue_at_start"] else "blue";typ="higher_at_start";fmt="color"
 elif t=="end":text="Does the red line end above or below the blue line at the rightmost point?";gt="above" if meta["red_above_blue_at_end"] else "below";typ="red_end_relation";fmt="choice"
 else:text="Is the leftmost intersection point closer to the left edge or the right edge of the image? Answer 'left' or 'right'.";gt="left" if meta["leftmost_intersection_x"]<meta["canvas_size"][0]/2 else "right";typ="leftmost_intersection_side";fmt="choice"
 qs.append({"question_id":iid+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":3})
 t=rng.choice(["parity","halves","remove"])
 if t=="parity":text="If the two lines intersect an odd number of times, the line that starts higher must end lower (and vice versa). Based on this rule, do these two lines intersect an odd or even number of times? Answer 'odd' or 'even'.";gt="odd" if meta["crossed_from_above_to_below"] else "even";typ="intersection_parity";fmt="choice"
 elif t=="halves":text="How many intersection points occur in the left half of the image versus the right half? Answer as two numbers separated by a comma, e.g. {2,1}.";left=sum(p["x"]<meta["canvas_size"][0]/2 for p in meta["intersections"]);gt=f"{left},{meta['total_intersections']-left}";typ="intersection_half_counts";fmt="numeric_pair"
 else:text="If you removed the segment of the red line closest to the left edge, how many intersection points would remain? Answer with a number in curly brackets.";gt=str(meta["total_intersections"]-sum(p["red_segment_index"]==0 for p in meta["intersections"]));typ="remove_first_red_segment";fmt="numeric"
 qs.append({"question_id":iid+"_q4","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":4});return qs
def render(path,size,red,blue):
 w,h=size;im=Image.new("RGB",(w*AA,h*AA),BG);d=ImageDraw.Draw(im);d.line([(x*AA,y*AA) for x,y in red],fill=RED,width=6,joint="curve");d.line([(x*AA,y*AA) for x,y in blue],fill=BLUE,width=6,joint="curve");im.resize((w,h),Image.Resampling.LANCZOS).save(path,"PNG")
def generate_one(i,images):
 rng,size,red,blue,ints=generate_geometry(i);iid=f"line_intersect_{i:04d}";render(images/f"{iid}.png",size,red,blue);total=len(ints);meta={"canvas_size":list(size),"num_red_segments":len(red)-1,"num_blue_segments":len(blue)-1,"total_intersections":total,"intersections":ints,"leftmost_intersection_x":ints[0]["x"] if ints else None,"rightmost_intersection_x":ints[-1]["x"] if ints else None,"red_above_blue_at_start":red[0][1]<blue[0][1],"red_above_blue_at_end":red[-1][1]<blue[-1][1],"crossed_from_above_to_below":(red[0][1]<blue[0][1])!=(red[-1][1]<blue[-1][1]),"red_self_intersecting":is_self_intersecting(red),"blue_self_intersecting":is_self_intersecting(blue),"seed":i,"red_points":red,"blue_points":blue};difficulty=round(min(1,.45*total/5+.35*((len(red)-1)+(len(blue)-1)-4)/6+.2*(total>2)),4);row={"id":iid,"image_path":f"images/{iid}.png",**meta,"difficulty_score":difficulty};row["questions"]=questions(iid,row,rng);return row
def generate_dataset(n=3000,output_dir="line_intersection_dataset"):
 out=Path(output_dir);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 with (out/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as f:
  for i in tqdm(range(1,n+1),desc="Generating line intersections"):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
 from validate_line_intersect_dataset import validate;checked,issues=validate(out);assert not issues,issues[:10];print(f"Validated {checked} images in {out.resolve()}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--output-dir",default="line_intersection_dataset");p.add_argument("--sample",action="store_true");a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=="__main__":main()
