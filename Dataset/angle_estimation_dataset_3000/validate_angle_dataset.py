"""Independent analytic, question, distribution, and rendered-PNG validation."""
import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image

RAY=(83,190,205);ARC=(242,174,75);SCENES=('single','comparison','triangle')
def angle(v,p1,p2):
    a=(p1[0]-v[0],p1[1]-v[1]);b=(p2[0]-v[0],p2[1]-v[1]);return math.degrees(math.acos(max(-1,min(1,(a[0]*b[0]+a[1]*b[1])/(math.hypot(*a)*math.hypot(*b))))))
def marked(v,p1,p2,reflex):
    m=angle(v,p1,p2);return 360-m if reflex else m
def triangle_angles(vertices):return [angle(vertices[0],vertices[1],vertices[2]),angle(vertices[1],vertices[0],vertices[2]),angle(vertices[2],vertices[0],vertices[1])]
def nearest(x,step):return int(math.floor(x/step+.5)*step)
def class90(x):return 'right' if abs(x-90)<=2 else 'acute' if x<90 else 'obtuse'
def color_near(im,p,target,radius=3):
    x,y=p
    for yy in range(max(0,round(y)-radius),min(im.height,round(y)+radius+1)):
        for xx in range(max(0,round(x)-radius),min(im.width,round(x)+radius+1)):
            q=im.getpixel((xx,yy))
            if sum((q[i]-target[i])**2 for i in range(3))<85**2:return True
    return False
def line_samples(a,b):return [(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t) for t in (.15,.35,.55,.75,.92)]
def arc_samples(v,p1,sweep,radius):
    theta=math.atan2(p1[1]-v[1],p1[0]-v[0]);return [(v[0]+radius*math.cos(theta+math.radians(sweep)*t),v[1]+radius*math.sin(theta+math.radians(sweep)*t)) for t in (.15,.35,.55,.75,.9)]
def verify_angle_png(im,v,p1,p2,sweep):
    if sum(color_near(im,p,RAY) for p in line_samples(v,p1))<3 or sum(color_near(im,p,RAY) for p in line_samples(v,p2))<3:return 'ray segment missing'
    radius=min(math.dist(v,p1),math.dist(v,p2))*.23
    if sum(color_near(im,p,ARC,4) for p in arc_samples(v,p1,sweep,radius))<4:return 'marked arc/sweep mismatch'
    return None
def expected_question(q,row):
    t=q['question_type'];scene=row['scene_type']
    if scene=='single':
        a=row['angle_degrees'];values={'single_angle_class':class90(a),'single_angle_nearest_15':str(nearest(a,15)),'single_vs_right':'approximately equal to' if abs(a-90)<=5 else 'less than' if a<90 else 'greater than','distance_from_straight_angle':str(round(abs(a-180))),'single_doubled':'less than 180' if a*2<180 else 'exceeds 180'}
    elif scene=='comparison':
        a,b=row['angle_1_degrees'],row['angle_2_degrees'];s=a+b;small,large=sorted((a,b));values={'shown_angle_count':'2','larger_angle':'Angle 1' if a>b else 'Angle 2','angle_difference_nearest_10':str(nearest(abs(a-b),10)),'angle_sum_bucket':'right' if abs(s-90)<=15 else 'straight' if abs(s-180)<=15 else 'neither','double_smaller_angle_compare':'larger' if 2*small>large else 'equal to' if abs(2*small-large)<1e-9 else 'smaller'}
    else:values={'triangle_vertex_count':'3','triangle_class':row['triangle_class'],'largest_triangle_angle':row['largest_angle_vertex'],'triangle_angle_sum':'180','increase_triangle_angle_validity':'190,no'}
    return values[t]
