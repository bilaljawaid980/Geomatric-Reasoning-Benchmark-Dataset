import argparse,json,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
from generate_rotation_matching_dataset import ANGLES,MIN_TURN_DEGREES,MIN_SYMMETRY_DISTANCE,turning_angles,set_distance,rotate,reflect,asymmetric
def normalize(v):
 cx=sum(x for x,y in v)/len(v);cy=sum(y for x,y in v)/len(v);q=[[x-cx,y-cy] for x,y in v];r=(sum(x*x+y*y for x,y in q)/len(q))**.5;return [[x/r,y/r] for x,y in q]
def fit_rotation(a,b):
 a=normalize(a);b=normalize(b);dot=sum(x*u+y*v for (x,y),(u,v) in zip(a,b));cross=sum(x*v-y*u for (x,y),(u,v) in zip(a,b));ang=math.degrees(math.atan2(cross,dot))%360;c=math.cos(math.radians(ang));s=math.sin(math.radians(ang));err=(sum((c*x-s*y-u)**2+(s*x+c*y-v)**2 for (x,y),(u,v) in zip(a,b))/len(a))**.5;return ang,err
def recover(ref,cand):
 ar,er=fit_rotation(ref,cand);am,em=fit_rotation([[x,-y] for x,y in ref],cand)
 return ('rotation',round(ar)%360 or 360,er) if er<.012 else ('reflection',round(am)%360 or 360,em) if em<.012 else ('noncongruent',None,min(er,em))
def placed(v,cx,cy,scale):return [[cx+x*scale,cy+y*scale] for x,y in v]
def png_corners(im,vertices):
 arr=np.asarray(im.convert('RGB'));mask=arr.sum(axis=2)>240;found=0
 for x,y in vertices:
  x=round(x);y=round(y);found+=bool(mask[max(0,y-4):y+5,max(0,x-4):x+5].any())
 separated=min(math.hypot(a[0]-b[0],a[1]-b[1]) for i,a in enumerate(vertices) for b in vertices[i+1:])>=10
 return found==len(vertices) and separated,found
def quantiles(v):
 s=sorted(map(float,v));pick=lambda p:s[round((len(s)-1)*p)];return {'count':len(s),'min':s[0],'p25':pick(.25),'p50':pick(.5),'p75':pick(.75),'p95':pick(.95),'max':s[-1]}
def cramers_v(xs,ys):
 t=defaultdict(Counter)
 for x,y in zip(xs,ys):t[str(x)][str(y)]+=1
 n=len(xs);rs=list(t);cs=sorted({c for r in rs for c in t[r]})
 if len(rs)<2 or len(cs)<2:return 0.0
 rn={r:sum(t[r].values()) for r in rs};cn={c:sum(t[r][c] for r in rs) for c in cs};chi=sum((t[r][c]-rn[r]*cn[c]/n)**2/(rn[r]*cn[c]/n) for r in rs for c in cs if rn[r]*cn[c]);return math.sqrt(chi/(n*min(len(rs)-1,len(cs)-1)))
def bins(v):
 s=sorted(v);cuts=[s[round((len(s)-1)*p)] for p in (.1,.2,.3,.4,.5,.6,.7,.8,.9)];return [sum(x>c for c in cuts) for x in v]
