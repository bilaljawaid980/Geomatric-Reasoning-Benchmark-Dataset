"""Independent formula, geometry, question, balance, and PNG validation."""
import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image
import numpy as np

PATTERNS=('grid','circle','triangle');SHAPES=('dot','square','triangle');STYLES=('seamless','visible_box');BG=(26,26,26)
def inside(p,b):x,y=p;x0,y0,x1,y1=b;return x0<=x<=x1 and y0<=y<=y1
def expected_total(kind,params):
    if kind=='grid':return params['rows']*params['cols']
    if kind=='circle':return params['n_objects']
    if kind=='triangle':return params['k']*(params['k']+1)//2
    raise ValueError('invalid pattern_type')
def reconstruct(row):
    w,h=row['canvas_size'];x0,y0,x1,y1=(72,68,w-72,h-68);kind=row['pattern_type'];p=row['pattern_params'];points=[]
    if kind=='grid':
        for r in range(p['rows']):
            y=y0+r*(y1-y0)/(p['rows']-1)
            for c in range(p['cols']):points.append((round(x0+c*(x1-x0)/(p['cols']-1),3),round(y,3)))
    elif kind=='circle':
        cx=(x0+x1)/2;cy=(y0+y1)/2;radius=min(x1-x0,y1-y0)/2
        for i in range(p['n_objects']):points.append((round(cx+radius*math.cos(-math.pi/2+2*math.pi*i/p['n_objects']),3),round(cy+radius*math.sin(-math.pi/2+2*math.pi*i/p['n_objects']),3)))
    else:
        k=p['k'];cx=(x0+x1)/2
        for r in range(k):
            y=y0+r*(y1-y0)/(k-1);span=(x1-x0)*r/(k-1);left=cx-span/2
            for c in range(r+1):points.append((round(cx if r==0 else left+c*span/r,3),round(y,3)))
    return points
def color_components(im,color):
    array=np.asarray(im,dtype=np.int32);target=np.asarray(color,dtype=np.int32);binary=np.sum((array-target)**2,axis=2)<55**2
    ys,xs=np.nonzero(binary);mask={(int(x),int(y)) for y,x in zip(ys,xs)};count=0
    while mask:
        start=mask.pop();todo=[start];area=1
        while todo:
            x,y=todo.pop()
            for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if q in mask:mask.remove(q);todo.append(q);area+=1
        if area>=18:count+=1
    return count
def close_color(a,b,tolerance=65):return sum((a[i]-b[i])**2 for i in range(3))<=tolerance**2
def verify_png(row,path):
    im=Image.open(path).convert('RGB')
    if list(im.size)!=row['canvas_size']:return 'canvas size mismatch'
    color=row['object_color'];visible=0
    for obj in row['object_positions']:
        pixel=im.getpixel((round(obj['x']),round(obj['y'])));has_color=close_color(pixel,color)
        if obj['occluded'] and has_color:return 'occluded object remains visible at its center'
        if not obj['occluded']:
            visible+=1
            if not has_color:return 'visible object missing at its center'
    if color_components(im,color)!=visible:return 'rendered visible-object component count mismatch'
    x0,y0,x1,y1=row['occluder_bounds'];sample=im.getpixel((round((x0+x1)/2),round((y0+y1)/2)))
    if row['occluder_style']=='seamless' and not close_color(sample,BG,8):return 'seamless occluder does not match background'
    if row['occluder_style']=='visible_box' and close_color(sample,BG,12):return 'visible occluder box is not visibly distinct'
    return None
def expected_question(q,row):
    return {'visible_object_count':str(row['visible_object_count']),'total_object_count':str(row['total_object_count']),'pattern_type':row['pattern_type'],'occluded_object_count':str(row['occluded_object_count'])}[q['question_type']]
