"""Generate clean colored-route visual reasoning puzzles.

Examples:
  python generate_route_dataset.py --sample --output-dir route_dataset_sample
  python generate_route_dataset.py --n 3000 --output-dir route_dataset_3000
"""
from __future__ import annotations
import argparse,json,math,random
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
try:
 from tqdm import tqdm
except ImportError:
 def tqdm(x,**_):return x

BG="#FDFAF4";INK="#101719";SCALE=3;GRID=15
COLORS=[("teal","#009E9A"),("orange","#F05A17"),("blue","#0878BD"),("green","#149B43"),("red","#D7192D"),("purple","#9256C2"),("brown","#7A4938"),("amber","#C77A00"),("magenta","#D51A78"),("cyan","#00A8C2"),("olive","#799514"),("gray-blue","#557383")]

def font(size):
 for p in (r"C:\Windows\Fonts\arialbd.ttf",r"C:\Windows\Fonts\segoeuib.ttf","DejaVuSans-Bold.ttf"):
  try:return ImageFont.truetype(p,size)
  except OSError:pass
 return ImageFont.load_default()

def assign_endpoints(num_endpoints,canvas_size):
 """Place sequential labels evenly around an inset rectangular perimeter."""
 w,h=canvas_size;m=64;rw=w-2*m;rh=h-2*m;per=2*(rw+rh);start=rw/2;out={}
 for i in range(num_endpoints):
  d=(start+i*per/num_endpoints)%per;letter=chr(65+i)
  if d<rw:point=(m+d,m);side="top"
  elif d<rw+rh:point=(w-m,m+d-rw);side="right"
  elif d<2*rw+rh:point=(w-m-(d-rw-rh),h-m);side="bottom"
  else:point=(m,h-m-(d-2*rw-rh));side="left"
  out[letter]={"anchor":[round(point[0]),round(point[1])],"side":side}
 return out

def port_point(info,index,total):
 x,y=info["anchor"];offset=(index-(total-1)/2)*10
 if info["side"] in ("top","bottom"):x+=offset
 else:y+=offset
 return (round(x),round(y))

def compatible_bends(start_side,end_side,rng):
 first="V" if start_side in ("top","bottom") else "H";last="V" if end_side in ("top","bottom") else "H"
 valid=[b for b in range(3,9) if (first if b%2==0 else ("H" if first=="V" else "V"))==last]
 return rng.choice(valid)

def generate_route(start_point,end_point,canvas_bounds,num_bends,start_side="top",rng=None):
 """Return an orthogonal snapped polyline with exactly num_bends turns."""
 rng=rng or random;left,top,right,bottom=canvas_bounds;first="V" if start_side in ("top","bottom") else "H"
 for _ in range(100):
  pts=[tuple(start_point)];orient=first
  for k in range(num_bends):
   x,y=pts[-1];last_bend=k==num_bends-1
   if orient=="H":nx=(end_point[0] if last_bend else rng.randrange(math.ceil(left/GRID),math.floor(right/GRID)+1)*GRID);p=(nx,y)
   else:ny=(end_point[1] if last_bend else rng.randrange(math.ceil(top/GRID),math.floor(bottom/GRID)+1)*GRID);p=(x,ny)
   if p==pts[-1]:break
   pts.append(p);orient="V" if orient=="H" else "H"
  else:
   if pts[-1]!=tuple(end_point):pts.append(tuple(end_point))
   if len(pts)==num_bends+2 and all(pts[k]!=pts[k+1] for k in range(len(pts)-1)):return pts
 raise RuntimeError("could not construct orthogonal route")

def segments(points):return list(zip(points,points[1:]))
def compute_crossings(routes):
 total=0
 for i,a in enumerate(routes):
  for b in routes[i+1:]:
   for p,q in segments(a["points"]):
    for r,s in segments(b["points"]):
     ah=p[1]==q[1];bh=r[1]==s[1]
     if ah==bh:continue
     hp,hq,vp,vq=(p,q,r,s) if ah else (r,s,p,q)
     if min(hp[0],hq[0])<vp[0]<max(hp[0],hq[0]) and min(vp[1],vq[1])<hp[1]<max(vp[1],vq[1]):total+=1
 return total

def render(path,size,endpoints,routes,line_width):
 w,h=size;im=Image.new("RGB",(w*SCALE,h*SCALE),BG);d=ImageDraw.Draw(im)
 for route in routes:d.line([(int(x*SCALE),int(y*SCALE)) for x,y in route["points"]],fill=route["hex"],width=max(3,round(line_width*SCALE)),joint="curve")
 f=font(39*SCALE)
 for letter,info in endpoints.items():
  x,y=info["anchor"];side=info["side"]
  if side=="top":pos=(x,y-39)
  elif side=="bottom":pos=(x,y+38)
  elif side=="left":pos=(x-39,y)
  else:pos=(x+39,y)
  box=d.textbbox((0,0),letter,font=f);tw,th=box[2]-box[0],box[3]-box[1]
  d.text((pos[0]*SCALE-tw/2,pos[1]*SCALE-th/2-box[1]),letter,font=f,fill=INK)
 im.resize((w,h),Image.Resampling.LANCZOS).save(path,"PNG")

