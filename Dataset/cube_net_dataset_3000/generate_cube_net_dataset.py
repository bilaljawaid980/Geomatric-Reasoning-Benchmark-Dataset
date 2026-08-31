from __future__ import annotations
import argparse,json,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26); INK=(238,238,238); AA=3; DATASET_VERSION="cube-net-2.0.0"
LAYOUTS={
"cross_tail":((0,0),(0,1),(0,2),(1,1),(2,1),(3,1)),
"long_zigzag":((0,0),(0,1),(0,2),(1,2),(1,3),(1,4)),
"t_left_cap":((0,0),(0,1),(1,1),(1,2),(1,3),(2,1)),
"t_middle_cap":((0,0),(0,1),(1,1),(1,2),(1,3),(2,2)),
"t_right_cap":((0,0),(0,1),(1,1),(1,2),(1,3),(2,3)),
"offset_cross":((0,0),(0,1),(1,1),(1,2),(2,1),(3,1)),
"zigzag_staircase":((0,0),(0,1),(1,1),(1,2),(2,2),(2,3)),
"double_step":((0,0),(0,1),(1,1),(2,1),(2,2),(3,1)),
"long_l":((0,0),(0,1),(1,1),(2,1),(3,1),(3,2)),
"t_cross_left":((0,1),(1,0),(1,1),(1,2),(1,3),(2,1)),
"t_cross_right":((0,1),(1,0),(1,1),(1,2),(1,3),(2,2)),
}
NAMES=tuple(LAYOUTS); COMPLEXITY={n:i+1 for i,n in enumerate(NAMES)}
def neg(v):return tuple(-x for x in v)
def fold_orientations(coords):
 s=set(coords);root=min(s);ori={root:((1,0,0),(0,1,0),(0,0,1))};q=[root]
 while q:
  p=q.pop();r,d,n=ori[p]
  moves=[((1,0),(neg(n),d,r)),((-1,0),(n,d,neg(r))),((0,1),(r,neg(n),d)),((0,-1),(r,n,neg(d)))]
  for (dx,dy),new in moves:
   z=(p[0]+dx,p[1]+dy)
   if z not in s:continue
   if z in ori and ori[z]!=new:raise ValueError("inconsistent fold")
   if z not in ori:ori[z]=new;q.append(z)
 if len(ori)!=6 or len({x[2] for x in ori.values()})!=6:raise ValueError("not a cube net")
 return ori
def position_relations(coords):
 ori=fold_orientations(coords);pos=list(coords);op=[];adj=[]
 for i,a in enumerate(pos):
  for b in pos[i+1:]:
   if ori[a][2]==neg(ori[b][2]):op.append((a,b))
   if abs(a[0]-b[0])+abs(a[1]-b[1])==1:adj.append((a,b))
 return op,adj
PRECOMPUTED={name:position_relations(coords)[0] for name,coords in LAYOUTS.items()}
def pairs_to_letters(pairs,at):return [sorted((at[a],at[b])) for a,b in pairs]
def make_questions(iid,row,rng):
 letters=list("ABCDEF");adj=row["net_edge_neighbors"];opp={a:b for a,b in row["opposite_pairs"] for a,b in ((a,b),(b,a))}
 qs=[{"question_id":iid+"_q1","question_text":"How many squares (faces) make up this cube net?","question_type":"face_count","ground_truth":"6","answer_format":"numeric","difficulty_level":1}]
 x=rng.choice(letters);valid=adj[x];qs.append({"question_id":iid+"_q2","question_text":f"Name one face that shares a fold edge with face {x}.","question_type":"net_edge_neighbor","ground_truth":rng.choice(valid),"valid_answers":valid,"answer_format":"letter_any_of_list","difficulty_level":2})
 x=rng.choice(letters)
 if rng.random()<.62:text=f"If this net is folded into a cube, which face will be OPPOSITE face {x}?";typ="opposite_face";gt=opp[x];fmt="letter"
 else:text=f"How many faces share a fold edge with face {x}?";typ="net_edge_degree";gt=str(len(adj[x]));fmt="numeric"
 qs.append({"question_id":iid+"_q3","question_text":text,"question_type":typ,"ground_truth":gt,"answer_format":fmt,"difficulty_level":3})
 # Every pair of distinct folded-cube faces is either adjacent or opposite.  Use
 # index parity to balance this binary Level 4 exactly across a 3,000-item build.
 pool=row["cube_adjacent_pairs"] if int(iid[-4:])%2 else row["opposite_pairs"]
 x,y=rng.choice(pool);gt="adjacent" if int(iid[-4:])%2 else "opposite"
 text=f"If this net is folded into a cube, are face {x} and face {y} adjacent or opposite? Answer 'adjacent' or 'opposite'."
 qs.append({"question_id":iid+"_q4","question_text":text,"question_type":"folded_pair_relationship","ground_truth":gt,"answer_format":"adjacent_or_opposite","difficulty_level":4})
 x,y=rng.sample(letters,2);text=f"If the positions of faces {x} and {y} were swapped in this net, would face {x} still end up opposite the same face it currently is opposite to? Answer yes or no."
 qs.append({"question_id":iid+"_q5","question_text":text,"question_type":"swap_preserves_opposite","ground_truth":"yes" if opp[x]==y else "no","answer_format":"yes_no","difficulty_level":5});return qs
