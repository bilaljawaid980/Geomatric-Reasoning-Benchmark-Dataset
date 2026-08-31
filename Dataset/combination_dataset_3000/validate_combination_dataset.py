import argparse,json
from collections import Counter
from pathlib import Path
from PIL import Image

LETTERS='ABCD'
DIRS=((1,0),(-1,0),(0,1),(0,-1))

def canonical(cells):
    cells={tuple(x) for x in cells};minx=min(x for x,y in cells);miny=min(y for x,y in cells)
    return tuple(sorted((x-minx,y-miny) for x,y in cells))

def orientations(cells,reflections=False):
    result=set()
    for mirror in ([False,True] if reflections else [False]):
        base=[(-x,y) if mirror else (x,y) for x,y in cells]
        for turns in range(4):
            rotated=[]
            for x,y in base:
                for _ in range(turns):x,y=-y,x
                rotated.append((x,y))
            result.add(canonical(rotated))
    return result

def possible_placements(piece,target,reflections=False):
    target=set(target);result=set()
    for shape in orientations(piece,reflections):
        for sx,sy in shape:
            for tx,ty in target:
                placed=frozenset((x-sx+tx,y-sy+ty) for x,y in shape)
                if placed<=target:result.add(placed)
    return result

def assembles(pieces,target,reflections=False):
    target=frozenset(map(tuple,target))
    if sum(len(p) for p in pieces)!=len(target):return False
    options=[possible_placements(p,target,reflections) for p in pieces]
    if any(not p for p in options):return False
    order=sorted(range(len(pieces)),key=lambda i:len(options[i]))
    def search(depth,used):
        if depth==len(order):return used==target
        for placement in options[order[depth]]:
            if not used&placement and search(depth+1,used|placement):return True
        return False
    return search(0,frozenset())

def connected(cells):
    cells=set(map(tuple,cells));seen={next(iter(cells))};todo=list(seen)
    while todo:
        x,y=todo.pop()
        for dx,dy in DIRS:
            q=(x+dx,y+dy)
            if q in cells and q not in seen:seen.add(q);todo.append(q)
    return seen==cells

def bounds(cells):
    cells=canonical(cells);return max(x for x,y in cells)+1,max(y for x,y in cells)+1

def candidate_layout(pieces,panel):
    x0,y0,x1,y1=panel;dims=[bounds(p) for p in pieces];units=sum(w for w,h in dims)+len(pieces)-1
    cell=min(18.0,(x1-x0-42)/max(1,units),(y1-y0-40)/max(h for w,h in dims));gap=cell
    widths=[w*cell for w,h in dims];x=x0+(x1-x0-sum(widths)-gap*(len(pieces)-1))/2;result=[]
    for p,pw,(wc,hc) in zip(pieces,widths,dims):
        result.append((p,x,y0+30+(y1-y0-35-hc*cell)/2,cell));x+=pw+gap
    return result

def nearby_ink(px,x,y,radius=3):
    w,h=px.size;x=int(round(x));y=int(round(y))
    for yy in range(max(0,y-radius),min(h,y+radius+1)):
        for xx in range(max(0,x-radius),min(w,x+radius+1)):
            r,g,b=px.getpixel((xx,yy))[:3]
            if r+g+b>390:return True
    return False

def check_render(row,image_path):
    im=Image.open(image_path).convert('RGB')
    if list(im.size)!=row['canvas_size']:return 'canvas size mismatch'
    w,h=im.size;target=row['target_cells'];tw,th=bounds(target);cell=min(28,125/max(tw,th));ox=w/2-tw*cell/2;oy=38
    layouts=[(target,ox,oy,cell)]
    panels=[(0,180,w/2,315),(w/2,180,w,315),(0,315,w/2,h),(w/2,315,w,h)]
    for candidate,panel in zip(row['candidates'],panels):layouts.extend(candidate_layout(candidate['pieces'],panel))
    for cells,x0,y0,size in layouts:
        for x,y in cells:
            probes=((x0+(x+.5)*size,y0+y*size),(x0+x*size,y0+(y+.5)*size),
                    (x0+(x+1)*size,y0+(y+.5)*size),(x0+(x+.5)*size,y0+(y+1)*size))
            if not all(nearby_ink(im,*p) for p in probes):return 'rendered cell boundary missing'
    return None

