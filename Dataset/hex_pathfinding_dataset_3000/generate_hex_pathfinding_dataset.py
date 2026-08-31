"""Generate deterministic hex-grid shortest-path puzzles with counterfactual replanning."""
from __future__ import annotations
import argparse,json,math,random
from collections import Counter,deque
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
BACKGROUND="#FDFAF4";WHITE="#FFFDF9";BLACK="#242A2E";GREY="#9DA3A8";HOME="#4A9B63";START="#D24A43";OUTLINE="#314958";L2="#2C78B8";L5="#8A4FA3"
DATASET_VERSION="hex-pathfinding-2.0.0"
DIRECTIONS=((1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1))
def font(size,bold=False):
 try:return ImageFont.truetype(str(Path("C:/Windows/Fonts")/("arialbd.ttf" if bold else "arial.ttf")),size)
 except OSError:return ImageFont.load_default()
def neighbors(coord):q,r=coord;return [(q+dq,r+dr) for dq,dr in DIRECTIONS]
def hex_distance(a,b):dq=a[0]-b[0];dr=a[1]-b[1];return (abs(dq)+abs(dr)+abs(dq+dr))//2
def all_coordinates(radius):return [(q,r) for q in range(-radius,radius+1) for r in range(-radius,radius+1) if abs(q+r)<=radius]
def bfs(traversable,start,goal):
 if start not in traversable or goal not in traversable:return None,[],0
 queue=deque([start]);distance={start:0};count={start:1};parent={}
 while queue:
  current=queue.popleft()
  for nxt in sorted(neighbors(current)):
   if nxt not in traversable:continue
   candidate=distance[current]+1
   if nxt not in distance:distance[nxt]=candidate;count[nxt]=count[current];parent[nxt]=current;queue.append(nxt)
   elif distance[nxt]==candidate:count[nxt]+=count[current]
 if goal not in distance:return None,[],0
 path=[];node=goal
 while True:
  path.append(node)
  if node==start:break
  node=parent[node]
 path.reverse();return distance[goal],path,count[goal]