def validate(root,report):
    root=Path(root);errors=[];rows=[]
    for number,line in enumerate((root/'annotations.jsonl').open(encoding='utf8'),1):
        try:rows.append(json.loads(line))
        except Exception as exc:errors.append(f'line {number}: invalid JSON: {exc}')
    pattern_counts=Counter();shape_counts=Counter();style_counts=Counter();templates=Counter()
    for row in rows:
        iid=row.get('id','unknown')
        def fail(message):errors.append(f'{iid}: {message}')
        kind=row.get('pattern_type');pattern_counts[kind]+=1;shape_counts[row.get('shape_type')]+=1;style_counts[row.get('occluder_style')]+=1
        try:formula_total=expected_total(kind,row['pattern_params'])
        except Exception as exc:fail(f'pattern formula failed: {exc}');continue
        stored_points=[(o['x'],o['y']) for o in row.get('object_positions',[])]
        if stored_points!=reconstruct(row):fail('object positions do not match pattern parameters')
        flags=[inside(p,row['occluder_bounds']) for p in stored_points];hidden=sum(flags);visible=len(flags)-hidden
        if formula_total!=len(stored_points) or row.get('total_object_count')!=formula_total:fail('total_object_count mismatch')
        if row.get('visible_object_count')!=visible or row.get('occluded_object_count')!=hidden:fail('visible/occluded count mismatch')
        if [o.get('occluded') for o in row.get('object_positions',[])]!=flags:fail('per-object occluded flags mismatch')
        if hidden==0 or visible==0 or visible/formula_total<.40 or not .15<=hidden/formula_total<=.60:fail('occlusion fraction outside constraints')
        if hidden<2:fail('occluder hides fewer than two objects')
        if kind=='grid':
            rows_n=row['pattern_params']['rows'];cols_n=row['pattern_params']['cols'];hidden_indices=[i for i,f in enumerate(flags) if f];hrs={i//cols_n for i in hidden_indices};hcs={i%cols_n for i in hidden_indices}
            if len(hidden_indices)!=len(hrs)*len(hcs):fail('grid occlusion is not a rectangular cell block')
            if len(hrs)==rows_n or len(hcs)==cols_n:fail('grid occluder removes all evidence along an axis')
        else:
            points=[p for p,f in zip(stored_points,flags) if not f];w,h=row['canvas_size']
            if max(x for x,y in points)-min(x for x,y in points)<.35*(w-144) or max(y for x,y in points)-min(y for x,y in points)<.35*(h-136):fail('remaining pattern evidence has insufficient span')
        if row.get('shape_type') not in SHAPES or row.get('occluder_style') not in STYLES:fail('invalid shape/style')
        questions=row.get('questions',[])
        if len(questions)!=4 or [q.get('difficulty_level') for q in questions]!=[1,2,3,4]:fail('questions must be exactly ordered levels 1-4')
        for q in questions:
            templates[(q.get('difficulty_level'),q.get('question_type'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} cannot be checked: {exc}");continue
            if str(q.get('ground_truth')).lower()!=expected.lower():fail(f"{q.get('question_id')} ground truth mismatch")
        image=root/row.get('image_path','')
        if not image.is_file():fail('image missing')
        else:
            issue=verify_png(row,image)
            if issue:fail(issue)
    for name,counts,keys in (('pattern_type',pattern_counts,PATTERNS),('shape_type',shape_counts,SHAPES),('occluder_style',style_counts,STYLES)):
        if rows and max(counts[k] for k in keys)-min(counts[k] for k in keys)>1:errors.append(f'dataset: uneven {name} distribution {dict(counts)}')
    lines=[f'Total images checked: {len(rows)}',f'Total mismatches found: {len(errors)}',f'Pattern distribution: {dict(sorted(pattern_counts.items()))}',f'Shape distribution: {dict(sorted(shape_counts.items()))}',f'Occluder-style distribution: {dict(sorted(style_counts.items()))}','Question template counts:']
    lines.extend(f'  Level {level} / {kind}: {count}' for (level,kind),count in sorted(templates.items()));lines+=['','Mismatches:'];lines.extend(errors or ['  None']);lines+=['',f"Summary: {'PASS' if not errors else 'FAIL'}"]
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines[:5]));print(lines[-1]);return not errors
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');p.add_argument('--report',default='validation_report.txt');a=p.parse_args();root=Path(a.dataset_dir);report=Path(a.report);report=report if report.is_absolute() else root/report;raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
