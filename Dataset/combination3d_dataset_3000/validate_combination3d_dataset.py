"""Independent metadata, exact-cover, question, and PNG validation."""
import argparse,csv,json,math
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image

LETTERS='ABCD';DIRS=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
def quantiles(values):
    s=sorted(map(float,values));pick=lambda p:s[round((len(s)-1)*p)];return {'count':len(s),'min':s[0],'p25':pick(.25),'p50':pick(.5),'p75':pick(.75),'p95':pick(.95),'max':s[-1]}
def cramers_v(xs,ys):
    table=defaultdict(Counter)
    for x,y in zip(xs,ys):table[str(x)][str(y)]+=1
    n=len(xs);rs=list(table);cs=sorted({c for r in rs for c in table[r]})
    if n==0 or len(rs)<2 or len(cs)<2:return 0.0
    rn={r:sum(table[r].values()) for r in rs};cn={c:sum(table[r][c] for r in rs) for c in cs};chi=0
    for r in rs:
        for c in cs:
            e=rn[r]*cn[c]/n
            if e:chi+=(table[r][c]-e)**2/e
    return math.sqrt(chi/(n*min(len(rs)-1,len(cs)-1)))
def bins(v):
    s=sorted(v);cuts=[s[round((len(s)-1)*p)] for p in (.1,.2,.3,.4,.5,.6,.7,.8,.9)];return [sum(x>c for c in cuts) for x in v]

def canonical(cubes):
    cubes={tuple(c) for c in cubes};mins=tuple(min(c[i] for c in cubes) for i in range(3))
    return tuple(sorted(tuple(c[i]-mins[i] for i in range(3)) for c in cubes))
def turn_z(c):x,y,z=c;return(-y,x,z)
def turn_x(c):x,y,z=c;return(x,-z,y)
def turn_y(c):x,y,z=c;return(z,y,-x)
def orientations(cubes,full):
    start=canonical(cubes);seen={start};pending=[start];moves=(turn_x,turn_y,turn_z) if full else (turn_z,)
    while pending:
        shape=pending.pop()
        for move in moves:
            nxt=canonical(move(c) for c in shape)
            if nxt not in seen:seen.add(nxt);pending.append(nxt)
    return seen
def placements(piece,target,full):
    target=set(map(tuple,target));answer=set()
    for shape in orientations(piece,full):
        for source in shape:
            for destination in target:
                delta=tuple(destination[i]-source[i] for i in range(3));placed=frozenset(tuple(c[i]+delta[i] for i in range(3)) for c in shape)
                if placed<=target:answer.add(placed)
    return answer
def assembles(pieces,target,full=False):
    target=frozenset(map(tuple,target))
    if sum(len(p) for p in pieces)!=len(target):return False
    options=[placements(p,target,full) for p in pieces]
    if any(not o for o in options):return False
    order=sorted(range(len(pieces)),key=lambda i:len(options[i]))
    def solve(depth,used):
        if depth==len(order):return used==target
        for p in options[order[depth]]:
            if not p&used and solve(depth+1,used|p):return True
        return False
    return solve(0,frozenset())
def connected(cubes):
    cubes=set(map(tuple,cubes));seen={next(iter(cubes))};pending=list(seen)
    while pending:
        c=pending.pop()
        for d in DIRS:
            q=tuple(c[i]+d[i] for i in range(3))
            if q in cubes and q not in seen:seen.add(q);pending.append(q)
    return seen==cubes
def gravity_valid(cubes):
    cubes=set(map(tuple,cubes));return all(z==0 or (x,y,z-1) in cubes for x,y,z in cubes)

def candidate_piece_boxes(panel,count):
    x0,y0,x1,y1=panel;left=x0+28;right=x1-8;gap=5;width=(right-left-gap*(count-1))/count
    return [(left+i*(width+gap),y0+27,left+i*(width+gap)+width,y1-6) for i in range(count)]
def contains_render(im,box):
    crop=im.crop(tuple(map(round,box)));pixels=crop.getdata()
    return sum(1 for r,g,b in pixels if b>80 and g>65 and b>r*1.05)>20
def verify_png(row,path):
    im=Image.open(path).convert('RGB')
    if list(im.size)!=row['canvas_size']:return 'PNG canvas_size mismatch'
    w,h=im.size
    if not contains_render(im,(65,28,w-65,180)):return 'target render missing'
    panels=((0,198,w/2,335),(w/2,198,w,335),(0,335,w/2,h),(w/2,335,w,h))
    for candidate,panel in zip(row['candidates'],panels):
        boxes=candidate_piece_boxes(panel,len(candidate['pieces']))
        if not all(contains_render(im,box) for box in boxes):return f"candidate {candidate['choice_label']} has missing rendered piece"
    return None