def coord_list(coord):return [coord[0],coord[1]]
def coord_text(coord):return f"({coord[0]},{coord[1]})"
def make_scene(index):
 rng=random.Random(index);radius=3+(index-1)%3;coords=all_coordinates(radius);coord_set=set(coords);desired_l2_hole=index%2==0;desired_l5=("same","increase","no_path")[(index-1)%3]
 for attempt in range(500):
  start,home=rng.sample(coords,2)
  if hex_distance(start,home)<radius+1:continue
  start_neighbors=[n for n in neighbors(start) if n in coord_set]
  minimum=min(hex_distance(n,home) for n in start_neighbors);toward=[n for n in start_neighbors if hex_distance(n,home)==minimum];l2_tile=rng.choice(toward)
  forced_holes=set();forced_walk={start,home,l2_tile};unique_exit=None
  if desired_l2_hole:forced_holes.add(l2_tile);forced_walk.remove(l2_tile)
  if desired_l5=="no_path":
   exit_options=[n for n in start_neighbors if n!=l2_tile] if not desired_l2_hole else [n for n in start_neighbors if n!=l2_tile]
   if not exit_options:continue
   unique_exit=rng.choice(exit_options);forced_holes.update(n for n in start_neighbors if n!=unique_exit);forced_walk.add(unique_exit)
   if desired_l2_hole:forced_holes.add(l2_tile)
   else:
    # Keep the visually queried tile walkable but trap it away from the goal;
    # the separate unique exit remains the Level 5 articulation tile.
    for n in neighbors(l2_tile):
     if n in coord_set and n not in (start,l2_tile,unique_exit):forced_holes.add(n)
  density=rng.uniform(.13,.24);target=max(len(forced_holes),round(len(coords)*density));candidates=[c for c in coords if c not in forced_walk and c not in forced_holes];rng.shuffle(candidates);holes=set(forced_holes)|set(candidates[:max(0,target-len(forced_holes))]);holes.discard(start);holes.discard(home)
  if not desired_l2_hole:holes.discard(l2_tile)
  traversable=coord_set-holes;length,path,path_count=bfs(traversable,start,home)
  if length is None:continue
  near_path={c for c in traversable-{start,home} if min(hex_distance(c,p) for p in path)<=1};outcomes={"same":[],"increase":[],"no_path":[]}
  for tile in near_path:
   new_length,_new_path,_new_count=bfs(traversable-{tile},start,home)
   outcome="no_path" if new_length is None else ("increase" if new_length>length else "same");outcomes[outcome].append((tile,new_length))
  if desired_l5=="no_path" and unique_exit is not None:
   options=[item for item in outcomes["no_path"] if item[0]==unique_exit]
  else:options=outcomes[desired_l5]
  if not options:continue
  l5_tile,new_length=rng.choice(sorted(options));break
 else:raise RuntimeError(f"unable to generate scene {index}")
 decorative={coord for coord in traversable-{start,home} if (coord[0]-coord[1]+index)%4==0};all_tiles=[]
 for coord in sorted(coords):
  color="grey" if coord in holes else ("home" if coord==home else ("start" if coord==start else ("black" if coord in decorative else "white")))
  all_tiles.append({"coordinate":coord_list(coord),"color":color})
 l5_answer="no valid path exists" if new_length is None else (f"stay the same ({length} moves)" if new_length==length else f"increase to {new_length} moves")
 iid=f"hex_pathfinding_{index:04d}";questions=[
  {"question_id":f"{iid}_q1","difficulty_level":1,"question_type":"hole_tile_count","question_text":"How many grey (hole) tiles are shown in this grid?","ground_truth":str(len(holes)),"answer_format":"integer"},
  {"question_id":f"{iid}_q2","difficulty_level":2,"question_type":"adjacent_neighbor_status","question_text":"Is the tile outlined in blue with a '?', immediately adjacent to START, a grey hole or walkable? Answer 'hole' or 'walkable'.","ground_truth":"hole" if l2_tile in holes else "walkable","answer_format":"hole or walkable"},
  {"question_id":f"{iid}_q3","difficulty_level":3,"question_type":"shortest_path_length","question_text":"What is the minimum number of moves needed to travel from START to HOME while avoiding all grey holes? Answer with a number in curly brackets.","ground_truth":str(length),"answer_format":"integer in curly brackets"},
  {"question_id":f"{iid}_q4","difficulty_level":4,"question_type":"shortest_path_uniqueness","question_text":"Is the shortest path from START to HOME unique, or are there multiple different shortest paths of the same length? If multiple, how many?","ground_truth":"unique" if path_count==1 else f"multiple ({path_count})","answer_format":"unique or multiple (count)"},
  {"question_id":f"{iid}_q5","difficulty_level":5,"question_type":"blocked_tile_replanning","question_text":f"If the walkable tile marked with a purple X at axial position {coord_text(l5_tile)} were turned into a hole, would the shortest path length increase, stay the same, or would there be no valid path? If it increases, state the new shortest length.","ground_truth":l5_answer,"answer_format":"stay the same (N moves), increase to N moves, or no valid path exists"}]
 return {"dataset_version":DATASET_VERSION,"coordinate_frame":"axial hex coordinates (q,r)","id":iid,"image_path":f"images/{iid}.png","canvas_size":[rng.randint(500,600)]*2,"seed":index,"grid_radius":radius,"all_tiles":all_tiles,"num_hole_tiles":len(holes),"hole_density":round(len(holes)/len(coords),6),"start_coordinate":coord_list(start),"home_coordinate":coord_list(home),"shortest_path_length":length,"shortest_path_sequence":[coord_list(c) for c in path],"num_alternate_shortest_paths":path_count,"level2_neighbor_coordinate":coord_list(l2_tile),"level2_neighbor_direction_is_toward_home":True,"level5_blocked_coordinate":coord_list(l5_tile),"level5_outcome":desired_l5,"level5_new_shortest_path_length":new_length,"generation_attempt":attempt,"difficulty_score":round(.35+.08*(radius-3)+.18*(len(holes)/len(coords))+.12*(path_count>1)+.15*(desired_l5=="no_path")+.1*(desired_l5=="increase"),4),"questions":questions}
def pixel_geometry(canvas,radius):
 size=min((canvas-72)/(math.sqrt(3)*(2*radius+1)),(canvas-112)/(3*radius+2));return size,(canvas/2,canvas/2-22)