def validate(root,report):
    root=Path(root);rows=[];errors=[]
    for n,line in enumerate((root/'annotations.jsonl').open(encoding='utf8'),1):
        try:rows.append(json.loads(line))
        except Exception as exc:errors.append(f'line {n}: invalid JSON: {exc}')
    scenes=Counter();classes=Counter();templates=Counter()
    for row in rows:
        iid=row.get('id','unknown');scene=row.get('scene_type');scenes[scene]+=1
        def fail(msg):errors.append(f'{iid}: {msg}')
        path=root/row.get('image_path','')
        if not path.is_file():fail('image missing');continue
        im=Image.open(path).convert('RGB')
        if list(im.size)!=row['canvas_size']:fail('canvas size mismatch')
        if scene=='single':
            v=tuple(row['vertex']);p1,p2=map(tuple,row['ray_endpoints']);actual=marked(v,p1,p2,row['marked_sweep']=='reflex')
            if abs(actual-row['angle_degrees'])>1e-5 or abs(actual-row['arc_sweep_degrees'])>1e-5:fail('single angle geometry mismatch')
            issue=verify_angle_png(im,v,p1,p2,row['arc_sweep_degrees'])
            if issue:fail(issue)
        elif scene=='comparison':
            computed=[]
            for j,a in enumerate(row['angles']):
                v=tuple(a['vertex']);p1,p2=map(tuple,a['ray_endpoints']);actual=angle(v,p1,p2);computed.append(actual)
                if abs(actual-a['angle_degrees'])>1e-5:fail(f'comparison angle {j+1} geometry mismatch')
                issue=verify_angle_png(im,v,p1,p2,a['arc_sweep_degrees'])
                if issue:fail(f'angle {j+1}: {issue}')
            if abs(computed[0]-row['angle_1_degrees'])>1e-5 or abs(computed[1]-row['angle_2_degrees'])>1e-5 or abs(computed[0]-computed[1])<5:fail('comparison metadata/separation mismatch')
        elif scene=='triangle':
            vertices=list(map(tuple,row['triangle_vertices']));computed=triangle_angles(vertices);classes[row['triangle_class']]+=1
            if max(abs(a-b) for a,b in zip(computed,row['interior_angles_degrees']))>1e-5:fail('triangle angle geometry mismatch')
            if abs(sum(computed)-180)>1e-7:fail('triangle angles do not sum to 180')
            klass='right' if any(abs(x-90)<=2 for x in computed) else 'acute' if max(computed)<90 else 'obtuse'
            if klass!=row['triangle_class']:fail('triangle class mismatch')
            labels='ABC'
            if labels[max(range(3),key=lambda i:computed[i])]!=row['largest_angle_vertex'] or labels[min(range(3),key=lambda i:computed[i])]!=row['smallest_angle_vertex']:fail('largest/smallest vertex mismatch')
            for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                if sum(color_near(im,p,RAY) for p in line_samples(a,b))<3:fail('rendered triangle edge missing');break
        else:fail('invalid scene_type')
        qs=row.get('questions',[])
        if len(qs)!=5 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4,5]:fail('question structure mismatch')
        for q in qs:
            templates[(q.get('difficulty_level'),q.get('question_type'))]+=1
            try:expected=expected_question(q,row)
            except Exception as exc:fail(f"{q.get('question_id')} cannot be checked: {exc}");continue
            if str(q.get('ground_truth'))!=expected:fail(f"{q.get('question_id')} answer mismatch")
    if len(rows)==3000:
        expected={'single':1200,'comparison':1050,'triangle':750}
        if dict(scenes)!=expected:errors.append(f'dataset: scene distribution mismatch {dict(scenes)}')
        if classes!=Counter({'acute':250,'right':250,'obtuse':250}):errors.append(f'dataset: triangle class distribution mismatch {dict(classes)}')
    lines=[f'Total images checked: {len(rows)}',f'Total mismatches found: {len(errors)}',f'Scene distribution: {dict(sorted(scenes.items()))}',f'Triangle-class distribution: {dict(sorted(classes.items()))}','Question template counts:']
    lines.extend(f'  Level {l} / {t}: {n}' for (l,t),n in sorted(templates.items()));lines+=['','Mismatches:'];lines.extend(errors or ['  None']);lines+=['',f"Summary: {'PASS' if not errors else 'FAIL'}"]
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines[:4]));print(lines[-1]);return not errors
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');p.add_argument('--report',default='validation_report.txt');a=p.parse_args();root=Path(a.dataset_dir);report=Path(a.report);report=report if report.is_absolute() else root/report;raise SystemExit(0 if validate(root,report) else 1)
if __name__=='__main__':main()
