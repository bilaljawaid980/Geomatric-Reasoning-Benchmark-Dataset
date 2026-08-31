import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw
BG=(26,26,26);AA=3;PALETTE=[('teal',(56,171,159)),('magenta',(205,75,139)),('orange',(232,133,55)),('blue',(64,139,207)),('purple',(143,104,190))];SHAPES=('circle','square','triangle');BLOCK_H=21;BLOCK_PITCH=24;BLOCK_W=54
def perspective_size(base,depth):return base*(1-.4*depth)
def render_depth(path,size,objects):
 im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im)
 for o in sorted(objects,key=lambda z:z['depth_value'],reverse=True):
  x,y=o['canvas_position'];s=o['rendered_size'];c=tuple(o['rgb']);X=lambda z:round(z*AA)
  if o['shape_type']=='circle':d.ellipse((X(x-s/2),X(y-s/2),X(x+s/2),X(y+s/2)),fill=c)
  elif o['shape_type']=='square':d.rectangle((X(x-s/2),X(y-s/2),X(x+s/2),X(y+s/2)),fill=c)
  else:d.polygon([(X(x),X(y-s/2)),(X(x-s/2),X(y+s/2)),(X(x+s/2),X(y+s/2))],fill=c)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def render_stacks(path,size,stacks):
 im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im);ground=size[1]-38;d.line([(20*AA,ground*AA),((size[0]-20)*AA,ground*AA)],fill=(95,98,100),width=2)
 for s in stacks:
  x=s['position_x'];c=tuple(s['rgb'])
  for k in range(s['block_count']):
   bottom=ground-k*BLOCK_PITCH;d.rectangle((round((x-BLOCK_W/2)*AA),round((bottom-BLOCK_H)*AA),round((x+BLOCK_W/2)*AA),round(bottom*AA)),fill=c,outline=(235,235,235),width=2)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def depth_questions(iid,row,rng):
 o=row['objects'];a,b=rng.sample(o,2);x,y=rng.sample(o,2);newd=min(1,x['depth_value']*2);news=perspective_size(row['base_size_px'],newd);cmp='larger' if news>y['rendered_size']+.5 else 'smaller' if news<y['rendered_size']-.5 else 'same'
 return [{'question_id':iid+'_q1','question_text':'How many objects are shown in this scene?','question_type':'object_count','ground_truth':str(len(o)),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':f"Which object is closer to the camera: the {a['color']} {a['shape_type']} or the {b['color']} {b['shape_type']}?",'question_type':'pair_closer','ground_truth':a['color'] if a['depth_value']<b['depth_value'] else b['color'],'answer_format':'color','difficulty_level':2},{'question_id':iid+'_q3','question_text':'Rank all objects in this scene from closest to farthest, by color.','question_type':'depth_ordering','ground_truth':row['depth_ordering'],'answer_format':'ordered_list','difficulty_level':3},{'question_id':iid+'_q4','question_text':f"If the {x['color']} object moved twice as far from the camera as its current distance, would it appear larger, smaller, or about the same size as the {y['color']} object?",'question_type':'counterfactual_size','ground_truth':cmp,'answer_format':'choice','difficulty_level':4,'subject_color':x['color'],'comparison_color':y['color']}]
def stack_questions(iid,row,rng):
 s=row['stacks'];a,b=rng.sample(s,2);qs=[{'question_id':iid+'_q1','question_text':'How many separate stacks of blocks are shown in this image?','question_type':'stack_count','ground_truth':str(len(s)),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':f"Which stack is taller: the {a['color']} stack or the {b['color']} stack?",'question_type':'pair_taller','ground_truth':a['color'] if a['block_count']>b['block_count'] else b['color'],'answer_format':'color','difficulty_level':2},{'question_id':iid+'_q3','question_text':'Rank all stacks from tallest to shortest, by color.','question_type':'height_ordering','ground_truth':row['height_ordering'],'answer_format':'ordered_list','difficulty_level':3}]
 tallest=max(s,key=lambda z:z['block_count']);short=min(s,key=lambda z:z['block_count']);post={z['color']:z['block_count'] for z in s};post[tallest['color']]-=2;post[short['color']]+=2;mx=max(post.values());unique=sum(v==mx for v in post.values())==1
 if rng.random()<.5 and unique:text='If you moved 2 blocks from the tallest stack to the shortest stack, would the shortest stack become the unique new tallest? Answer yes or no.';typ='transfer_blocks';gt='yes' if post[short['color']]==mx else 'no'
 else:text='How many total blocks are there across all stacks combined?';typ='total_blocks';gt=str(sum(z['block_count'] for z in s))
 qs.append({'question_id':iid+'_q4','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':'yes_no' if typ=='transfer_blocks' else 'numeric','difficulty_level':4});return qs
def generate_one(i,images):
 rng=random.Random(i);w=rng.randint(550,650);h=rng.randint(350,400);kind='depth_ordering' if i%2 else 'stack_height';iid=f'depth_height_{i:04d}'
 if kind=='depth_ordering':
  n=rng.randint(2,4);colors=rng.sample(PALETTE,n);depths=sorted(rng.uniform(.05,.95) for _ in range(n))
  while min(b-a for a,b in zip(depths,depths[1:]))<.12:depths=sorted(rng.uniform(.05,.95) for _ in range(n))
  rng.shuffle(depths);base=rng.uniform(78,96);xs=[(j+1)*w/(n+1) for j in range(n)];rng.shuffle(xs);objs=[]
  for j,(name,rgb) in enumerate(colors):
   dep=depths[j];sz=perspective_size(base,dep);y=h*.76-dep*h*.42;objs.append({'index':j,'color':name,'rgb':list(rgb),'shape_type':rng.choice(SHAPES),'depth_value':round(dep,6),'canvas_position':[round(xs[j]+rng.uniform(-12,12),4),round(y,4)],'rendered_size':round(sz,4)})
  order=[x['color'] for x in sorted(objs,key=lambda z:z['depth_value'])];render_depth(images/f'{iid}.png',(w,h),objs);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'scene_type':kind,'base_size_px':round(base,4),'objects':objs,'closest_object_color':order[0],'farthest_object_color':order[-1],'depth_ordering':order,'seed':i,'difficulty_score':round(.3+.14*(n-2)+.18*(min(abs(a-b) for a,b in itertools_pairs(depths))<.2),4)}
  row['questions']=depth_questions(iid,row,rng)
 else:
  n=rng.randint(2,4);colors=rng.sample(PALETTE,n);counts=rng.sample(range(2,8),n);xs=[(j+1)*w/(n+1) for j in range(n)];st=[]
  for j,(name,rgb) in enumerate(colors):c=counts[j];st.append({'index':j,'color':name,'rgb':list(rgb),'position_x':round(xs[j],4),'block_count':c,'pixel_height':(c-1)*BLOCK_PITCH+BLOCK_H})
  order=[x['color'] for x in sorted(st,key=lambda z:z['block_count'],reverse=True)];render_stacks(images/f'{iid}.png',(w,h),st);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'scene_type':kind,'block_width_px':BLOCK_W,'block_height_px':BLOCK_H,'block_pitch_px':BLOCK_PITCH,'stacks':st,'tallest_stack_color':order[0],'shortest_stack_color':order[-1],'height_ordering':order,'seed':i,'difficulty_score':round(.28+.14*(n-2)+.07*max(counts),4)};row['questions']=stack_questions(iid,row,rng)
 return row
def itertools_pairs(x):return [(x[i],x[j]) for i in range(len(x)) for j in range(i+1,len(x))]
def generate_dataset(n,out,sample=False):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True);ids=list(range(1,n+1)) if not sample else list(range(1,11))
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for k,i in enumerate(ids,1):f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n');print(f'Generated {k}/{len(ids)}') if k%250==0 or k==len(ids) else None
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='depth_height_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
