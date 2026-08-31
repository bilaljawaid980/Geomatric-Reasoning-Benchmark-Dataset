"""Independent fold simulation, label, question, and rendered-PNG validation."""
import argparse,json
from collections import Counter,deque
from pathlib import Path
from PIL import Image

LETTERS='ABCD'
def simulate_reverse(sequence,punch):
    bounds=(0.0,1.0,0.0,1.0);records=[]
    for fold in sequence:
        xmin,xmax,ymin,ymax=bounds
        if fold['axis']=='vertical':
            mid=(xmin+xmax)/2
            if fold['direction']=='right over left':after=(xmin,mid,ymin,ymax)
            elif fold['direction']=='left over right':after=(mid,xmax,ymin,ymax)
            else:raise ValueError('invalid vertical direction')
        elif fold['axis']=='horizontal':
            mid=(ymin+ymax)/2
            if fold['direction']=='top over bottom':after=(xmin,xmax,ymin,mid)
            elif fold['direction']=='bottom over top':after=(xmin,xmax,mid,ymax)
            else:raise ValueError('invalid horizontal direction')
        else:raise ValueError('invalid fold axis')
        records.append((fold,mid));bounds=after
    points={tuple(punch)}
    for fold,mid in reversed(records):
        expanded=set()
        for x,y in points:
            expanded.add((x,y));expanded.add((2*mid-x,y) if fold['axis']=='vertical' else (x,2*mid-y))
        points=expanded
    return sorted((round(x,6),round(y,6)) for x,y in points),bounds
def normalized(points):return sorted((round(float(x),6),round(float(y),6)) for x,y in points)
def reflected(points,axis):
    return normalized(((1-x,y) if axis=='vertical' else (x,1-y)) for x,y in points)
def required_symmetries(sequence):return {f['axis'] for f in sequence}

def candidate_boxes(size):
    w,h=size;divider=150;mid=(h+divider)/2;panels=((0,divider+3,w/2,mid),(w/2,divider+3,w,mid),(0,mid,w/2,h),(w/2,mid,w,h));boxes=[]
    for x0,y0,x1,y1 in panels:
        side=min(y1-y0-6,x1-x0-42);boxes.append((x0+(x1-x0-side)/2,y0+3,x0+(x1-x0+side)/2,y0+3+side))
    return boxes
def dark_near(im,x,y,radius=3):
    for yy in range(max(0,round(y)-radius),min(im.height,round(y)+radius+1)):
        for xx in range(max(0,round(x)-radius),min(im.width,round(x)+radius+1)):
            if sum(im.getpixel((xx,yy)))<150:return True
    return False
def count_dot_components(im,box):
    x0,y0,x1,y1=map(round,box);x0+=2;y0+=2;x1-=2;y1-=2;dark=set()
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b=im.getpixel((x,y))
            if r<55 and g<55 and b<55:dark.add((x,y))
    components=[]
    while dark:
        start=dark.pop();todo=[start];area=1
        while todo:
            x,y=todo.pop()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                q=(x+dx,y+dy)
                if q in dark:dark.remove(q);todo.append(q);area+=1
        if area>=10:components.append(area)
    return len(components)
def verify_png(row,path):
    im=Image.open(path).convert('RGB')
    if list(im.size)!=row['canvas_size']:return 'canvas_size mismatch'
    w,h=im.size;count=len(row['fold_sequence'])+1;gap=6;step_w=(w-20-gap*(count-1))/count;final_box=(10+len(row['fold_sequence'])*(step_w+gap),24,10+len(row['fold_sequence'])*(step_w+gap)+step_w,129)
    xmin,xmax,ymin,ymax=row['final_folded_bounds'];x0,y0,x1,y1=final_box;maxdim=max(xmax-xmin,ymax-ymin);scale=min((x1-x0-8)/maxdim,(y1-y0-8)/maxdim);cx=(x0+x1)/2;cy=(y0+y1)/2;rect=(cx-(xmax-xmin)*scale/2,cy-(ymax-ymin)*scale/2,cx+(xmax-xmin)*scale/2,cy+(ymax-ymin)*scale/2);px=rect[0]+(row['punch_position'][0]-xmin)/(xmax-xmin)*(rect[2]-rect[0]);py=rect[3]-(row['punch_position'][1]-ymin)/(ymax-ymin)*(rect[3]-rect[1])
    if not dark_near(im,px,py,5):return 'punch-panel dot missing'
    for candidate,box in zip(row['candidates'],candidate_boxes(im.size)):
        x0,y0,x1,y1=box
        if count_dot_components(im,box)!=len(candidate['hole_positions']):return f"candidate {candidate['choice_label']} rendered dot count mismatch"
        for x,y in candidate['hole_positions']:
            px=x0+x*(x1-x0);py=y1-y*(y1-y0)
            if not dark_near(im,px,py):return f"candidate {candidate['choice_label']} rendered dot position missing"
    return None
def expected_question(q,row):
    kind=q['question_type']
    if kind=='fold_count':return str(len(row['fold_sequence']))
    if kind=='unfolded_hole_count':return str(2**len(row['fold_sequence']))
    if kind=='correct_pattern_choice':return next(c['choice_label'] for c in row['candidates'] if c['error_type'] is None)
    if kind=='wrong_positions_choice':return next(c['choice_label'] for c in row['candidates'] if c['error_type']=='wrong_positions')
    if kind=='wrong_count_choice':return next(c['choice_label'] for c in row['candidates'] if c['error_type']=='wrong_count')
    if kind=='remove_last_fold':return 'exactly half'
    if kind=='additional_fold_hole_count':return str(2**(len(row['fold_sequence'])+1))
    raise ValueError('unknown question type '+kind)
