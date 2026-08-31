"""Generate deterministic isometric voxel-structure reasoning datasets."""
from __future__ import annotations
import argparse,json,math,random
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw
try:
 from tqdm import tqdm
except ImportError:
 def tqdm(x,**_):return x
BG="#F1EFE8";SCALE_AA=3
DATASET_VERSION="cube-structure-2.0.0"
RAMPS={"A":{"top":"#BFD2D6","left":"#8FB2BA","right":"#6F98A3"},"B":{"top":"#D3CBC0","left":"#AA998A","right":"#86766A"}};EDGE="#26383D"

def iso_project(x,y,z):return((x-y)*.8660254,(x+y)*.5-z)
def gravity_valid(cubes):
 s=set(cubes);return all(z==0 or (x,y,z-1) in s for x,y,z in s)
def cube_hidden(cube,cubes,viewpoint=0):
 """Exact full-projection occlusion along the fixed isometric viewing ray."""
 x,y,z=cube;s=set(cubes);dx,dy=(1,1) if viewpoint==0 else (-1,-1)
 return any((x+dx*k,y+dy*k,z+k) in s for k in range(1,12))
def face_count(cube,cubes,viewpoint=0):
 if cube_hidden(cube,cubes,viewpoint):return 0
 x,y,z=cube;s=set(cubes);dx,dy=(1,1) if viewpoint==0 else (-1,-1)
 return int((x,y,z+1) not in s)+int((x+dx,y,z) not in s)+int((x,y+dy,z) not in s)
def visibility(cubes,viewpoint=0):return {c:face_count(c,cubes,viewpoint)>0 for c in cubes}

def generate_valid_structure(num_cubes,rng):
 base_n=rng.randint(4,min(10,num_cubes));foot={(0,0)}
 while len(foot)<base_n:
  x,y=rng.choice(tuple(foot));dx,dy=rng.choice([(1,0),(-1,0),(0,1),(0,-1)]);foot.add((x+dx,y+dy))
 heights={p:1 for p in foot};remaining=num_cubes-base_n
 while remaining:
  candidates=[p for p,h in heights.items() if h<6];p=rng.choice(candidates);heights[p]+=1;remaining-=1
 cubes={(x,y,z) for (x,y),height in heights.items() for z in range(height)};assert len(cubes)==num_cubes and gravity_valid(cubes);return cubes
