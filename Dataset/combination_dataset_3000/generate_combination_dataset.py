import argparse,json,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);INK=(220,222,224);AA=3;CHOICES='ABCD';DIRS=((1,0),(-1,0),(0,1),(0,-1))
def canonical(cells):
 cells=set(map(tuple,cells));mx=min(x for x,y in cells);my=min(y for x,y in cells);return tuple(sorted((x-mx,y-my) for x,y in cells))
def rotations(cells,reflect=False):
 base=[(-x,y) if reflect else (x,y) for x,y in cells];out=set()
 for k in range(4):
  q=[]
  for x,y in base:
   for _ in range(k):x,y=-y,x
   q.append((x,y))
  out.add(canonical(q))
 return sorted(out)
def all_orientations(cells,allow_reflection):
 out=set(rotations(cells,False))
 if allow_reflection:out.update(rotations(cells,True))
 return sorted(out)
def placements(piece,target,allow_reflection):
 target=set(target);out=set()
 for shape in all_orientations(piece,allow_reflection):
  anchor=shape[0]
  for tx,ty in target:
   placed=frozenset((x-anchor[0]+tx,y-anchor[1]+ty) for x,y in shape)
   if placed<=target:out.add(placed)
 return sorted(out,key=lambda x:sorted(x))
def try_assemble(pieces,target,allow_reflection=False):
 target=frozenset(target)
 if sum(len(p) for p in pieces)!=len(target):return False
 opts=[placements(p,target,allow_reflection) for p in pieces]
 if any(not x for x in opts):return False
 order=sorted(range(len(pieces)),key=lambda i:len(opts[i]))
 def rec(k,used):
  if k==len(order):return used==target
  return any(rec(k+1,used|p) for p in opts[order[k]] if not used&p)
 return rec(0,frozenset())
def connected(cells):
 cells=set(cells);seen={next(iter(cells))};stack=list(seen)
 while stack:
  x,y=stack.pop()
  for dx,dy in DIRS:
   q=(x+dx,y+dy)
   if q in cells and q not in seen:seen.add(q);stack.append(q)
 return len(seen)==len(cells)
def grow_polyomino(n,rng):
 if n==1:return ((0,0),)
 while True:
  cells={(0,0)}
  while len(cells)<n:
   x,y=rng.choice(tuple(cells));dx,dy=rng.choice(DIRS);cells.add((x+dx,y+dy))
  c=canonical(cells);w=max(x for x,y in c)+1;h=max(y for x,y in c)+1
  if n==2 or (w>=2 and h>=2):return c
def partition(target,k,rng):
 target=set(target);root=rng.choice(tuple(target));seen={root};tree=[];stack=[root]
 while stack:
  p=stack[-1];nbr=[(p[0]+dx,p[1]+dy) for dx,dy in DIRS if (p[0]+dx,p[1]+dy) in target and (p[0]+dx,p[1]+dy) not in seen]
  if nbr:q=rng.choice(nbr);seen.add(q);tree.append((p,q));stack.append(q)
  else:stack.pop()
 cuts=set(rng.sample(range(len(tree)),k-1));adj={p:[] for p in target}
 for i,(a,b) in enumerate(tree):
  if i not in cuts:adj[a].append(b);adj[b].append(a)
 comps=[];left=set(target)
 while left:
  s=left.pop();comp={s};todo=[s]
  while todo:
   p=todo.pop()
   for q in adj[p]:
    if q in left:left.remove(q);comp.add(q);todo.append(q)
  comps.append(canonical(comp))
 return comps if len(comps)==k and min(map(len,comps))>=1 else partition(target,k,rng)
def reflected_pieces(pieces):return [canonical([(-x,y) for x,y in p]) for p in pieces]
def near_miss(total,target,rng):
 for _ in range(2000):
  k=rng.randint(2,min(4,total-1));cuts=sorted(rng.sample(range(1,total),k-1));sizes=[b-a for a,b in zip([0]+cuts,cuts+[total])]
  p=[grow_polyomino(n,rng) for n in sizes]
  if not try_assemble(p,target,False) and not try_assemble(p,target,True):return p
 raise RuntimeError('unable to create equal-area near miss')
def wrong_area(pieces,rng):
 p=[list(x) for x in pieces];i=max(range(len(p)),key=lambda j:len(p[j]));cells=set(p[i]);removable=[c for c in cells if len(cells)>1 and connected(cells-{c})]
 if removable:cells.remove(rng.choice(removable));p[i]=list(canonical(cells))
 else:p.append([(0,0)])
 return [canonical(x) for x in p]
def build_geometry(rng,n):
 for _ in range(400):
  target=grow_polyomino(n,rng);k=rng.randint(2,min(4,n-2));correct=partition(target,k,rng);mirror=reflected_pieces(correct)
  if try_assemble(correct,target,False) and not try_assemble(mirror,target,False) and try_assemble(mirror,target,True):
   miss=near_miss(n,target,rng);wrong=wrong_area(correct,rng)
   if not try_assemble(miss,target,False) and sum(map(len,wrong))!=n:return target,correct,miss,wrong,mirror
 raise RuntimeError('unable to construct verified puzzle')
def font(size):
 p=Path('C:/Windows/Fonts/arialbd.ttf');return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()
