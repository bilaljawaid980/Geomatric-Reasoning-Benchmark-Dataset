import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image
def key(a,b):return tuple(sorted((tuple(a),tuple(b))))
def embedding(tv,segs):return {key(a,b) for a,b in zip(tv,tv[1:]+tv[:1])}<={key(a,b) for a,b in segs}
def closed(tv):return len(tv)>=3 and len({tuple(x) for x in tv})==len(tv) and all(key(a,b) for a,b in zip(tv,tv[1:]+tv[:1]))
def edge_pixels(im,a,b):
 good=0;total=16
 for k in range(1,total):
  t=k/total;x=round(a[0]+(b[0]-a[0])*t);y=round(a[1]+(b[1]-a[1])*t);hit=False
  for yy in range(max(0,y-2),min(im.height,y+3)):
   for xx in range(max(0,x-2),min(im.width,x+3)):
    if sum(im.getpixel((xx,yy)))>180:hit=True
  good+=hit
 return good>=12
def normalized(v):
 cx=sum(p[0] for p in v)/len(v);cy=sum(p[1] for p in v)/len(v);r=max(math.hypot(p[0]-cx,p[1]-cy) for p in v);return [((p[0]-cx)/r,(p[1]-cy)/r) for p in v]
def validate(root):
 root=Path(root);issues=[];shapes=Counter();answers=Counter();types=Counter();lines=(root/'annotations.jsonl').read_text(encoding='utf8').splitlines()
 for line in lines:
  r=json.loads(line);iid=r['id'];shapes[r['target_shape_type']]+=1;answers[r['correct_answer_choice']]+=1;p=root/r['image_path']
  if not p.exists():issues.append(f'{iid}: missing image');continue
  with Image.open(p) as src:im=src.convert('RGB')
  if list(im.size)!=r['canvas_size']:issues.append(f'{iid}: canvas mismatch')
  tv=r['target_vertices'];segs=r['segments'];n=len(tv)
  if not embedding(tv,segs):issues.append(f'{iid}: target edges absent from segment network')
  if not closed(tv):issues.append(f'{iid}: target is not a closed polygon')
  if r['num_total_segments']!=len(segs) or r['num_distractor_segments']!=len(segs)-n:issues.append(f'{iid}: segment counts mismatch')
  if not all(edge_pixels(im,a,b) for a,b in zip(tv,tv[1:]+tv[:1])):issues.append(f'{iid}: target edge missing from PNG')
  cands=r['candidate_choices'];correct=[c for c in cands if c['is_correct']]
  if len(correct)!=1 or correct[0]['label']!=r['correct_answer_choice'] or correct[0]['side_count']!=n:issues.append(f'{iid}: candidate metadata mismatch')
  elif max(math.hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(normalized(tv),normalized(correct[0]['vertices'])))>.002:issues.append(f'{iid}: correct candidate proportions mismatch')
  same=any(not c['is_correct'] and c['side_count']==n for c in cands)
  if same!=r['same_side_foil_exists']:issues.append(f'{iid}: same-side foil mismatch')
  qs=r.get('questions',[])
  if len(qs)!=4 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4]:issues.append(f'{iid}: question structure mismatch');continue
  for q in qs:
   t=q['question_type'];types[t]+=1
   if t=='total_segments':e=str(len(segs))
   elif t=='target_side_count':e=str(n)
   elif t=='embedded_choice':e=correct[0]['label']
   elif t=='distractor_segment_count':e=str(len(segs)-n)
   elif t=='target_closure':e='closed' if closed(tv) else 'open'
   elif t=='same_side_foil_exists':e='yes' if same else 'no'
   else:issues.append(f'{iid}: unknown question {t}');continue
   if q['ground_truth']!=e:issues.append(f'{iid}: {t} answer mismatch')
 if len(lines)>=3000:
  if min(shapes.values())<700 or min(answers.values())<700:issues.append('distribution uneven')
 report=[f'Total images checked: {len(lines)}',f'Total mismatches found: {len(issues)}','Target distribution:']+[f'  {k}: {v}' for k,v in sorted(shapes.items())]+['Correct-choice distribution:']+[f'  {k}: {v}' for k,v in sorted(answers.items())]+[f"Summary: {'PASS' if not issues else 'FAIL'}"]+issues;(root/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf8');print('\n'.join(report[:16]));return len(lines),issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();_,x=validate(a.dataset);raise SystemExit(bool(x))
if __name__=='__main__':main()