def unordered(a,b):return "".join(sorted((a,b)))
def questions_for(image_id,letters,routes,rng):
 counts=Counter(unordered(r["start"],r["end"]) for r in routes if r["start"]!=r["end"]);all_pairs=[letters[i]+letters[j] for i in range(len(letters)) for j in range(i+1,len(letters))];degree=Counter()
 for r in routes:degree[r["start"]]+=1;degree[r["end"]]+=1
 # Level 1
 if rng.random()<.5:text="How many distinct colored routes are visible in this image?";gt=str(len(routes));typ="num_routes_visible"
 else:text="How many labeled endpoints (letters) are shown in this image?";gt=str(len(letters));typ="num_labeled_endpoints"
 q1={"question_id":image_id+"_q1","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"numeric","difficulty_level":1}
 # Level 2
 zero=[p for p in all_pairs if counts[p]==0]
 if rng.random()<.15 and zero:pair=rng.choice(zero)
 else:pair=rng.choice([p for p in all_pairs if counts[p]>0])
 q2={"question_id":image_id+"_q2","question_text":f"Count the one-colored routes that go from {pair[0]} to {pair[1]}. Answer with a number in curly brackets e.g. {{1}}","question_type":"count_routes_between_pair","ground_truth":str(counts[pair]),"answer_format":"numeric","difficulty_level":2}
 # Level 3: random preferred template with unambiguous fallbacks.
 max_degree=max(degree[x] for x in letters);degree_winners=[x for x in letters if degree[x]==max_degree];max_pair=max(counts[p] for p in all_pairs);pair_winners=[p for p in all_pairs if counts[p]==max_pair];preferred=rng.choice(["letter","pair","degree"])
 if preferred=="letter" and len(degree_winners)==1:text="Which letter has the most routes connected to it?";gt=degree_winners[0];typ="highest_degree_letter";fmt="letter"
 elif preferred in ("letter","pair") and len(pair_winners)==1:text="Which two letters have the most routes directly connecting them?";gt=pair_winners[0];typ="most_connected_pair";fmt="letter_pair"
 else:x=rng.choice(letters);text=f"How many routes does letter {x} have in total (i.e. touching {x})?";gt=str(degree[x]);typ="letter_degree";fmt="numeric"
 q3={"question_id":image_id+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":3}
 # Level 4
 choice=rng.choice(["single","zero","ordering"])
 if choice=="single":text="List all letter-pairs that have exactly one connecting route between them.";gt=sorted(p for p in all_pairs if counts[p]==1);typ="single_route_pairs";fmt="list"
 elif choice=="zero":text="Is there any letter-pair with zero directly connecting routes? If yes, name one such pair; if no, answer 'none'.";gt=(rng.choice(zero) if zero else "none");typ="zero_connection_pair";fmt="letter_pair"
 else:
  text="Among all letters, list them in order from most connected routes to least connected routes.";freq=Counter(degree[x] for x in letters);gt=[f"{x} (degree {degree[x]}{'—tie' if freq[degree[x]]>1 else ''})" for x in sorted(letters,key=lambda x:(-degree[x],x))];typ="degree_ordering";fmt="list"
 q4={"question_id":image_id+"_q4","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":4};return [q1,q2,q3,q4]

def generate_one(index,images_dir):
 rng=random.Random(index);size=(rng.randint(582,600),rng.randint(582,600));nend=rng.randint(4,6);letters=[chr(65+i) for i in range(nend)];endpoints=assign_endpoints(nend,size);nroute=rng.randint(6,12);palette=rng.sample(COLORS,nroute);thin=rng.random()<.20;line_width=round(rng.uniform(1,1.5) if thin else rng.uniform(2.5,3),2)
 pairs=[]
 for j in range(nroute):
  if j==0 and rng.random()<.05:a=b=rng.choice(letters)
  else:a,b=rng.sample(letters,2)
  pairs.append((a,b))
 totals=Counter(x for p in pairs for x in p);used=Counter();routes=[];bounds=(92,92,size[0]-92,size[1]-92)
 for j,((a,b),(name,hx)) in enumerate(zip(pairs,palette)):
  sp=port_point(endpoints[a],used[a],totals[a]);used[a]+=1;ep=port_point(endpoints[b],used[b],totals[b]);used[b]+=1;bends=compatible_bends(endpoints[a]["side"],endpoints[b]["side"],rng)
  pts=generate_route(sp,ep,bounds,bends,endpoints[a]["side"],rng);routes.append({"color":name,"hex":hx,"start":a,"end":b,"num_bends":bends,"line_width":line_width,"points":[list(p) for p in pts]})
 cross=compute_crossings(routes);avg=sum(r["num_bends"] for r in routes)/nroute;difficulty=min(1,round(.22*(nroute-6)/6+.13*(nend-4)/2+.20*(avg-3)/5+.15*(3-line_width)/2+.30*min(cross,60)/60,4));iid=f"route_puzzle_{index:04d}";render(images_dir/f"{iid}.png",size,endpoints,routes,line_width)
 return {"id":iid,"image_path":f"images/{iid}.png","canvas_size":list(size),"num_endpoints":nend,"endpoint_letters":letters,"num_routes":nroute,"colors_used":[r["color"] for r in routes],"line_width_px":line_width,"seed":index,"routes":routes,"crossing_count":cross,"difficulty_score":difficulty,"questions":questions_for(iid,letters,routes,rng)}

def validate_dataset(out):
 rows=[]
 with (out/"annotations.jsonl").open(encoding="utf-8") as f:
  for line in f:
   row=json.loads(line);rows.append(row);assert (out/row["image_path"]).is_file()
   q=row["questions"][0];pair=q["question_text"].split("from ",1)[1].split(". Answer",1)[0].split(" to ");actual=sum(unordered(r["start"],r["end"])==unordered(*pair) for r in row["routes"] if r["start"]!=r["end"]);assert str(actual)==q["ground_truth"],row["id"]
 return len(rows)

def generate_dataset(n=3000,output_dir="dataset"):
 out=Path(output_dir);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 with (out/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as f:
  for i in tqdm(range(1,n+1),desc="Generating route puzzles"):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
 total=validate_dataset(out);print(f"Validated {total} images and annotations in {out.resolve()}")

def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--output-dir",default="dataset");p.add_argument("--sample",action="store_true");a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=="__main__":main()