def expected_question(q,row):
    typ=q['question_type'];by_label={c['choice_label']:c for c in row['candidates']}
    if typ=='target_cell_count':return str(len(row['target_cells']))
    if typ=='assembly_choice':return next(c['choice_label'] for c in row['candidates'] if c['is_valid_assembly'])
    if typ=='candidate_piece_count':return str(len(by_label[q['candidate_label']]['pieces']))
    if typ=='candidate_same_area':return 'yes' if by_label[q['candidate_label']]['total_cell_count']==len(row['target_cells']) else 'no'
    if typ=='requires_reflection_choice':return next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='requires_reflection')
    if typ=='wrong_area_choice':return next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='wrong_area')
    if typ=='extra_cell_connectivity':return 'yes'
    raise ValueError('unknown question type '+typ)

def validate(root,report_path):
    root=Path(root);errors=[];rows=[]
    with (root/'annotations.jsonl').open(encoding='utf8') as handle:
        for line_no,line in enumerate(handle,1):
            try:rows.append(json.loads(line))
            except Exception as exc:errors.append(f'line {line_no}: invalid JSON: {exc}')
    choices=Counter();template_counts=Counter()
    for row in rows:
        iid=row.get('id','unknown');target=row.get('target_cells',[])
        def fail(message):errors.append(f'{iid}: {message}')
        if not target or not connected(target):fail('target is empty or disconnected')
        if len(target)!=row.get('target_cell_count'):fail('target_cell_count mismatch')
        candidates=row.get('candidates',[])
        if [c.get('choice_label') for c in candidates]!=list(LETTERS):fail('candidate labels/order invalid')
        valid_labels=[];role_counts=Counter()
        for c in candidates:
            pieces=c.get('pieces',[]);area=sum(len(p) for p in pieces);rot=assembles(pieces,target,False);refl=assembles(pieces,target,True)
            if area!=c.get('total_cell_count'):fail(f"candidate {c.get('choice_label')} total_cell_count mismatch")
            if any(not connected(p) for p in pieces):fail(f"candidate {c.get('choice_label')} has disconnected piece")
            expected_flag=rot
            if c.get('is_valid_assembly')!=expected_flag:fail(f"candidate {c.get('choice_label')} validity mismatch")
            if rot:valid_labels.append(c['choice_label']);expected_reason=None
            elif area!=len(target):expected_reason='wrong_area'
            elif refl:expected_reason='requires_reflection'
            else:expected_reason='gap_or_overlap'
            if c.get('failure_reason')!=expected_reason:fail(f"candidate {c.get('choice_label')} failure_reason mismatch: expected {expected_reason}")
            role_counts[expected_reason or 'valid']+=1
        if len(valid_labels)!=1:fail(f'exactly one valid candidate required, found {valid_labels}')
        if role_counts!=Counter({'valid':1,'gap_or_overlap':1,'wrong_area':1,'requires_reflection':1}):fail(f'candidate roles invalid: {dict(role_counts)}')
        if valid_labels and row.get('correct_answer_choice')!=valid_labels[0]:fail('correct_answer_choice mismatch')
        choices[row.get('correct_answer_choice')]+=1
        questions=row.get('questions',[])
        if len(questions)!=4 or [q.get('difficulty_level') for q in questions]!=[1,2,3,4]:fail('questions must contain ordered levels 1-4')
        for q in questions:
            template_counts[(q.get('difficulty_level'),q.get('question_type'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} cannot be checked: {exc}");continue
            if str(q.get('ground_truth')).lower()!=str(expected).lower():fail(f"{q.get('question_id')} ground truth mismatch: {q.get('ground_truth')} != {expected}")
        image_path=root/row.get('image_path','')
        if not image_path.is_file():fail('image missing')
        else:
            issue=check_render(row,image_path)
            if issue:fail(issue)
    if len(rows)>=4 and max(choices.values(),default=0)-min(choices.get(x,0) for x in LETTERS)>1:errors.append(f'dataset: answer distribution uneven: {dict(choices)}')
    lines=[f'Total images checked: {len(rows)}',f'Total mismatches found: {len(errors)}',f'Correct answer distribution: {dict(sorted(choices.items()))}','Question template counts:']
    lines.extend(f'  Level {level} / {typ}: {count}' for (level,typ),count in sorted(template_counts.items()))
    lines.extend(['','Mismatches:']);lines.extend(errors or ['  None']);lines.extend(['',f"Summary: {'PASS' if not errors else 'FAIL'}"])
    Path(report_path).write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines[:3]));print(lines[-1])
    return not errors

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dataset-dir',default='.');parser.add_argument('--report',default='validation_report.txt');args=parser.parse_args()
    root=Path(args.dataset_dir);report=Path(args.report);report=report if report.is_absolute() else root/report
    raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
