import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
BG=(26,26,26);INK=(220,222,224);AA=3;LETTERS='ABCD';SHAPES={3:'triangle',4:'square',5:'pentagon',6:'hexagon'}
def polygon(n,cx,cy,r,rot,jitter=None):
 return [[round(cx+r*(1+(jitter[k] if jitter else 0))*math.cos(rot+2*math.pi*k/n),4),round(cy+r*(1+(jitter[k] if jitter else 0))*math.sin(rot+2*math.pi*k/n),4)] for k in range(n)]
def edges(v):return [[v[i],v[(i+1)%len(v)]] for i in range(len(v))]
def normalized_copy(vertices,cx,cy,radius):
 mx=sum(p[0] for p in vertices)/len(vertices);my=sum(p[1] for p in vertices)/len(vertices);span=max(math.hypot(p[0]-mx,p[1]-my) for p in vertices)
 return [[round(cx+(p[0]-mx)*radius/span,4),round(cy+(p[1]-my)*radius/span,4)] for p in vertices]
def candidates(n,rng,w,h,correct,target_vertices,same):
 data=[];wrong_counts=[]
 if same:wrong_counts=[n]
 choices=[x for x in range(3,7) if x!=n];rng.shuffle(choices);wrong_counts+=choices[:2] if same else choices[:3]
 counts=[]
 for lab in LETTERS:counts.append(n if lab==correct else wrong_counts.pop())
 for k,(lab,count) in enumerate(zip(LETTERS,counts)):
  cx=(k+.5)*w/4;cy=h-49;r=22;rot=-math.pi/2+rng.uniform(-.18,.18);jit=[rng.uniform(-.09,.09) for _ in range(count)];verts=normalized_copy(target_vertices,cx,cy,r) if lab==correct else polygon(count,cx,cy,r,rot,jit)
  data.append({'label':lab,'side_count':count,'vertices':verts,'is_correct':lab==correct,'description':'scaled copy of the embedded target' if lab==correct else ('same side count but different proportions' if count==n else 'different vertex count')})
 return data,same
def render(path,size,segs,cands):
 im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',14*AA) if Path('C:/Windows/Fonts/arialbd.ttf').exists() else ImageFont.load_default()
 for a,b in segs:d.line([(round(a[0]*AA),round(a[1]*AA)),(round(b[0]*AA),round(b[1]*AA))],fill=INK,width=round(1.15*AA))
 d.line([(12*AA,350*AA),((size[0]-12)*AA,350*AA)],fill=(90,92,94),width=2)
 for c in cands:
  v=c['vertices'];d.line([(round(x*AA),round(y*AA)) for x,y in v+[v[0]]],fill=INK,width=round(1.1*AA),joint='curve');cx=sum(x for x,y in v)/len(v);top=min(y for x,y in v);bb=d.textbbox((0,0),c['label'],font=font);d.text((round(cx*AA-(bb[2]-bb[0])/2),round((top-22)*AA)),c['label'],font=font,fill=INK)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def valid_embedding(tv,segs):
 target={tuple(sorted((tuple(a),tuple(b)))) for a,b in edges(tv)};full={tuple(sorted((tuple(a),tuple(b)))) for a,b in segs};return target<=full
def questions(iid,row,rng):
 qs=[{'question_id':iid+'_q1','question_text':'How many straight line segments make up this complex figure in total?','question_type':'total_segments','ground_truth':str(row['num_total_segments']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':'How many sides does the hidden target shape have (visible in the answer choices below)?','question_type':'target_side_count','ground_truth':str(len(row['target_vertices'])),'answer_format':'numeric','difficulty_level':2},{'question_id':iid+'_q3','question_text':'Which of the four candidate shapes (A, B, C, D) is actually hidden within the complex figure above? Answer with the letter.','question_type':'embedded_choice','ground_truth':row['correct_answer_choice'],'answer_format':'letter','difficulty_level':3}]
 t=rng.choice(('distractors','closed','same_side'))
 if t=='distractors':text='How many of the total line segments in the complex figure are NOT part of the hidden target shape (i.e. are distractor lines)?';typ='distractor_segment_count';gt=str(row['num_distractor_segments']);fmt='numeric'
 elif t=='closed':text="If you removed all distractor lines and kept only the target shape's edges, would the remaining figure be a closed polygon or an open/broken shape?";typ='target_closure';gt='closed';fmt='choice'
 else:text='One of the 3 incorrect answer choices may share the same number of sides as the correct target shape. Does such a choice exist among the 4 options? Answer yes or no.';typ='same_side_foil_exists';gt='yes' if row['same_side_foil_exists'] else 'no';fmt='yes_no'
 qs.append({'question_id':iid+'_q4','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':4});return qs
def generate_one(i,images):
 rng=random.Random(i);w=h=rng.randint(450,500);n=3+(i-1)%4;cx=w/2+rng.uniform(-24,24);cy=180+rng.uniform(-18,18);r=rng.uniform(58,78);rot=rng.uniform(0,math.tau);jit=[rng.uniform(-.12,.12) for _ in range(n)];tv=polygon(n,cx,cy,r,rot,jit);segs=edges(tv);total=rng.randint(n+6,14);dcount=total-n
 for k in range(dcount):
  mode=k%3
  if k<n:a=tv[k];b=[rng.uniform(28,w-28),rng.uniform(28,328)]
  elif mode==0:a=tv[rng.randrange(n)];b=[rng.uniform(28,w-28),rng.uniform(28,328)]
  elif mode==1:
   p=tv[rng.randrange(n)];q=tv[(rng.randrange(n-1)+1)%n];a=[(p[0]+q[0])/2,(p[1]+q[1])/2];b=[rng.uniform(28,w-28),rng.uniform(28,328)]
  else:
   e=rng.randrange(n);p=tv[e];q=tv[(e+1)%n];a=[round(p[0]+(q[0]-p[0])*rng.uniform(.25,.75),4),round(p[1]+(q[1]-p[1])*rng.uniform(.25,.75),4)];b=tv[(e+rng.randint(2,max(2,n-1)))%n] if n>3 else [rng.uniform(28,w-28),rng.uniform(28,328)]
  if math.hypot(a[0]-b[0],a[1]-b[1])>30:segs.append([[round(a[0],4),round(a[1],4)],[round(b[0],4),round(b[1],4)]])
 while len(segs)<total:segs.append([[rng.uniform(28,w-28),rng.uniform(28,328)],[rng.uniform(28,w-28),rng.uniform(28,328)]])
 correct=LETTERS[(i-1)%4];same=i%2==0;cands,same=candidates(n,rng,w,h,correct,tv,same);iid=f'embedded_figure_{i:04d}';render(images/f'{iid}.png',(w,h),segs,cands);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'target_shape_type':SHAPES[n],'target_vertices':tv,'target_edges':edges(tv),'segments':segs,'num_total_segments':len(segs),'num_distractor_segments':len(segs)-n,'correct_answer_choice':correct,'candidate_choices':cands,'distractor_choices_info':{c['label']:c['description'] for c in cands if not c['is_correct']},'same_side_foil_exists':same,'seed':i,'difficulty_score':round(.28+.04*n+.035*(len(segs)-8)+.12*(same),4)}
 assert valid_embedding(tv,segs);row['questions']=questions(iid,row,rng);return row
def generate_dataset(n,out,sample=False):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for i in range(1,count+1):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n');print(f'Generated {i}/{count}') if i%250==0 or i==count else None
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='embedded_figures_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
