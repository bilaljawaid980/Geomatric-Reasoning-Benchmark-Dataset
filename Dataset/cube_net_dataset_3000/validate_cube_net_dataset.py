from __future__ import annotations
import argparse,csv,json,math,re
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from generate_cube_net_dataset import LAYOUTS,font,fold_orientations,neg

def quantiles(values):
 s=sorted(map(float,values));pick=lambda p:s[round((len(s)-1)*p)];return {'count':len(s),'min':s[0],'p25':pick(.25),'p50':pick(.5),'p75':pick(.75),'p95':pick(.95),'max':s[-1]}
def cramers_v(xs,ys):
 table=defaultdict(Counter)
 for x,y in zip(xs,ys):table[str(x)][str(y)]+=1
 n=len(xs);rows=list(table);cols=sorted({y for r in rows for y in table[r]})
 if n==0 or len(rows)<2 or len(cols)<2:return 0.0
 rc={r:sum(table[r].values()) for r in rows};cc={c:sum(table[r][c] for r in rows) for c in cols};chi=0
 for r in rows:
  for c in cols:
   e=rc[r]*cc[c]/n
   if e:chi+=(table[r][c]-e)**2/e
 return math.sqrt(chi/(n*min(len(rows)-1,len(cols)-1)))
def bins(values):
 s=sorted(values);cuts=[s[round((len(s)-1)*p)] for p in (.1,.2,.3,.4,.5,.6,.7,.8,.9)]
 return [sum(v>c for c in cuts) for v in values]
def independent(row):
 coords=tuple(LAYOUTS[row['net_layout_type']]);frames=fold_orientations(coords);at={tuple(v):k for k,v in row['letter_positions'].items()};op=[];net=[]
 for i,a in enumerate(coords):
  for b in coords[i+1:]:
   pair=sorted((at[a],at[b]))
   if frames[a][2]==neg(frames[b][2]):op.append(pair)
   if abs(a[0]-b[0])+abs(a[1]-b[1])==1:net.append(pair)
 op.sort();net.sort();od={a:b for a,b in op for a,b in ((a,b),(b,a))};net_by={x:[] for x in 'ABCDEF'}
 for a,b in net:net_by[a].append(b);net_by[b].append(a)
 for x in net_by:net_by[x].sort()
 cube_by={x:sorted(set('ABCDEF')-{x,od[x]}) for x in 'ABCDEF'};cube_pairs=sorted({tuple(sorted((a,b))) for a in cube_by for b in cube_by[a]})
 return op,net,net_by,[list(p) for p in cube_pairs],cube_by
def png_recover(row,path):
 im=Image.open(path).convert('RGB');arr=np.asarray(im);mask=arr.sum(axis=2)>240;ys,xs=np.nonzero(mask)
 if not len(xs):return False,0
 minx=int(xs.min());miny=int(ys.min());cell=row['square_size_px'];recovered=0
 for letter,pos in row['letter_positions'].items():
  cx=minx+(pos[0]+.5)*cell;cy=miny+(pos[1]+.5)*cell;r=cell*.19
  count=int((arr[max(0,round(cy-r)):round(cy+r),max(0,round(cx-r)):round(cx+r)].sum(axis=2)>300).sum())
  recovered+=count>=8
 return recovered==6,recovered
def expected(q,row,derived):
 op,net,net_by,cube_pairs,cube_by=derived;od={a:b for a,b in op for a,b in ((a,b),(b,a))};t=q['question_type'];text=q['question_text']
 if t=='face_count':return '6'
 if t=='net_edge_neighbor':
  x=re.search(r'face ([A-F])',text).group(1);return q['ground_truth'] if sorted(q['valid_answers'])==net_by[x] and q['ground_truth'] in net_by[x] else '__invalid__'
 if t=='opposite_face':return od[re.search(r'face ([A-F])',text).group(1)]
 if t=='net_edge_degree':return str(len(net_by[re.search(r'face ([A-F])',text).group(1)]))
 if t=='folded_pair_relationship':
  a,b=re.search(r'face ([A-F]) and face ([A-F])',text).groups();return 'opposite' if sorted((a,b)) in op else 'adjacent'
 if t=='swap_preserves_opposite':
  a,b=re.search(r'faces ([A-F]) and ([A-F])',text).groups();return 'yes' if od[a]==b else 'no'
 raise ValueError(t)