def assign_clusters(cubes,two):
 if not two:return {c:"A" for c in cubes}
 xs=sorted({c[0] for c in cubes});pivot=xs[len(xs)//2];out={c:("A" if c[0]<pivot else "B") for c in cubes}
 if len(set(out.values()))<2:
  ordered=sorted(cubes);out={c:("A" if i<len(ordered)//2 else "B") for i,c in enumerate(ordered)}
 return out

def face_vertices(c,face,viewpoint=0):
 x,y,z=c;dx,dy=(1,1) if viewpoint==0 else (-1,-1)
 if face=="top":return [(x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1)]
 if face=="right":
  xx=x+1 if dx==1 else x;return [(xx,y,z),(xx,y+1,z),(xx,y+1,z+1),(xx,y,z+1)]
 yy=y+1 if dy==1 else y;return [(x,yy,z),(x+1,yy,z),(x+1,yy,z+1),(x,yy,z+1)]
def visible_faces(cubes):
 s=set(cubes);faces=[]
 for c in cubes:
  if cube_hidden(c,s,0):continue
  x,y,z=c
  if (x,y,z+1) not in s:faces.append((c,"top"))
  if (x+1,y,z) not in s:faces.append((c,"right"))
  if (x,y+1,z) not in s:faces.append((c,"left"))
 return sorted(faces,key=lambda f:(sum(f[0]),f[0][2],{"left":0,"right":1,"top":2}[f[1]]))
def render(path,size,cubes,clusters,line_width):
 w,h=size;faces=visible_faces(cubes);raw=[iso_project(*v) for c,f in faces for v in face_vertices(c,f)];minx,maxx=min(x for x,y in raw),max(x for x,y in raw);miny,maxy=min(y for x,y in raw),max(y for x,y in raw);scale=min((w-64)/(maxx-minx),(h-64)/(maxy-miny));ox=w/2-scale*(minx+maxx)/2;oy=h/2-scale*(miny+maxy)/2
 im=Image.new("RGB",(w*SCALE_AA,h*SCALE_AA),BG);d=ImageDraw.Draw(im)
 for c,f in faces:
  pts=[((ox+scale*x)*SCALE_AA,(oy+scale*y)*SCALE_AA) for x,y in [iso_project(*v) for v in face_vertices(c,f)]];d.polygon(pts,fill=RAMPS[clusters[c]][f]);d.line(pts+[pts[0]],fill=EDGE,width=max(2,round(line_width*SCALE_AA)),joint="curve")
 im.resize((w,h),Image.Resampling.LANCZOS).save(path,"PNG")

def make_questions(iid,meta,rng):
 layers={int(k):v for k,v in meta["cubes_per_layer"].items()};maxn=max(layers.values());best=min(z for z,n in layers.items() if n==maxn);qs=[
 {"question_id":iid+"_q1","question_text":"How many cubes make up this structure in total? Answer with a number in curly brackets, e.g. {12}.","question_type":"total_cube_count","ground_truth":str(meta["total_cube_count"]),"answer_format":"numeric","difficulty_level":1},
 {"question_id":iid+"_q2","question_text":"How many cubes are touching the ground (bottom layer)? Answer with a number in curly brackets, e.g. {5}.","question_type":"base_layer_count","ground_truth":str(meta["base_layer_count"]),"answer_format":"numeric","difficulty_level":2}]
 pool=["layers","largest"]+(["cluster"] if meta["color_cluster_count"]==2 else []);t=rng.choice(pool)
 if t=="layers":text="How many total layers (levels of height) does this structure have? Answer with a number in curly brackets, e.g. {3}.";gt=str(meta["max_height"]);typ="max_height"
 elif t=="largest":text="Which layer (counting from the ground as layer 1) has the most cubes? Answer with a number in curly brackets, e.g. {2}.";gt=str(best+1);typ="largest_layer"
 else:cluster=rng.choice(["A","B"]);text=f"How many cubes are in the {cluster} color cluster?";gt=str(meta["cluster_counts"][cluster]);typ="cluster_cube_count"
 qs.append({"question_id":iid+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":"numeric","difficulty_level":3})
 t="hidden"
 if t=="hidden":text="How many cubes in this structure are completely hidden from view? Answer with a number in curly brackets, e.g. {2}.";gt=str(meta["hidden_cube_count"]);typ="hidden_cube_count";fmt="numeric"
 elif t=="stable":text="Is this structure physically stable—does every cube have support beneath it with no floating cubes? Answer yes or no.";gt="yes";typ="physical_stability";fmt="yes_no"
 else:text="If this structure were rotated 180 degrees around the vertical axis, how many currently-hidden cubes would become visible? Answer with a number in curly brackets, e.g. {3}.";gt=str(meta["hidden_to_visible_180"]);typ="hidden_to_visible_180";fmt="numeric"
 qs.append({"question_id":iid+"_q4","question_text":"How many cubes are completely hidden from the current view? Answer with a number.","question_type":"hidden_cube_count","ground_truth":str(meta["hidden_cube_count"]),"answer_format":"numeric","difficulty_level":4})
 qs.append({"question_id":iid+"_q5","question_text":"If this structure were rotated 180 degrees around the vertical axis, how many currently-hidden cubes would become visible? Answer with a number in curly brackets, e.g. {3}.","question_type":"hidden_to_visible_180","ground_truth":str(meta["hidden_to_visible_180"]),"answer_format":"numeric","difficulty_level":5});return qs
def generate_one(i,images):
 iid=f"cube_structure_{i:04d}";target_hidden,target_level5=((0,0),(1,1),(2,2))[(i-1)%3]
 for attempt in range(10000):
  rng=random.Random(f"cube-structure-v2:{i}:{attempt}");size=(rng.randint(400,430),rng.randint(400,430));total=rng.randint(8,22);cubes=generate_valid_structure(total,rng);vis=visibility(cubes,0);ambiguous=any(z>0 and not vis.get((x,y,z-1),True) for x,y,z in cubes)
  if ambiguous:continue
  opp=visibility(cubes,180);hidden_count=sum(not vis[c] for c in cubes);level5_count=sum(not vis[c] and opp[c] for c in cubes)
  if (hidden_count,level5_count)!=(target_hidden,target_level5):continue
  two=rng.random()<.25;clusters=assign_clusters(cubes,two);line_width=round(rng.uniform(.5,1),2);render(images/f"{iid}.png",size,cubes,clusters,line_width)
  from validate_cube_dataset import png_faces_match
  with Image.open(images/f"{iid}.png") as source:probe=source.convert("RGB");probe.load()
  if png_faces_match(probe,cubes,clusters):break
 else:raise RuntimeError(f"unable to generate unambiguous cube structure {i}")
 hidden=[c for c in cubes if not vis[c]];layers=Counter(z for x,y,z in cubes);cluster_counts=Counter(clusters.values());cluster_hidden=Counter(clusters[c] for c in cubes if not vis[c])
 records=[]
 for c in sorted(cubes):
  fc=face_count(c,cubes,0);status="fully_hidden" if fc==0 else ("fully_visible" if fc==3 else "partially_occluded");records.append({"x":c[0],"y":c[1],"z":c[2],"visibility":status,"visible":fc>0,"visible_face_count":fc,"color_cluster":clusters[c]})
 meta={"total_cube_count":total,"visible_cube_count":sum(vis.values()),"hidden_cube_count":len(hidden),"base_layer_count":layers[0],"max_height":max(layers)+1,"cubes_per_layer":{str(z):layers[z] for z in sorted(layers)},"color_cluster_count":2 if two else 1,"cluster_counts":dict(cluster_counts),"hidden_members_per_cluster":{name:cluster_hidden.get(name,0) for name in cluster_counts},"has_ambiguous_visual_floater":False,"hidden_to_visible_180":sum(not vis[c] and opp[c] for c in cubes)};difficulty=round(min(1,.3*(total-8)/14+.3*len(hidden)/max(1,total)+.2*(meta["max_height"]-1)/5+.1*two),4)
 return {"dataset_version":DATASET_VERSION,"vertical_axis":"z","coordinate_frame":"right-handed voxel coordinates (x,y,z)","render_frame":"isometric projection with screen vertical component -z","rotation_axis_level5":"z","generation_attempt":attempt,"id":iid,"image_path":f"images/{iid}.png","canvas_size":list(size),**meta,"line_width_px":line_width,"seed":i,"difficulty_score":difficulty,"cubes":records,"questions":make_questions(iid,meta,rng)}
def generate_dataset(n=3000,output_dir="cube_structure_dataset"):
 out=Path(output_dir);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 with (out/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as f:
  for i in tqdm(range(1,n+1),desc="Generating cube structures"):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
 from validate_cube_dataset import validate;checked,issues=validate(out);assert not issues,issues[:10];print(f"Validated {checked} images in {out.resolve()}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--output-dir",default="cube_structure_dataset");p.add_argument("--sample",action="store_true");a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=="__main__":main()