def to_pixel(coord,size,center):q,r=coord;return center[0]+size*math.sqrt(3)*(q+r/2),center[1]+size*1.5*r
def polygon(center,size):return [(center[0]+size*math.cos(math.radians(30+60*i)),center[1]+size*math.sin(math.radians(30+60*i))) for i in range(6)]
def render(row,destination):
 scale=2;canvas=row["canvas_size"][0];size,center=pixel_geometry(canvas,row["grid_radius"]);image=Image.new("RGB",(canvas*scale,canvas*scale),BACKGROUND);draw=ImageDraw.Draw(image);fill={"white":WHITE,"black":BLACK,"grey":GREY,"home":HOME,"start":WHITE};tiles={tuple(t["coordinate"]):t["color"] for t in row["all_tiles"]}
 for coord,color in tiles.items():
  points=[(round(x*scale),round(y*scale)) for x,y in polygon(to_pixel(coord,size,center),size*.97)];draw.polygon(points,fill=fill[color],outline=OUTLINE,width=max(2,round(1.3*scale)))
 start=tuple(row["start_coordinate"]);home=tuple(row["home_coordinate"]);l2=tuple(row["level2_neighbor_coordinate"]);l5=tuple(row["level5_blocked_coordinate"]);small=font(max(12,round(size*.48))*scale,True)
 sx,sy=to_pixel(start,size,center);draw.ellipse([(round((sx-size*.23)*scale),round((sy-size*.23)*scale)),(round((sx+size*.23)*scale),round((sy+size*.23)*scale))],fill=START,outline="#8A2927",width=2*scale);draw.text((round(sx*scale),round(sy*scale)),"S",font=font(max(10,round(size*.34))*scale,True),fill="white",anchor="mm")
 hx,hy=to_pixel(home,size,center);draw.text((round(hx*scale),round(hy*scale)),"HOME",font=font(max(8,round(size*.27))*scale,True),fill="white",anchor="mm")
 lx,ly=to_pixel(l2,size,center);draw.ellipse([(round((lx-size*.45)*scale),round((ly-size*.45)*scale)),(round((lx+size*.45)*scale),round((ly+size*.45)*scale))],outline=L2,width=3*scale);draw.text((round((lx-size*.22)*scale),round((ly-size*.23)*scale)),"?",font=small,fill=L2,anchor="mm")
 xx,xy=to_pixel(l5,size,center);draw.line([(round((xx-size*.22)*scale),round((xy-size*.22)*scale)),(round((xx+size*.22)*scale),round((xy+size*.22)*scale))],fill=L5,width=3*scale);draw.line([(round((xx-size*.22)*scale),round((xy+size*.22)*scale)),(round((xx+size*.22)*scale),round((xy-size*.22)*scale))],fill=L5,width=3*scale)
 legend_font=font(13*scale,True);draw.text((canvas*scale/2,(canvas-18)*scale),"WHITE / BLACK = WALKABLE    |    GREY = HOLE",fill=OUTLINE,font=legend_font,anchor="mm")
 image.resize((canvas,canvas),Image.Resampling.LANCZOS).save(destination,"PNG",optimize=True)
def generate(output,count,start_index,render_images=True):
 output.mkdir(parents=True,exist_ok=True);images=output/"images";images.mkdir(exist_ok=True);rows=[]
 for position,index in enumerate(range(start_index,start_index+count),1):
  row=make_scene(index);rows.append(row)
  if render_images:render(row,images/Path(row["image_path"]).name)
  if render_images and (position%100==0 or position==count):print(f"Rendered {position}/{count}",flush=True)
 with (output/"annotations.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for row in rows:h.write(json.dumps(row,separators=(",",":"))+"\n")
 stats={"images":len(rows),"grid_radius":dict(Counter(r["grid_radius"] for r in rows)),"level2":dict(Counter(r["questions"][1]["ground_truth"] for r in rows)),"level5":dict(Counter(r["level5_outcome"] for r in rows)),"hole_density":{"min":min(r["hole_density"] for r in rows),"mean":sum(r["hole_density"] for r in rows)/len(rows),"max":max(r["hole_density"] for r in rows)}};(output/"generation_stats.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8");print(json.dumps(stats,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument("--count",type=int,default=3000);p.add_argument("--start-index",type=int,default=1);p.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent);p.add_argument("--metadata-only",action="store_true");p.add_argument("--sample",action="store_true");a=p.parse_args()
 if a.sample:a.output_dir=Path(__file__).resolve().parent/"sample_test";a.count=5
 generate(a.output_dir,a.count,a.start_index,not a.metadata_only)
if __name__=="__main__":main()