def validate(root,report):
    root=Path(root);errors=[];rows=[]
    for number,line in enumerate((root/'annotations.jsonl').open(encoding='utf8'),1):
        try:rows.append(json.loads(line))
        except Exception as exc:errors.append(f'line {number}: invalid JSON: {exc}')
    answers=Counter();fold_counts=Counter();templates=Counter()
    for row in rows:
        iid=row.get('id','unknown')
        def fail(message):errors.append(f'{iid}: {message}')
        sequence=row.get('fold_sequence',[]);n=len(sequence);fold_counts[n]+=1
        if row.get('num_folds')!=n or n not in (2,3):fail('num_folds invalid')
        try:correct,bounds=simulate_reverse(sequence,row['punch_position'])
        except Exception as exc:fail(f'fold simulation failed: {exc}');continue
        stored=normalized(row.get('unfolded_hole_positions',[]))
        if stored!=correct:fail('unfolded_hole_positions mismatch')
        if any(abs(a-b)>1e-6 for a,b in zip(bounds,row.get('final_folded_bounds',[]))):fail('final_folded_bounds mismatch')
        if len(correct)!=2**n or row.get('num_holes')!=2**n:fail('power-of-two hole count mismatch')
        labels=[];roles=Counter();symmetries=required_symmetries(sequence)
        for c in row.get('candidates',[]):
            label=c.get('choice_label');holes=normalized(c.get('hole_positions',[]));error=c.get('error_type');roles[error or 'correct']+=1
            if holes==correct:labels.append(label)
            if error is None and holes!=correct:fail(f'candidate {label} marked correct but differs')
            elif error=='wrong_count' and len(holes)==len(correct):fail(f'candidate {label} wrong_count is not genuine')
            elif error=='wrong_positions':
                if len(holes)!=len(correct) or holes==correct:fail(f'candidate {label} wrong_positions is not genuine')
                if any(reflected(holes,axis)!=holes for axis in symmetries):fail(f'candidate {label} wrong_positions does not preserve required symmetry')
            elif error=='wrong_symmetry':
                if len(holes)!=len(correct) or holes==correct:fail(f'candidate {label} wrong_symmetry is not genuine')
                if all(reflected(holes,axis)==holes for axis in symmetries):fail(f'candidate {label} does not break a required symmetry')
                if not c.get('wrong_symmetry_axis'):fail(f'candidate {label} lacks wrong-axis provenance')
                nearest=max(min(((x-a)**2+(y-b)**2)**.5 for a,b in correct) for x,y in holes)
                if nearest<.04-1e-9:fail(f'candidate {label} displacement below 0.04')
            elif error not in (None,'wrong_count','wrong_positions','wrong_symmetry'):fail(f'candidate {label} has invalid error_type')
        if [c.get('choice_label') for c in row.get('candidates',[])]!=list(LETTERS):fail('candidate labels/order invalid')
        if roles!=Counter({'correct':1,'wrong_count':1,'wrong_positions':1,'wrong_symmetry':1}):fail(f'candidate role counts invalid: {dict(roles)}')
        if row.get('dataset_version')!='fold-punch-2.0.0':fail('dataset version mismatch')
        if len(labels)!=1 or row.get('correct_answer_choice')!=(labels[0] if labels else None):fail(f'correct answer mismatch: matching candidates={labels}')
        answers[row.get('correct_answer_choice')]+=1
        questions=row.get('questions',[])
        if len(questions)!=5 or [q.get('difficulty_level') for q in questions]!=[1,2,3,4,5]:fail('questions must be exactly levels 1-5')
        for q in questions:
            templates[(q.get('difficulty_level'),q.get('question_type'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} cannot be checked: {exc}");continue
            if str(q.get('ground_truth')).lower()!=str(expected).lower():fail(f"{q.get('question_id')} ground truth mismatch")
        image=root/row.get('image_path','')
        if not image.is_file():fail('image missing')
        else:
            issue=verify_png(row,image)
            if issue:fail(issue)
    if len(rows)>=4:
        if max(answers.get(x,0) for x in LETTERS)-min(answers.get(x,0) for x in LETTERS)>1:errors.append(f'dataset: answer distribution uneven {dict(answers)}')
        if abs(fold_counts[2]-fold_counts[3])>1:errors.append(f'dataset: fold count split uneven {dict(fold_counts)}')
    lines=[f'Total images checked: {len(rows)}',f'Total mismatches found: {len(errors)}',f'Correct answer distribution: {dict(sorted(answers.items()))}',f'Fold-count distribution: {dict(sorted(fold_counts.items()))}','Question template counts:']
    lines.extend(f'  Level {level} / {kind}: {count}' for (level,kind),count in sorted(templates.items()));lines+=['','Mismatches:'];lines.extend(errors or ['  None']);lines+=['',f"Summary: {'PASS' if not errors else 'FAIL'}"]
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines[:4]));print(lines[-1]);return not errors
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');p.add_argument('--report',default='validation_report.txt');a=p.parse_args();root=Path(a.dataset_dir);report=Path(a.report);report=report if report.is_absolute() else root/report;raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
