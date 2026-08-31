"""Generate deterministic overlapping-circle reasoning datasets."""
from __future__ import annotations
import argparse,json,math,random
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
try:
 from tqdm import tqdm
except ImportError:
 def tqdm(x,**_):return x
BG=(241,239,232,255);FILL=(49,111,123,46);EDGE=(32,82,92,255);AA=3;DATASET_VERSION="overlap-circles-2.0.0"
def circles_overlap(a,b):return math.hypot(a["center"][0]-b["center"][0],a["center"][1]-b["center"][1])<a["radius"]+b["radius"]
def overlap_data(circles):
 pairs=[];degree=Counter()
 for i,a in enumerate(circles):
  for j,b in enumerate(circles[i+1:],i+1):
   if circles_overlap(a,b):pairs.append({"circle_i":i,"circle_j":j});degree[i]+=1;degree[j]+=1
 return pairs,[i for i in range(len(circles)) if degree[i]==0],degree
def compute_max_stack_depth(circles,canvas_size,grid_resolution=2):
 candidates=[tuple(c["center"]) for c in circles]
 for i,a in enumerate(circles):
  x0,y0=a["center"];r0=a["radius"]
  for b in circles[i+1:]:
   x1,y1=b["center"];r1=b["radius"];dx=x1-x0;dy=y1-y0;d=math.hypot(dx,dy)
   if d==0 or d>r0+r1 or d<abs(r0-r1):continue
   along=(r0*r0-r1*r1+d*d)/(2*d);height=math.sqrt(max(0,r0*r0-along*along));mx=x0+along*dx/d;my=y0+along*dy/d
   candidates.extend([(mx-height*dy/d,my+height*dx/d),(mx+height*dy/d,my-height*dx/d)])
 best=max(candidates,key=lambda p:sum(math.dist(p,c["center"])<=c["radius"]+1e-7 for c in circles));depth=sum(math.dist(best,c["center"])<=c["radius"]+1e-7 for c in circles);return depth,[round(best[0],5),round(best[1],5)]
def near_duplicate(a,b):return abs(a["center"][0]-b["center"][0])<3 and abs(a["center"][1]-b["center"][1])<3 and abs(a["radius"]-b["radius"])<3
def generate_geometry(i):
 base=random.Random(i);w=base.randint(400,420);h=base.randint(400,420);n=base.randint(5,12);target_density=(.28,.34,.40,.46,.52)[(i-1)%5];mode="target_density";rejected_depth=0
 for attempt in range(10000):
  rng=random.Random(f"overlap-circles-v2:{i}:{attempt}")
  circles=[];ccx=rng.uniform(w*.42,w*.58);ccy=rng.uniform(h*.42,h*.58)
  for k in range(n):
   r=rng.uniform(w*.10,w*.22)
   margin=r+3
   cx=rng.uniform(margin,w-margin);cy=rng.uniform(margin,h-margin)
   c={"index":k,"center":[round(cx,5),round(cy,5)],"radius":round(r,5)}
   if any(near_duplicate(c,x) for x in circles):break
   circles.append(c)
  if len(circles)!=n:continue
  pairs,isolated,degree=overlap_data(circles);fraction=len(pairs)/(n*(n-1)/2)
  if abs(fraction-target_density)>.065 or len(pairs)>=n*(n-1)/2-1:continue
  depth,loc=compute_max_stack_depth(circles,(w,h))
  if depth>4:rejected_depth+=1;continue
  return rng,(w,h),circles,mode,pairs,isolated,degree,depth,loc,attempt,rejected_depth,target_density
 raise RuntimeError("unable to generate circle arrangement")
def recompute_isolated_after_removal(circles,index):
 remaining=[c for i,c in enumerate(circles) if i!=index];return sum(not any(circles_overlap(c,x) for j,x in enumerate(remaining) if x is not c) for c in remaining)