def bounds(cells):return max(x for x,y in cells)+1,max(y for x,y in cells)+1
def draw_cells(d,cells,ox,oy,cell):
 for x,y in cells:d.rectangle((round((ox+x*cell)*AA),round((oy+y*cell)*AA),round((ox+(x+1)*cell)*AA),round((oy+(y+1)*cell)*AA)),outline=INK,width=max(2,round(.9*AA)))
def candidate_layout(pieces,panel):
 x0,y0,x1,y1=panel;dims=[bounds(p) for p in pieces];units=sum(w for w,h in dims)+len(pieces)-1
 cell=min(18.0,(x1-x0-42)/max(1,units),(y1-y0-40)/max(h for w,h in dims));gap=cell
 widths=[w*cell for w,h in dims];total=sum(widths)+gap*(len(pieces)-1);x=x0+(x1-x0-total)/2
 result=[]
 for p,pw,(pw_cells,ph_cells) in zip(pieces,widths,dims):
  result.append((p,x,y0+30+(y1-y0-35-ph_cells*cell)/2,cell));x+=pw+gap
 return result
def render(path,size,target,candidates):
 im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im);f=font(14*AA);tf=font(15*AA);d.text((22*AA,18*AA),'Target',font=tf,fill=INK);tw,th=bounds(target);cell=min(28,125/max(tw,th));draw_cells(d,target,size[0]/2-tw*cell/2,38,cell);d.line([(15*AA,174*AA),((size[0]-15)*AA,174*AA)],fill=(90,92,94),width=2)
 panels=[(0,180,size[0]/2,315),(size[0]/2,180,size[0],315),(0,315,size[0]/2,size[1]),(size[0]/2,315,size[0],size[1])]
 for cand,panel in zip(candidates,panels):
  x0,y0,x1,y1=panel;d.text((round((x0+12)*AA),round((y0+8)*AA)),cand['choice_label'],font=f,fill=INK);pieces=cand['pieces']
  for p,x,y,cell in candidate_layout(pieces,panel):draw_cells(d,p,x,y,cell)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def questions(iid,row,rng):
 qs=[{'question_id':iid+'_q1','question_text':'How many unit cells make up the target shape?','question_type':'target_cell_count','ground_truth':str(row['target_cell_count']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':'Which set of pieces (A, B, C, or D) can be assembled using only translation and rotation, with no mirroring, to exactly form the target?','question_type':'assembly_choice','ground_truth':row['correct_answer_choice'],'answer_format':'letter','difficulty_level':2}]
 if rng.random()<.5:
  c=rng.choice(row['candidates']);text=f"How many separate pieces are shown in candidate {c['choice_label']}?";typ='candidate_piece_count';gt=str(len(c['pieces']));fmt='numeric';extra={'candidate_label':c['choice_label']}
 else:
  c=rng.choice([x for x in row['candidates'] if not x['is_valid_assembly']]);text=f"Does candidate {c['choice_label']} have the same total number of unit cells as the target? Answer yes or no.";typ='candidate_same_area';gt='yes' if c['total_cell_count']==row['target_cell_count'] else 'no';fmt='yes_no';extra={'candidate_label':c['choice_label']}
 qs.append({'question_id':iid+'_q3','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':3,**extra})
 t=rng.choice(('mirror','wrong','connectivity'))
 if t=='mirror':text='Which candidate has the correct area but would require flipping (mirroring) its pieces to form the target?';typ='requires_reflection_choice';gt=next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='requires_reflection');fmt='letter'
 elif t=='wrong':text='Which candidate has the wrong total number of unit cells compared with the target?';typ='wrong_area_choice';gt=next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='wrong_area');fmt='letter'
 else:text='If one extra unit cell were attached along an edge of the correctly assembled connected target, would the result remain connected? Answer yes or no.';typ='extra_cell_connectivity';gt='yes';fmt='yes_no'
 qs.append({'question_id':iid+'_q4','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':4});return qs
def generate_one(i,images):
 rng=random.Random(i);w=rng.randint(550,600);h=rng.randint(400,450);n=rng.randint(6,10);target,correct,miss,wrong,mirror=build_geometry(rng,n);correct_label=CHOICES[(i-1)%4];roles=[('valid',correct,None),('gap',miss,'gap_or_overlap'),('wrong',wrong,'wrong_area'),('mirror',mirror,'requires_reflection')];other=[x for x in CHOICES if x!=correct_label];rng.shuffle(other);labels=[correct_label]+other;cands=[]
 for lab,(role,pieces,reason) in zip(labels,roles):cands.append({'choice_label':lab,'pieces':[[list(c) for c in p] for p in pieces],'total_cell_count':sum(map(len,pieces)),'is_valid_assembly':role=='valid','failure_reason':reason})
 cands.sort(key=lambda x:CHOICES.index(x['choice_label']));iid=f'combination_{i:04d}';render(images/f'{iid}.png',(w,h),target,cands);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'target_cells':[list(c) for c in target],'target_cell_count':n,'candidates':cands,'correct_answer_choice':correct_label,'seed':i,'difficulty_score':round(.3+.055*(n-6)+.06*(len(correct)-2),4)};row['questions']=questions(iid,row,rng);return row
def generate_dataset(n,out,sample=False):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for i in range(1,count+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
   if i%250==0 or i==count:print(f'Generated {i}/{count}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='combination_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
