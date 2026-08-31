"""Independent analytic, question, distribution, and PNG validation."""
import argparse,json,math
from collections import Counter
from itertools import combinations
from pathlib import Path
from PIL import Image

LABELS='ABCD';POINT=(239,118,129);AXIS=(181,189,192)
def dist(a,b):return math.hypot(b[0]-a[0],b[1]-a[1])
def mid(a,b):return ((a[0]+b[0])/2,(a[1]+b[1])/2)
def coll(a,b,c):return (b[1]-a[1])*(c[0]-a[0])==(c[1]-a[1])*(b[0]-a[0])
def key(a,b):return f'{a}-{b}'
def fmt_num(x):return str(int(x)) if float(x).is_integer() else f'{x:.1f}'
def fmt_point(p):return f'({fmt_num(p[0])}, {fmt_num(p[1])})'
def plot_box(size):
    w,h=size;side=min(w-92,h-96);return ((w-side)/2,42,(w+side)/2,42+side)
def pixel(p,box):
    x,y=p;x0,y0,x1,y1=box;return (x0+(x+10)*(x1-x0)/20,y1-(y+10)*(y1-y0)/20)
def near_color(im,p,color,radius=4,tol=75):
    x,y=p
    for yy in range(max(0,round(y)-radius),min(im.height,round(y)+radius+1)):
        for xx in range(max(0,round(x)-radius),min(im.width,round(x)+radius+1)):
            q=im.getpixel((xx,yy))
            if sum((q[i]-color[i])**2 for i in range(3))<tol**2:return True
    return False
def expected_question(q,row):
    points=row['points'];t=q['question_type']
    if t=='point_coordinates':return fmt_point(points[q['point_label']])
    if t=='pair_distance':return f"{row['all_pairwise_distances'][q['point_pair']]:.2f}"
    if t=='pair_midpoint':return fmt_point(row['all_pairwise_midpoints'][q['point_pair']])
    if t in ('farthest_pair','closest_pair'):
        fn=max if t=='farthest_pair' else min;p=fn(row['all_pairwise_distances'],key=row['all_pairwise_distances'].get);return f'{p[0]} and {p[2]}'
    if t=='triple_collinearity':return 'yes' if coll(*(points[x] for x in q['point_triple'])) else 'no'
    if t=='distance_vs_10':
        d=row['all_pairwise_distances'][q['point_pair']];return 'greater than' if d>10 else 'less than' if d<10 else 'equal to'
    if t=='sum_x_coordinates':return str(sum(p[0] for p in points.values()))
    raise ValueError('unknown question type '+t)
def validate(root,report):
    root=Path(root);rows=[];errors=[]
    for n,line in enumerate((root/'annotations.jsonl').open(encoding='utf8'),1):
        try:rows.append(json.loads(line))
        except Exception as exc:errors.append(f'line {n}: invalid JSON: {exc}')
    counts=Counter();col_counts=Counter();templates=Counter()
    for row in rows:
        iid=row.get('id','unknown');points=row.get('points',{});labels=list(points);counts[len(points)]+=1
        def fail(msg):errors.append(f'{iid}: {msg}')
        if labels!=list(LABELS[:len(labels)]) or row.get('num_points')!=len(points) or len(points) not in (2,3,4):fail('point labels/count invalid')
        if any(not isinstance(v,int) or not -8<=v<=8 for p in points.values() for v in p):fail('coordinate is non-integer or outside visible range')
        triples=[''.join(t) for t in combinations(labels,3) if coll(*(points[x] for x in t))];is_col=bool(triples);col_counts[is_col]+=1
        if is_col!=row.get('is_collinear_triple') or row.get('collinear_labels')!=(list(triples[0]) if triples else []):fail('collinearity metadata mismatch')
        if len(triples)>1:fail('multiple collinear triples create ambiguity')
        expected_d={};expected_m={};sq=[]
        for a,b in combinations(labels,2):
            k=key(a,b);expected_d[k]=float(f'{dist(points[a],points[b]):.2f}');expected_m[k]=list(mid(points[a],points[b]));sq.append((points[a][0]-points[b][0])**2+(points[a][1]-points[b][1])**2)
        if expected_d!=row.get('all_pairwise_distances') or expected_m!=row.get('all_pairwise_midpoints'):fail('distance/midpoint metadata mismatch')
        if len(sq)!=len(set(sq)):fail('closest/farthest distance tie')
        image=root/row.get('image_path','')
        if not image.is_file():fail('image missing')
        else:
            im=Image.open(image).convert('RGB')
            if list(im.size)!=row['canvas_size']:fail('canvas size mismatch')
            box=plot_box(im.size)
            for label,p in points.items():
                if not near_color(im,pixel(p,box),POINT):fail(f'point {label} missing from stored grid intersection')
            origin=pixel((0,0),box)
            if not near_color(im,origin,AXIS,2,85):fail('coordinate axes/origin missing')
        qs=row.get('questions',[])
        if len(qs)!=4 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4]:fail('questions must be exactly levels 1-4')
        for q in qs:
            templates[(q.get('difficulty_level'),q.get('question_type'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} cannot be checked: {exc}");continue
            if str(q.get('ground_truth'))!=expected:fail(f"{q.get('question_id')} answer mismatch")
    if len(rows)==3000:
        if counts!=Counter({2:1000,3:1000,4:1000}):errors.append(f'dataset: point-count distribution mismatch {dict(counts)}')
        if col_counts!=Counter({False:2100,True:900}):errors.append(f'dataset: collinearity distribution mismatch {dict(col_counts)}')
    lines=[f'Total images checked: {len(rows)}',f'Total mismatches found: {len(errors)}',f'Point-count distribution: {dict(sorted(counts.items()))}',f'Collinearity distribution: {dict(sorted(col_counts.items()))}','Question template counts:']
    lines.extend(f'  Level {level} / {kind}: {count}' for (level,kind),count in sorted(templates.items()));lines+=['','Mismatches:'];lines.extend(errors or ['  None']);lines+=['',f"Summary: {'PASS' if not errors else 'FAIL'}"]
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines[:4]));print(lines[-1]);return not errors
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');p.add_argument('--report',default='validation_report.txt');a=p.parse_args();root=Path(a.dataset_dir);report=Path(a.report);report=report if report.is_absolute() else root/report;raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