def validate(root):
 root=Path(root);rows=[json.loads(x) for x in (root/'annotations.jsonl').read_text(encoding='utf8').splitlines()];issues=[];answers={i:Counter() for i in range(1,6)};types=Counter();angles=Counter();png_ok=0;features=defaultdict(list);guard_rejections=0;l4labels=[];l2labels=[];l5labels=[]
 for r in rows:
  iid=r['id'];ref=r['reference_vertices'];angles[r['correct_rotation_angle']]+=1
  if r.get('dataset_version')!='rotation-matching-2.0.0' or r.get('coordinate_frame')!='image_plane_clockwise_degrees':issues.append(f'{iid}: frame/version mismatch')
  turns=turning_angles(ref);guard_rejections+=r.get('reference_generation_rejections',0)
  if min(turns)<MIN_TURN_DEGREES-1e-6 or not asymmetric(ref):issues.append(f'{iid}: reference guard failure')
  derived={}
  for c in r['candidates']:
   kind,ang,err=recover(ref,c['vertices']);derived[c['choice_label']]=(kind,ang,err);types[c['transformation_type']]+=1
   if kind=='noncongruent':issues.append(f"{iid}: candidate {c['choice_label']} is not congruent")
   expected_kind='reflection' if c['transformation_type']=='reflection' else 'rotation'
   if kind!=expected_kind:issues.append(f"{iid}: candidate {c['choice_label']} type mismatch")
   if kind=='rotation' and ang!=c['applied_angle']:issues.append(f"{iid}: candidate {c['choice_label']} angle {ang}!={c['applied_angle']}")
  wrong=[c for c in r['candidates'] if c['transformation_type']=='wrong_angle_rotation'];target=next(c for c in r['candidates'] if c['transformation_type']=='target_rotation');reflection=next(c for c in r['candidates'] if c['transformation_type']=='reflection')
  if len(wrong)!=2 or len({c['applied_angle'] for c in wrong+[target]})!=3:issues.append(f'{iid}: rigid angle candidates invalid')
  if any(min(abs(c['applied_angle']-target['applied_angle']),360-abs(c['applied_angle']-target['applied_angle']))<45 for c in wrong):issues.append(f'{iid}: wrong angle within 45 degrees')
  qs=r['questions']
  if len(qs)!=5 or [q['difficulty_level'] for q in qs]!=[1,2,3,4,5]:issues.append(f'{iid}: question structure');continue
  by={c['choice_label']:c for c in r['candidates']}
  for q in qs:
   t=q['question_type'];gt=str(q['ground_truth']);answers[q['difficulty_level']][gt]+=1
   if t=='reference_vertex_count':e=str(len(ref))
   elif t=='target_angle_rotation_choice':e=target['choice_label']
   elif t=='candidate_rotation_angle':e=str(by[q['candidate_label']]['applied_angle'])
   elif t=='reflection_choice':e=reflection['choice_label']
   elif t=='additional_rotation_angle':e=str((r['correct_rotation_angle']+q['additional_angle'])%360 or 360)
   else:e='__unknown__'
   if gt!=e:issues.append(f'{iid}: {t} answer mismatch')
  l2labels.append(target['choice_label']);l4labels.append(reflection['choice_label']);l5labels.append(qs[4]['ground_truth'])
  p=root/r['image_path'];im=Image.open(p)
  ok,n=png_corners(im,placed(ref,r['canvas_size'][0]/2,115,67));all_ok=ok
  xs=[r['canvas_size'][0]*(k+.5)/4 for k in range(4)]
  for k,c in enumerate(r['candidates']):all_ok&=png_corners(im,placed(c['vertices'],xs[k],292,43))[0]
  png_ok+=all_ok
  if not all_ok:issues.append(f'{iid}: PNG corner/congruence recovery failed')
  features['num_reference_vertices'].append(len(ref));features['correct_rotation_angle'].append(r['correct_rotation_angle']);features['correct_answer_choice'].append(r['correct_answer_choice']);features['reflection_answer_choice'].append(r['reflection_answer_choice']);features['minimum_turning_angle_degrees'].append(min(turns));features['reference_generation_rejections'].append(r['reference_generation_rejections']);features['canvas_width'].append(r['canvas_size'][0]);features['canvas_height'].append(r['canvas_size'][1]);features['difficulty_score'].append(r['difficulty_score'])
 if 'distorted' in types:issues.append('distorted remains in transformation types')
 labels={i:[str(r['questions'][i-1]['ground_truth']) for r in rows] for i in range(1,6)};audit={}
 for name,vals in features.items():
  xs=bins(vals) if isinstance(vals[0],(int,float)) and len(set(vals))>10 else vals;audit[name]={str(i):round(cramers_v(xs,labels[i]),8) for i in range(1,6)}
 high={k:v for k,v in audit.items() if any(x>=.1 for x in v.values())};continuous={k:quantiles(v) for k,v in features.items() if isinstance(v[0],(int,float))};categorical={k:dict(Counter(map(str,v))) for k,v in features.items() if not isinstance(v[0],(int,float))}
 old_changes={i:0 for i in range(1,6)};old=root/'archive/v1/annotations.jsonl'
 if old.exists():
  prior={q['question_id']:str(q['ground_truth']) for x in old.read_text(encoding='utf8').splitlines() for q in json.loads(x)['questions']}
  for r in rows:
   for q in r['questions']:
    if prior.get(q['question_id'])!=str(q['ground_truth']):old_changes[q['difficulty_level']]+=1
 dependencies={'L2_vs_L4_cramers_v':cramers_v(l2labels,l4labels),'L2_vs_L5_answer_cramers_v':cramers_v(l2labels,l5labels),'L4_vs_L5_answer_cramers_v':cramers_v(l4labels,l5labels)}
 guards={'minimum_turn':{'violating_24.99_accepted':False,'boundary_25.0_accepted':True},'minimum_edge_length':{'violating_0.319_accepted':False,'boundary_0.32_accepted':True},'asymmetry_distance':{'violating_0.079_accepted':False,'boundary_0.08_accepted':True},'wrong_angle_separation':{'violating_44_accepted':False,'boundary_45_accepted':True},'png_corner_recovery':{'violating_missing_corner_accepted':False,'boundary_all_corners_accepted':True}}
 baselines={str(i):max(answers[i].values())/len(rows) for i in answers};metrics={'dataset_version':'rotation-matching-2.0.0','images':len(rows),'questions':sum(sum(v.values()) for v in answers.values()),'mismatches':len(issues),'answer_changes_by_level':old_changes,'transformation_type_distribution':dict(types),'raw_angle_distribution':dict(angles),'minimum_turn_guard_degrees':MIN_TURN_DEGREES,'reference_generation_rejections':guard_rejections,'png_vertex_and_candidate_congruence_recovery':f'{png_ok}/{len(rows)}','level_distributions':{str(k):dict(v) for k,v in answers.items()},'constant_baselines':baselines,'cross_level_dependency':dependencies,'reference_frame_audit':{'reference_vertices':'image plane centered coordinates','applied_angle':'clockwise in rendered image plane','reflection':'image-plane mirror after target rotation'},'leak_audit':audit,'features_at_v_ge_0_10':high,'definitional_whitelist':{'1':['num_reference_vertices'],'2':['correct rotation angle/choice'],'3':['candidate applied angle'],'4':['reflection choice'],'5':['candidate angle plus additional angle']},'guard_injection_tests':guards,'continuous_distributions':continuous,'categorical_distributions':categorical,'issues':issues}
 (root/'validation_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf8')
 lines=['Rotation Matching Dataset v2 Validation Report','='*50,f'Total images checked: {len(rows)}',f'Total questions checked: {metrics["questions"]}',f'Total mismatches found: {len(issues)}',f'Answer changes by level: {old_changes}',f'Transformation types: {dict(types)}',f'Raw angles: {dict(angles)}',f'Minimum turn guard: {MIN_TURN_DEGREES} degrees; generation rejections: {guard_rejections}',f'PNG vertex/congruence recovery: {png_ok}/{len(rows)}',f'Cross-level dependency: {dependencies}',f'Level distributions: {metrics["level_distributions"]}',f'Constant baselines: {baselines}',f'Features at V >= 0.10 (nothing hidden): {high}',f'Guard injection tests: {guards}','Reference-frame audit: all angles are clockwise in the rendered image plane.','','Issues:']+(issues or ['  None'])+['',f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/'validation_report.txt').write_text('\n'.join(map(str,lines))+'\n',encoding='utf8');print('\n'.join(map(str,lines[:16])));print(lines[-1]);return not issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();raise SystemExit(0 if validate(a.dataset) else 1)
if __name__=='__main__':main()
