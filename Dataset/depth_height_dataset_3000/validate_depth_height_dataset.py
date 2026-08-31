import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image
import numpy as np
def psize(base,d):return base*(1-.4*d)
def color_bbox(arr,rgb,region):
 x0,y0,x1,y1=region;x0=max(0,int(x0));y0=max(0,int(y0));x1=min(arr.shape[1],int(x1));y1=min(arr.shape[0],int(y1));crop=arr[y0:y1,x0:x1];delta=crop.astype(np.int32)-np.array(rgb,dtype=np.int32);ys,xs=np.where(np.sum(delta*delta,axis=2)<=48**2)
 return None if not len(xs) else (int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0),int(ys.max()+y0))
def validate(root):
 root=Path(root);issues=[];dist=Counter();types=Counter();lines=(root/'annotations.jsonl').read_text(encoding='utf8').splitlines()
 for line in lines:
  r=json.loads(line);iid=r['id'];dist[r['scene_type']]+=1;p=root/r['image_path']
  if not p.exists():issues.append(f'{iid}: missing image');continue
  with Image.open(p) as src:im=src.convert('RGB')
  arr=np.asarray(im)
  if list(im.size)!=r['canvas_size']:issues.append(f'{iid}: canvas mismatch')
  if r['scene_type']=='depth_ordering':
   items=r['objects'];lookup={o['color']:o for o in items};order=[o['color'] for o in sorted(items,key=lambda z:z['depth_value'])]
   if order!=r['depth_ordering'] or order[0]!=r['closest_object_color'] or order[-1]!=r['farthest_object_color']:issues.append(f'{iid}: depth ordering mismatch')
   for o in items:
    expected=psize(r['base_size_px'],o['depth_value'])
    if abs(expected-o['rendered_size'])>.02:issues.append(f"{iid}: size metadata mismatch {o['index']}")
    cx,cy=o['canvas_position'];b=color_bbox(arr,o['rgb'],(cx-expected,cy-expected,cx+expected,cy+expected))
    if b is None:issues.append(f"{iid}: color absent in PNG {o['index']}")
    else:
     measured=max(b[2]-b[0]+1,b[3]-b[1]+1)
     if abs(measured-round(expected))>3:issues.append(f"{iid}: PNG size mismatch {o['index']}")
  else:
   items=r['stacks'];lookup={s['color']:s for s in items};order=[s['color'] for s in sorted(items,key=lambda z:z['block_count'],reverse=True)]
   if order!=r['height_ordering'] or order[0]!=r['tallest_stack_color'] or order[-1]!=r['shortest_stack_color']:issues.append(f'{iid}: height ordering mismatch')
   for s in items:
    expected=(s['block_count']-1)*r['block_pitch_px']+r['block_height_px']
    if expected!=s['pixel_height']:issues.append(f"{iid}: stack height metadata mismatch {s['index']}")
    ground=im.height-38;b=color_bbox(arr,s['rgb'],(s['position_x']-r['block_width_px'],ground-expected-5,s['position_x']+r['block_width_px'],ground+4))
    if b is None:issues.append(f"{iid}: stack color absent {s['index']}")
    elif abs((b[3]-b[1]+1)-expected)>3:issues.append(f"{iid}: PNG stack height mismatch {s['index']}")
  qs=r.get('questions',[])
  if len(qs)!=4 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4]:issues.append(f'{iid}: question structure mismatch');continue
  for q in qs:
   t=q['question_type'];types[t]+=1
   if t=='object_count':e=str(len(items))
   elif t=='pair_closer':
    named=[c for c in lookup if c in q['question_text']];e=min((lookup[c] for c in named),key=lambda z:z['depth_value'])['color']
   elif t=='depth_ordering':e=order
   elif t=='counterfactual_size':
    a=lookup[q['subject_color']];b=lookup[q['comparison_color']];new=psize(r['base_size_px'],min(1,a['depth_value']*2));e='larger' if new>b['rendered_size']+.5 else 'smaller' if new<b['rendered_size']-.5 else 'same'
   elif t=='stack_count':e=str(len(items))
   elif t=='pair_taller':
    named=[c for c in lookup if c in q['question_text']];e=max((lookup[c] for c in named),key=lambda z:z['block_count'])['color']
   elif t=='height_ordering':e=order
   elif t=='total_blocks':e=str(sum(s['block_count'] for s in items))
   elif t=='transfer_blocks':
    tall=max(items,key=lambda z:z['block_count']);short=min(items,key=lambda z:z['block_count']);post={z['color']:z['block_count'] for z in items};post[tall['color']]-=2;post[short['color']]+=2;mx=max(post.values());e='yes' if post[short['color']]==mx and sum(v==mx for v in post.values())==1 else 'no'
   else:issues.append(f'{iid}: unknown question {t}');continue
   if q['ground_truth']!=e:issues.append(f'{iid}: {t} answer mismatch')
 if len(lines)>=3000 and abs(dist['depth_ordering']-dist['stack_height'])>30:issues.append('scene balance outside tolerance')
 report=[f'Total images checked: {len(lines)}',f'Total mismatches found: {len(issues)}',f"Scene distribution: depth_ordering={dist['depth_ordering']}, stack_height={dist['stack_height']}",'Question distribution:']+[f'  {k}: {v}' for k,v in sorted(types.items())]+[f"Summary: {'PASS' if not issues else 'FAIL'}"]+issues;(root/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf8');print('\n'.join(report[:18]));return len(lines),issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();_,x=validate(a.dataset);raise SystemExit(bool(x))
if __name__=='__main__':main()
