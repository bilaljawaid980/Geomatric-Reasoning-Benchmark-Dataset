import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image
def transforms(kind):
 if kind.startswith('rotational_'):
  n=int(kind.rsplit('_',1)[1]);return [('rot',360/n)]
 if kind=='mirror_horizontal':return [('h',0)]
 if kind=='mirror_vertical':return [('v',0)]
 return [('h',0),('v',0)]
def apply(s,tr):
 x,y=s['center'];kind,a=tr
 if kind=='rot':q=math.radians(a);c=math.cos(q);sn=math.sin(q);return (x*c-y*sn,x*sn+y*c,(s['rotation_angle']+a)%90)
 if kind=='h':return(x,-y,(-s['rotation_angle'])%90)
 return(-x,y,(-s['rotation_angle'])%90)
def adiff(a,b):return min(abs(a-b)%90,90-abs(a-b)%90)
def match(s,t,tr,attrs=True):
 x,y,a=apply(s,tr)
 if math.hypot(x-t['center'][0],y-t['center'][1])>.08:return False
 return not attrs or (adiff(a,t['rotation_angle'])<.08 and abs(s['size']-t['size'])<.08 and s['filled']==t['filled'])
def mismatch_indices(shapes,kind):
 bad=set()
 for tr in transforms(kind):
  for i,s in enumerate(shapes):
   if not any(match(s,t,tr,True) for t in shapes):bad.add(i)
 return bad
def symmetric(shapes,kind):return not mismatch_indices(shapes,kind)
def pos_transform(p,kind):
 x,y=p
 if kind.startswith('rotational_'):q=math.tau/int(kind.rsplit('_',1)[1]);return(x*math.cos(q)-y*math.sin(q),x*math.sin(q)+y*math.cos(q))
 if kind=='mirror_horizontal':return(x,-y)
 return(-x,y)
def partners(shapes,kind):
 n=0
 for i,s in enumerate(shapes):
  x,y=pos_transform(s['center'],kind)
  if any(i!=j and math.hypot(x-t['center'][0],y-t['center'][1])<=2 for j,t in enumerate(shapes)):n+=1
 return n
def loc(p):
 x,y=p
 if abs(x)<28 and abs(y)<28:return 'center'
 return ('top' if y<0 else 'bottom')+'-'+('left' if x<0 else 'right')
def validate(root):
 root=Path(root);issues=[];classes=Counter();kinds=Counter();breaks=Counter();lines=(root/'annotations.jsonl').read_text(encoding='utf8').splitlines()
 for line in lines:
  r=json.loads(line);iid=r['id'];s=r['shapes'];kind=r['symmetry_type'];classes[r['is_broken']]+=1;kinds[kind]+=1;breaks[r['break_type']]+=1;p=root/r['image_path']
  if not p.exists():issues.append(f'{iid}: missing image');continue
  with Image.open(p) as im:
   if list(im.size)!=r['canvas_size']:issues.append(f'{iid}: canvas mismatch')
  bad=mismatch_indices(s,kind);derived=bool(bad)
  if derived!=r['is_broken']:issues.append(f'{iid}: symmetry status mismatch')
  if derived:
   bi=r['broken_shape_index']
   if bi not in bad:issues.append(f'{iid}: identified shape not anomalous')
   if any(s[j]['orbit_id']!=s[bi]['orbit_id'] for j in bad):issues.append(f'{iid}: more than one orbit broken')
   if r['broken_shape_position']!=s[bi]['center']:issues.append(f'{iid}: broken position mismatch')
  elif r['broken_shape_index'] is not None:issues.append(f'{iid}: unbroken has broken index')
  pc=partners(s,kind)
  if pc!=r['symmetric_partner_count']:issues.append(f'{iid}: partner count mismatch')
  qs=r.get('questions',[])
  if len(qs)!=4 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4]:issues.append(f'{iid}: question structure mismatch');continue
  for q in qs:
   t=q['question_type']
   if t=='shape_count':e=str(len(s))
   elif t=='symmetry_status':e='broken' if derived else 'symmetric'
   elif t=='broken_location':e=loc(s[r['broken_shape_index']]['center'])
   elif t=='symmetry_family':e='rotational' if kind.startswith('rotational') else 'mirror'
   elif t=='break_type':e={'fill':'filled','rotation':'rotated','position':'shifted','size':'different size'}[r['break_type']]
   elif t=='rotation_90_invariant':e='yes' if not derived and kind in ('rotational_4','rotational_6') else 'no'
   elif t=='symmetric_partner_count':e=str(pc)
   else:issues.append(f'{iid}: unknown question {t}');continue
   if q['ground_truth']!=e:issues.append(f'{iid}: {t} answer mismatch')
 if len(lines)>=3000:
  if abs(classes[True]-classes[False])>30:issues.append('class balance outside tolerance')
  if min(kinds.values())<400:issues.append('symmetry type distribution uneven')
  if min(v for k,v in breaks.items() if k is not None)<350:issues.append('break distribution uneven')
 report=[f'Total images checked: {len(lines)}',f'Total mismatches found: {len(issues)}',f"Class distribution: broken={classes[True]}, unbroken={classes[False]}",'Symmetry distribution:']+[f'  {k}: {v}' for k,v in sorted(kinds.items())]+['Break distribution:']+[f'  {k}: {v}' for k,v in sorted((str(k),v) for k,v in breaks.items())]+[f"Summary: {'PASS' if not issues else 'FAIL'}"]+issues;(root/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf8');print('\n'.join(report[:18]));return len(lines),issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();_,x=validate(a.dataset);raise SystemExit(bool(x))
if __name__=='__main__':main()
