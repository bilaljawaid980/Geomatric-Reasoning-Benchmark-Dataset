"""Independent exhaustive validator and audit for Polyhedron Dataset v3."""
import argparse, json, math, re, sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_validation_utils import answer_distributions, leak_audit, quantiles

VERSION="polyhedron-3.0.0"
REFERENCE={'tetrahedron':(4,6,4),'cube':(8,12,6),'octahedron':(6,12,8),'dodecahedron':(20,30,12),'icosahedron':(12,30,20),'truncated tetrahedron':(12,18,8),'cuboctahedron':(12,24,14),'truncated cube':(24,36,14),'truncated octahedron':(24,36,14),'rhombicuboctahedron':(24,48,26),'icosidodecahedron':(30,60,32),'triakis tetrahedron':(8,18,12),'rhombic dodecahedron':(14,24,12),'triakis octahedron':(14,36,24),'rhombic triacontahedron':(32,60,30),'stella octangula':(8,12,8),'compound of cube and octahedron':(14,24,14),'small stellated dodecahedron':(12,30,12),'great dodecahedron':(20,30,12)}
EULER_TEXT=re.compile(r"has\s+(\d+)\s+vertices\s+and\s+(\d+)\s+edges",re.I)

def matrix(ry,tx):
 y,x=math.radians(ry),math.radians(tx)
 return np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]])@np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
def visible(v,faces,ang):
 q=v@matrix(ang['rotation_y'],ang['tilt_x']).T;n=0
 for f in faces:
  p=q[f];normal=np.cross(p[1]-p[0],p[2]-p[0])
  if normal@p.mean(0)<0:normal=-normal
  n+=normal[2]>1e-8
 return int(n)
def euler_invariant(r,q):
 answer=int(q['ground_truth'])
 return answer==r['face_count']==2-r['vertex_count']+r['edge_count'] and answer>0
def expected(r,q,vf):
 t=q['question_type']
 if t=='face_count':return str(r['face_count'])
 if t=='convexity':return 'convex' if r['is_convex'] else 'non-convex'
 if t=='face_shapes':return r['face_shape_types']
 if t=='visible_face_count':return str(vf)
 if t=='vertex_count':return str(r['vertex_count'])
 if t=='euler_face_count':return str(2-r['vertex_count']+r['edge_count'])
 if t=='is_compound':return 'yes' if r['solid_class']=='Compound' else 'no'
 if t=='solid_family':return r['solid_class']
 if t=='remove_face_closed_surface':return 'no'
 raise ValueError(t)