def questions(iid,row,rng):
 qs=[{"question_id":iid+"_q1","question_text":"How many distinct circles are in this image? Answer with a number in curly brackets, e.g. {8}.","question_type":"total_circle_count","ground_truth":str(row["total_circle_count"]),"answer_format":"numeric","difficulty_level":1}]
 if int(iid[-4:])%2:text="Is there any circle that does not overlap with any other circle? Answer yes or no.";gt="yes" if row["non_overlapping_count"] else "no";typ="has_non_overlapping_circle";fmt="yes_no"
 else:text="How many pairs of circles overlap with each other? Answer with a number in curly brackets, e.g. {10}.";gt=str(row["total_overlapping_pairs"]);typ="overlapping_pair_count";fmt="numeric"
 qs.append({"question_id":iid+"_q2","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":2})
 t=rng.choice(["ratio","depth","distribution"])
 if t=="ratio":text="Which is larger: the biggest circle or the smallest circle? Estimate the ratio of their sizes (diameter), rounded to 1 decimal, e.g. {2.3}.";gt=f"{row['largest_radius']/row['smallest_radius']:.1f}";typ="largest_smallest_ratio";fmt={"type":"numeric_tolerance","absolute_tolerance":0.1}
 elif t=="depth":text="Roughly how many circles overlap at the most densely overlapped point in the image? Answer with a number in curly brackets, e.g. {4}.";gt=str(row["max_stack_depth"]);typ="max_stack_depth";fmt="numeric"
 else:text="Are the circles clustered tightly in one area, or spread evenly across the whole image? Answer 'clustered' or 'spread'.";gt=row["generation_mode"];typ="cluster_distribution";fmt="choice"
 qs.append({"question_id":iid+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":3})
 t=rng.choice(["remove","average","percentage"])
 if t=="remove":text="If you removed the largest circle from the image, how many circles would remain that don't overlap with any other circle? Answer with a number in curly brackets.";gt=str(row["isolated_after_largest_removal"]);typ="isolated_after_largest_removal"
 elif t=="average":text="How many circles have a radius larger than the average radius of all circles in this image? Answer with a number in curly brackets.";gt=str(row["above_average_radius_count"]);typ="above_average_radius_count"
 else:text="Estimate what percentage of circles in this image overlap with at least 3 other circles. Answer as a whole number percentage in curly brackets, e.g. {40}.";gt=str(row["three_plus_overlap_percent"]);typ="three_plus_overlap_percent"
 qs.append({"question_id":iid+"_q4","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"numeric","difficulty_level":4})
 qs.append({"question_id":iid+"_q5","question_text":"If the largest circle were removed, how many overlapping circle-pairs would remain?","question_type":"remove_largest_overlap_pairs","ground_truth":str(row["overlapping_pairs_after_largest_removal"]),"answer_format":"numeric","difficulty_level":5});return qs
def render(path,size,circles,line_width):
 w,h=size;im=Image.new("RGBA",(w*AA,h*AA),BG)
 for c in circles:
  cx,cy=c["center"];r=c["radius"];box=[(cx-r)*AA,(cy-r)*AA,(cx+r)*AA,(cy+r)*AA];layer=Image.new("RGBA",im.size,(0,0,0,0));d=ImageDraw.Draw(layer);d.ellipse(box,fill=FILL,outline=EDGE,width=max(2,round(line_width*AA)));im=Image.alpha_composite(im,layer)
 im.convert("RGB").resize((w,h),Image.Resampling.LANCZOS).save(path,"PNG")
def generate_one(i,images):
 rng,size,circles,mode,pairs,isolated,degree,depth,loc,attempt,rejected_depth,target_density=generate_geometry(i);radii=[c["radius"] for c in circles];largest=max(range(len(circles)),key=lambda x:radii[x]);smallest=min(range(len(circles)),key=lambda x:radii[x]);mean=sum(radii)/len(radii);line_width=round(rng.uniform(1,1.5),2);iid=f"overlap_circles_{i:04d}";render(images/f"{iid}.png",size,circles,line_width);remaining_pairs=[p for p in pairs if p["circle_i"]!=largest and p["circle_j"]!=largest];row={"dataset_version":DATASET_VERSION,"geometry_frame":"canvas pixel coordinates; centres and radii share this frame","generation_attempt":attempt,"rejections_max_stack_depth":rejected_depth,"target_overlap_density":target_density,"overlap_density":len(pairs)/(len(circles)*(len(circles)-1)/2),"id":iid,"image_path":f"images/{iid}.png","canvas_size":list(size),"total_circle_count":len(circles),"pairwise_overlaps":pairs,"total_overlapping_pairs":len(pairs),"non_overlapping_circles":isolated,"non_overlapping_count":len(isolated),"largest_circle_index":largest,"smallest_circle_index":smallest,"largest_radius":radii[largest],"smallest_radius":radii[smallest],"max_stack_depth":depth,"max_stack_location":loc,"generation_mode":mode,"line_width_px":line_width,"seed":i,"circles":circles,"isolated_after_largest_removal":recompute_isolated_after_removal(circles,largest),"overlapping_pairs_after_largest_removal":len(remaining_pairs),"above_average_radius_count":sum(r>mean for r in radii),"three_plus_overlap_percent":round(100*sum(degree[x]>=3 for x in range(len(circles)))/len(circles))};variance=float(np.var(radii));row["difficulty_score"]=round(min(1,.35*(len(circles)-5)/7+.3*row["overlap_density"]+.25*(depth-1)/3+.1*min(1,variance/1500)),4);row["questions"]=questions(iid,row,rng);return row
def generate_dataset(n=3000,output_dir="overlap_circles_dataset",start=1):
 out=Path(output_dir);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 mode="a" if start>1 else "w"
 with (out/"annotations.jsonl").open(mode,encoding="utf-8",newline="\n") as f:
  for i in tqdm(range(start,n+1),desc="Generating overlap circles"):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
 from validate_overlap_circles_dataset import validate;checked,issues=validate(out);assert not issues,issues[:10];print(f"Validated {checked} images in {out.resolve()}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--start",type=int,default=1);p.add_argument("--output-dir",default="overlap_circles_dataset");p.add_argument("--sample",action="store_true");a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir,a.start)
if __name__=="__main__":main()