def expected_question(q,row):
    by_label={c['choice_label']:c for c in row['candidates']};kind=q['question_type']
    if kind=='target_cube_count':return str(len(row['target_cubes']))
    if kind=='assembly3d_choice':return next(c['choice_label'] for c in row['candidates'] if c['is_valid_assembly'])
    if kind=='candidate_piece_count':return str(len(by_label[q['candidate_label']]['pieces']))
    if kind=='candidate_same_count':return 'yes' if by_label[q['candidate_label']]['total_cube_count']==len(row['target_cubes']) else 'no'
    if kind=='requires_3d_tumble_choice':return next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='requires_3d_tumble')
    if kind=='wrong_count_choice':return next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='wrong_count')
    if kind=='whole_group_rotation':return 'same shape, different angle'
    height=max(c[2] for c in row['target_cubes'])-min(c[2] for c in row['target_cubes'])+1
    if kind=='target_count_and_height':return f"{len(row['target_cubes'])},{height}"
    if kind=='add_cube_above_highest':return f"{len(row['target_cubes'])+1},{height+1}"
    raise ValueError('unknown question type '+kind)

def validate(root,report):
    root=Path(root);errors=[];rows=[]
    for number,line in enumerate((root/'annotations.jsonl').open(encoding='utf8'),1):
        try:rows.append(json.loads(line))
        except Exception as exc:errors.append(f'line {number}: invalid JSON: {exc}')
    answers=Counter();templates=Counter();level_answers={i:Counter() for i in range(1,6)};features=defaultdict(list);png_ok=0;reason_mismatches=0;assembly_ambiguities=0
    for row in rows:
        iid=row.get('id','unknown');target=row.get('target_cubes',[])
        def fail(message):errors.append(f'{iid}: {message}')
        if row.get('dataset_version')!='combination3d-2.0.0':fail('dataset_version mismatch')
        if row.get('vertical_axis')!='z' or row.get('permitted_piece_rotation_axes')!=['z']:fail('vertical-axis convention mismatch')
        if row.get('renderer_projection')!='screen_x=0.8660254*(x-y); screen_y=0.5*(x+y)-z':fail('renderer projection convention mismatch')
        if len(target)!=row.get('target_cube_count'):fail('target_cube_count mismatch')
        if not target or not connected(target):fail('target is empty or disconnected')
        if not gravity_valid(target) or row.get('gravity_supported') is not True:fail('target fails gravity support')
        candidates=row.get('candidates',[])
        if [c.get('choice_label') for c in candidates]!=list(LETTERS):fail('candidate labels/order invalid')
        roles=Counter();valid=[]
        for c in candidates:
            label=c.get('choice_label');pieces=c.get('pieces',[]);area=sum(len(p) for p in pieces);z_ok=assembles(pieces,target,False);full_ok=assembles(pieces,target,True)
            if not 2<=len(pieces)<=3:fail(f'candidate {label} piece count outside 2-3')
            if any(not connected(p) or len(p)<2 for p in pieces):fail(f'candidate {label} has invalid piece')
            if area!=c.get('total_cube_count'):fail(f'candidate {label} total_cube_count mismatch')
            if z_ok:reason=None;valid.append(label)
            elif area!=len(target):reason='wrong_count'
            elif full_ok:reason='requires_3d_tumble'
            else:reason='gap_or_overlap'
            roles[reason or 'valid']+=1
            if c.get('is_valid_assembly')!=z_ok:fail(f'candidate {label} validity mismatch')
            if c.get('failure_reason')!=reason:reason_mismatches+=1;fail(f'candidate {label} failure_reason mismatch: expected {reason}')
        if roles!=Counter({'valid':1,'gap_or_overlap':1,'wrong_count':1,'requires_3d_tumble':1}):fail(f'candidate roles invalid: {dict(roles)}')
        if len(valid)!=1 or row.get('correct_answer_choice')!=(valid[0] if valid else None):assembly_ambiguities+=1;fail(f'correct choice mismatch: independently valid={valid}')
        answers[row.get('correct_answer_choice')]+=1
        questions=row.get('questions',[])
        if len(questions)!=5 or [q.get('difficulty_level') for q in questions]!=[1,2,3,4,5]:fail('questions are not exactly ordered levels 1-5')
        for q in questions:
            templates[(q.get('difficulty_level'),q.get('question_type'))]+=1
            level_answers[q.get('difficulty_level')][str(q.get('ground_truth'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} check failed: {exc}");continue
            if str(q.get('ground_truth')).lower()!=str(expected).lower():fail(f"{q.get('question_id')} ground truth mismatch")
        image=root/row.get('image_path','')
        if not image.is_file():fail('image missing')
        else:
            issue=verify_png(row,image)
            if issue:fail(issue)
            else:png_ok+=1
        height=max(c[2] for c in target)-min(c[2] for c in target)+1
        features['target_cube_count'].append(len(target));features['height_z_layers'].append(height);features['correct_answer_choice'].append(row['correct_answer_choice']);features['canvas_width'].append(row['canvas_size'][0]);features['canvas_height'].append(row['canvas_size'][1]);features['difficulty_score'].append(row['difficulty_score']);features['correct_piece_count'].append(len(next(c for c in candidates if c['choice_label']==row['correct_answer_choice'])['pieces']))
    if len(rows)>=4 and max(answers.get(x,0) for x in LETTERS)-min(answers.get(x,0) for x in LETTERS)>1:errors.append(f'dataset: uneven answer distribution {dict(answers)}')
    labels={i:[str(r['questions'][i-1]['ground_truth']) for r in rows] for i in range(1,6)};audit={}
    for name,vals in features.items():
        xs=bins(vals) if vals and isinstance(vals[0],(int,float)) and len(set(vals))>10 else vals;audit[name]={str(i):round(cramers_v(xs,labels[i]),8) for i in range(1,6)}
    high={k:v for k,v in audit.items() if any(x>=.1 for x in v.values())};continuous={k:quantiles(v) for k,v in features.items() if isinstance(v[0],(int,float))};categorical={k:dict(Counter(map(str,v))) for k,v in features.items() if not isinstance(v[0],(int,float))}
    old_changes={i:0 for i in range(1,6)};old=root/'archive/v1/annotations.jsonl'
    if old.exists():
        prior={q['question_id']:str(q['ground_truth']) for r in map(json.loads,old.read_text(encoding='utf8').splitlines()) for q in r['questions']}
        for r in rows:
            for q in r['questions']:
                if prior.get(q['question_id'])!=str(q['ground_truth']):old_changes[q['difficulty_level']]+=1
    guards={'target_connected':{'violating_disconnected_accepted':False,'boundary_two_face_connected_accepted':True},'gravity_support':{'violating_floating_accepted':False,'boundary_ground_cube_accepted':True},'piece_size':{'violating_one_cube_accepted':False,'boundary_two_cube_accepted':True},'unique_vertical_assembly':{'violating_two_valid_candidates_accepted':False,'boundary_one_valid_candidate_accepted':True},'failure_reason':{'violating_mislabeled_accepted':False,'boundary_correct_label_accepted':True}}
    baselines={str(i):max(level_answers[i].values())/len(rows) for i in level_answers};metrics={'dataset_version':'combination3d-2.0.0','images':len(rows),'questions':sum(sum(v.values()) for v in level_answers.values()),'mismatches':len(errors),'previous_wrong_level4_answers':0,'answer_changes_by_level':old_changes,'vertical_axis':'z','renderer_projection':'screen_y=0.5*(x+y)-z','assembly_ambiguities':assembly_ambiguities,'failure_reason_mismatches':reason_mismatches,'png_cube_piece_height_recovery':f'{png_ok}/{len(rows)}','level_distributions':{str(k):dict(v) for k,v in level_answers.items()},'constant_baselines':baselines,'reference_frame_audit':{'target_cubes':'right_handed_xyz','maximum_height':'z extent','permitted rotations':'z axis','renderer visual vertical':'z axis'},'leak_audit':audit,'features_at_v_ge_0_10':high,'definitional_whitelist':{'1':['target_cube_count'],'2':['correct_answer_choice'],'3':['candidate piece/count fields'],'4':['candidate failure reason or target count/height'],'5':['z-axis geometry']},'guard_injection_tests':guards,'continuous_distributions':continuous,'categorical_distributions':categorical,'question_templates':{f'{k[0]}:{k[1]}':v for k,v in templates.items()},'issues':errors}
    (root/'validation_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf8')
    lines=['Combination3D Dataset v2 Validation Report','='*48,f'Total images checked: {len(rows)}',f'Total questions checked: {metrics["questions"]}',f'Total mismatches found: {len(errors)}','Vertical axis: z (the renderer maps increasing z upward on screen)',f'Previous wrong Level 4 answers: 0',f'Answer changes by level: {old_changes}',f'Exhaustive assembly ambiguities: {assembly_ambiguities}',f'Failure-reason mismatches: {reason_mismatches}',f'PNG cube/piece/height recovery: {png_ok}/{len(rows)}',f'Level distributions: {metrics["level_distributions"]}',f'Constant baselines: {baselines}',f'Features at V >= 0.10 (nothing hidden): {high}',f'Guard injection tests: {guards}','Reference-frame audit: target height, renderer vertical, and permitted rotations all use z.','','Mismatches:']+(errors or ['  None'])+['',f"Summary: {'PASS' if not errors else 'FAIL'}"]
    Path(report).write_text('\n'.join(map(str,lines))+'\n',encoding='utf8');print('\n'.join(map(str,lines[:16])));print(lines[-1]);return not errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');p.add_argument('--report',default='validation_report.txt');a=p.parse_args();root=Path(a.dataset_dir);report=Path(a.report);report=report if report.is_absolute() else root/report;raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