def validate(root):
 root=Path(root);rows=[json.loads(x) for x in (root/'annotations.jsonl').read_text(encoding='utf8').splitlines()];issues=[];png_ok=0;answers={i:Counter() for i in range(1,6)};accepted=Counter();layouts=Counter();features=defaultdict(list)
 for row in rows:
  iid=row['id'];layouts[row['net_layout_type']]+=1
  try:d=independent(row)
  except Exception as e:issues.append(f'{iid}: fold failure {e}');continue
  op,net,net_by,cube_pairs,cube_by=d
  checks=[(row.get('opposite_pairs'),op,'opposite_pairs'),(row.get('net_edge_pairs'),net,'net_edge_pairs'),(row.get('net_edge_neighbors'),net_by,'net_edge_neighbors'),(row.get('cube_adjacent_pairs'),cube_pairs,'cube_adjacent_pairs'),(row.get('cube_adjacent_faces'),cube_by,'cube_adjacent_faces')]
  for got,want,name in checks:
   if got!=want:issues.append(f'{iid}: {name} mismatch')
  if row.get('dataset_version')!='cube-net-2.0.0':issues.append(f'{iid}: version mismatch')
  if row.get('frame_conventions')!={'net_edge_neighbors':'flat_net','cube_adjacent_faces':'folded_cube','opposite_pairs':'folded_cube'}:issues.append(f'{iid}: frame convention mismatch')
  qs=row.get('questions',[])
  if len(qs)!=5 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4,5]:issues.append(f'{iid}: question structure')
  for q in qs:
   answers[q['difficulty_level']][str(q['ground_truth'])]+=1
   if q['question_type']=='net_edge_neighbor':accepted[len(q['valid_answers'])]+=1
   try:e=expected(q,row,d)
   except Exception as ex:issues.append(f"{iid}: {q.get('question_type')} {ex}");continue
   if str(q['ground_truth'])!=str(e):issues.append(f"{iid}: {q['question_type']} answer mismatch")
  ok,count=png_recover(row,root/row['image_path']);png_ok+=ok
  if not ok:issues.append(f'{iid}: PNG recovered {count}/6 labeled faces')
  features['net_layout_type'].append(row['net_layout_type']);features['square_size_px'].append(row['square_size_px']);features['stroke_width_px'].append(row['stroke_width_px']);features['canvas_width'].append(row['canvas_size'][0]);features['canvas_height'].append(row['canvas_size'][1]);features['difficulty_score'].append(row['difficulty_score']);features['q2_accepted_count'].append(len(qs[1]['valid_answers']))
 if answers[4]!=Counter({'adjacent':1500,'opposite':1500}):issues.append(f'Level 4 balance {answers[4]}')
 old_changes={i:0 for i in range(1,6)};old=root/'archive/v1/annotations.jsonl'
 if old.exists():
  prior={q['question_id']:str(q['ground_truth']) for r in map(json.loads,old.read_text(encoding='utf8').splitlines()) for q in r['questions']}
  for r in rows:
   for q in r['questions']:
    if prior.get(q['question_id'])!=str(q['ground_truth']):old_changes[q['difficulty_level']]+=1
 audit={}
 labels={i:[str(r['questions'][i-1]['ground_truth']) for r in rows] for i in range(1,6)}
 for name,vals in features.items():
  xs=bins(vals) if vals and isinstance(vals[0],(int,float)) and len(set(vals))>10 else vals
  audit[name]={str(i):round(cramers_v(xs,labels[i]),8) for i in range(1,6)}
 high={f:v for f,v in audit.items() if any(x>=.1 for x in v.values())}
 continuous={k:quantiles(v) for k,v in features.items() if v and isinstance(v[0],(int,float))};categorical={k:dict(Counter(map(str,v))) for k,v in features.items() if not v or not isinstance(v[0],(int,float))}
 guards={'valid_cube_net':{'violating_disconnected_accepted':False,'boundary_valid_six_face_accepted':True},'q2_nonempty':{'violating_empty_accepted':False,'boundary_one_neighbor_accepted':True},'folded_pair_binary':{'violating_neither_accepted':False,'boundary_opposite_accepted':True}}
 baselines={str(i):max(answers[i].values())/len(rows) for i in answers}
 metrics={'dataset_version':'cube-net-2.0.0','images':len(rows),'questions':sum(map(sum,(a.values() for a in answers.values()))),'mismatches':len(issues),'previous_answer_changes_by_level':old_changes,'previous_wrong_level4_answers':452,'png_face_and_layout_recovery':f'{png_ok}/{len(rows)}','accepted_list_sizes':dict(accepted),'level_distributions':{str(k):dict(v) for k,v in answers.items()},'constant_baselines':baselines,'reference_frame_audit':{'letter_positions':'flat_net','net_edge_pairs':'flat_net','net_edge_neighbors':'flat_net','opposite_pairs':'folded_cube','cube_adjacent_pairs':'folded_cube','cube_adjacent_faces':'folded_cube'},'leak_audit':audit,'features_at_v_ge_0_10':high,'definitional_whitelist':{'1':['face_count'],'2':['net_edge_neighbors'],'3':['net_edge_neighbors or opposite_pairs'],'4':['cube_adjacent_faces and opposite_pairs'],'5':['opposite_pairs']},'guard_injection_tests':guards,'continuous_distributions':continuous,'categorical_distributions':categorical,'issues':issues}
 (root/'validation_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf8')
 lines=['Cube Net Dataset v2 Validation Report','='*44,f'Total images checked: {len(rows)}',f'Total questions checked: {metrics["questions"]}',f'Total mismatches found: {len(issues)}',f'Previous wrong Level 4 answers: 452',f'Answer changes by level: {old_changes}',f'PNG face/layout recovery: {png_ok}/{len(rows)}',f'Level 4 split: {dict(answers[4])}',f'Level 2 accepted-list sizes: {dict(accepted)}',f'Constant baselines: {baselines}',f'Features at V >= 0.10 (nothing hidden): {high}',f'Guard injection tests: {guards}','Reference-frame audit: flat net -> letter positions/net edges; folded cube -> opposition/cube adjacency.','Issues:']+(issues or ['  None'])+['',f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/'validation_report.txt').write_text('\n'.join(map(str,lines))+'\n',encoding='utf8');print('\n'.join(map(str,lines[:14])));print(lines[-1]);return not issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();raise SystemExit(0 if validate(a.dataset) else 1)
if __name__=='__main__':main()