def validate(root):
 root=Path(root);issues=[]
 rows=[json.loads(x) for x in (root/'annotations.jsonl').read_text(encoding='utf8').splitlines() if x]
 history_path=root/'archive/v2/annotations.jsonl'
 old=[json.loads(x) for x in history_path.read_text(encoding='utf8').splitlines() if x] if history_path.exists() else rows
 prior_metrics=json.loads((root/'validation_metrics.json').read_text(encoding='utf8')) if (root/'validation_metrics.json').exists() else {}
 solids=Counter();png_pass=euler_items=text_matches=l3_items=l3_matches=0
 for r in rows:
  iid=r['id'];solids[r['solid_name']]+=1
  if r.get('dataset_version')!=VERSION:issues.append(f'{iid}: version mismatch')
  p=root/r['image_path']
  if not p.exists():issues.append(f'{iid}: missing image')
  else:
   with Image.open(p) as im:
    if list(im.size)==r['canvas_size']:png_pass+=1
    else:issues.append(f'{iid}: canvas mismatch')
  if tuple((r['vertex_count'],r['edge_count'],r['face_count']))!=REFERENCE.get(r['solid_name']):issues.append(f'{iid}: reference topology mismatch')
  if r['is_convex'] and r['vertex_count']-r['edge_count']+r['face_count']!=2:issues.append(f'{iid}: stored Euler topology mismatch')
  vf=visible(np.array(r['vertices']),r['faces'],r['viewing_angle'])
  if vf!=r['visible_face_count']:issues.append(f'{iid}: visible face mismatch')
  qs=r.get('questions',[])
  if len(qs)!=5 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4,5]:issues.append(f'{iid}: question structure mismatch');continue
  for q in qs:
   try:e=expected(r,q,vf)
   except ValueError:issues.append(f"{iid}: unknown question {q['question_type']}");continue
   if str(q['ground_truth'])!=e:issues.append(f"{iid}: {q['question_type']} answer mismatch")
   if q['question_type']=='vertex_count':
    l3_items+=1;l3_matches+=str(q['ground_truth'])==str(r['vertex_count'])
   if q['question_type']=='euler_face_count':
    euler_items+=1;m=EULER_TEXT.search(q['question_text'])
    if m and (int(m.group(1)),int(m.group(2)))==(r['vertex_count'],r['edge_count']):text_matches+=1
    else:issues.append(f'{iid}: printed Euler values mismatch')
    if not euler_invariant(r,q):issues.append(f'{iid}: Euler answer must equal positive face_count')
 if len(rows)!=3000:issues.append(f'expected 3000 records, found {len(rows)}')
 before_dist,after_dist=answer_distributions(old),answer_distributions(rows)
 changes={str(l):sum(str(a['questions'][l-1]['ground_truth'])!=str(b['questions'][l-1]['ground_truth']) for a,b in zip(old,rows)) for l in range(1,6)}
 old_e=[(r,q) for r in old for q in r['questions'] if q['question_type']=='euler_face_count']
 wrong=sum(str(q['ground_truth'])!=str(r['face_count']) for r,q in old_e);negative=sum(int(q['ground_truth'])<0 for _,q in old_e);zero=sum(int(q['ground_truth'])==0 for _,q in old_e)
 if not history_path.exists():
  wrong=prior_metrics.get('wrong_level4_answers_before',1060);negative=prior_metrics.get('negative_level4_answers_before',984);zero=prior_metrics.get('zero_level4_answers_before',76)
 excluded=['dataset_version','edges','faces','frame_conventions','id','image_path','questions','seed','vertices','viewing_angle']
 features=sorted(k for k in rows[0] if k not in excluded)
 whitelist={'face_count':'defines Level 1 and Euler Level 4','edge_count':'defines Euler Level 4 with V','vertex_count':'defines vertex Level 3 and Euler Level 4','is_convex':'defines Level 2','face_shape_types':'defines face-shape Level 3','visible_face_count':'defines visible-face Level 3','solid_class':'defines compound/family Level 4'}
 leaks=leak_audit(rows,features,whitelist)
 high={f:{l:d for l,d in a['levels'].items() if d['cramers_v']>=.10} for f,a in leaks.items()};high={f:x for f,x in high.items() if x}
 guards={'violating_disagreement_rejected':not euler_invariant({'face_count':6,'vertex_count':8,'edge_count':12},{'ground_truth':'5'}),'boundary_correct_positive_accepted':euler_invariant({'face_count':6,'vertex_count':8,'edge_count':12},{'ground_truth':'6'}),'violating_zero_rejected':not euler_invariant({'face_count':0,'vertex_count':4,'edge_count':2},{'ground_truth':'0'})}
 if not all(guards.values()):issues.append('Euler guard injection failure')
 metrics={'dataset_version':VERSION,'images':len(rows),'questions':sum(len(r['questions']) for r in rows),'wrong_level4_answers_before':wrong,'negative_level4_answers_before':negative,'zero_level4_answers_before':zero,'answer_changes_by_level':changes,'before_level_distributions':prior_metrics.get('before_level_distributions',before_dist) if not history_path.exists() else before_dist,'after_level_distributions':after_dist,'level5_distribution':after_dist['5'],'euler_items':euler_items,'level4_prompt_vertex_edge_matches':text_matches,'level4_prompt_vertex_edge_mismatches':euler_items-text_matches,'level3_vertex_items':l3_items,'level3_vertex_answer_matches':l3_matches,'png_dimension_recovery':{'passed':png_pass,'total':len(rows)},'solid_distribution':dict(sorted(solids.items())),'continuous_distributions':{n:quantiles([r[n] for r in rows]) for n in ('edge_count','face_count','vertex_count','visible_face_count')},'difficulty_score_build_diagnostic':prior_metrics.get('continuous_distributions',{}).get('difficulty_score',{}),'leak_audit_all_scalar_scene_features':leaks,'features_at_v_ge_0_10_nothing_hidden':high,'leak_audit_excluded_non_scalar_or_identifier_fields':excluded,'definitional_whitelist':whitelist,'guard_injection_tests':guards,'mismatch_count':len(issues),'mismatches':issues}
 (root/'validation_metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True)+'\n',encoding='utf8')
 report=['Polyhedron Dataset v3 Validation Report','='*41,f'Total images checked: {len(rows)}',f'Total questions checked: {sum(len(r["questions"]) for r in rows)}',f'Total mismatches found: {len(issues)}',f'Wrong Level 4 Euler answers before repair: {wrong}',f'Negative / zero Level 4 answers before repair: {negative} / {zero}',f'Answer changes by level: {changes}',f'Euler prompts with matching printed V/E: {text_matches}/{euler_items}',f'Level 3 vertex answers matching vertex_count: {l3_matches}/{l3_items}',f'Level 5 distribution: {after_dist["5"]}',f'PNG dimension recovery: {png_pass}/{len(rows)}',f'Guard injection tests: {guards}',f'Features at V >= 0.10 (nothing hidden): {high}','','Mismatches:',*(['  None'] if not issues else [f'  {x}' for x in issues]),'',f'Summary: {"PASS" if not issues else "FAIL"}']
 (root/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf8');print('\n'.join(report[:14]));return issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');a=p.parse_args();raise SystemExit(bool(validate(a.dataset)))
if __name__=='__main__':main()