def font(size):
 for p in ("C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/segoeuib.ttf"):
  if Path(p).exists():return ImageFont.truetype(p,size)
 return ImageFont.load_default()
def render(path,size,coords,at,cell,offset,stroke):
 im=Image.new("RGB",(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im);f=font(round(cell*.34*AA));ox,oy=offset
 for p in coords:
  x=(ox+p[0]*cell)*AA;y=(oy+p[1]*cell)*AA;box=(x,y,x+cell*AA,y+cell*AA);d.rectangle(box,outline=INK,width=max(2,round(stroke*AA)))
  letter=at[p];bb=d.textbbox((0,0),letter,font=f);d.text((x+cell*AA/2-(bb[2]-bb[0])/2,y+cell*AA/2-(bb[3]-bb[1])/2-bb[1]),letter,font=f,fill=INK)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def generate_one(i,images):
 rng=random.Random(i);name=NAMES[(i-1)%11];coords=LAYOUTS[name];letters=list("ABCDEF");rng.shuffle(letters);at=dict(zip(coords,letters));letter_pos={v:list(k) for k,v in at.items()};op_pos=PRECOMPUTED[name];_,adj_pos=position_relations(coords);op=sorted(pairs_to_letters(op_pos,at));adj=sorted(pairs_to_letters(adj_pos,at));by={x:[] for x in letters}
 for a,b in adj:by[a].append(b);by[b].append(a)
 for x in by:by[x].sort()
 w=rng.randint(500,560);h=rng.randint(350,420);cols=max(x for x,y in coords)+1;rows=max(y for x,y in coords)+1;cell=min(rng.randint(60,100),(w-36)//cols,(h-36)//rows);nw,nh=cols*cell,rows*cell;off=((w-nw)//2+rng.randint(-min(10,(w-nw)//3),min(10,(w-nw)//3)),(h-nh)//2+rng.randint(-min(8,(h-nh)//3),min(8,(h-nh)//3)));iid=f"cube_net_{i:04d}";stroke=rng.uniform(.55,1.0);render(images/f"{iid}.png",(w,h),coords,at,cell,off,stroke)
 od={a:b for a,b in op for a,b in ((a,b),(b,a))};cube_by={x:sorted(set(letters)-{x,od[x]}) for x in letters};cube_pairs=sorted({tuple(sorted((a,b))) for a in letters for b in cube_by[a]})
 row={"id":iid,"dataset_version":DATASET_VERSION,"image_path":f"images/{iid}.png","canvas_size":[w,h],"net_layout_type":name,"letter_positions":letter_pos,"opposite_pairs":op,"net_edge_pairs":adj,"net_edge_neighbors":by,"cube_adjacent_pairs":[list(p) for p in cube_pairs],"cube_adjacent_faces":cube_by,"frame_conventions":{"net_edge_neighbors":"flat_net","cube_adjacent_faces":"folded_cube","opposite_pairs":"folded_cube"},"square_size_px":cell,"stroke_width_px":round(stroke,2),"seed":i,"difficulty_score":round(.25+.5*(COMPLEXITY[name]-1)/10+.25*(cell<75),4)};row["questions"]=make_questions(iid,row,rng);return row
def generate_dataset(n,out):
 out=Path(out);images=out/"images";images.mkdir(parents=True,exist_ok=True)
 with (out/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as f:
  for i in range(1,n+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(",",":"))+"\n")
   if i%250==0 or i==n:print(f"Generated {i}/{n}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=3000);p.add_argument("--output-dir",default="cube_net_dataset_3000");p.add_argument("--sample",action="store_true");a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=="__main__":main()
