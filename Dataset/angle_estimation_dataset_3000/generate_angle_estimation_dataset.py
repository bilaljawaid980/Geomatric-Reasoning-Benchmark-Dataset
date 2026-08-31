"""Generate deterministic plane-geometry angle-estimation images."""
import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);RAY=(83,190,205);ARC=(242,174,75);INK=(226,230,230);POINT=(239,118,129);AA=3
ANGLE_SUM_TOLERANCE=15;ANGLE_SUM_BOUNDARY_MARGIN=2
DATASET_VERSION='angle-estimation-3.0.0';COMPARISON_REJECTIONS=0

def compute_angle(vertex,p1,p2):
    a=(p1[0]-vertex[0],p1[1]-vertex[1]);b=(p2[0]-vertex[0],p2[1]-vertex[1]);dot=a[0]*b[0]+a[1]*b[1];den=math.hypot(*a)*math.hypot(*b);return math.degrees(math.acos(max(-1,min(1,dot/den))))
def marked_angle(vertex,p1,p2,reflex):
    minor=compute_angle(vertex,p1,p2);return 360-minor if reflex else minor
def triangle_angles(vertices):
    a,b,c=vertices;return [compute_angle(a,b,c),compute_angle(b,a,c),compute_angle(c,a,b)]
def nearest(value,step):return int(math.floor(value/step+.5)*step)
def class90(value,tol=2):return 'right' if abs(value-90)<=tol else 'acute' if value<90 else 'obtuse'
def font(size,bold=False):
    p=Path('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf');return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()
def line(draw,points,fill,width=1.2):draw.line([(round(x*AA),round(y*AA)) for x,y in points],fill=fill,width=max(2,round(width*AA)),joint='curve')
def draw_arc(draw,vertex,start,sweep,radius):
    theta=math.atan2(start[1]-vertex[1],start[0]-vertex[0]);points=[];steps=max(18,round(abs(sweep)/4))
    for i in range(steps+1):
        a=theta+math.radians(sweep)*i/steps;points.append((vertex[0]+radius*math.cos(a),vertex[1]+radius*math.sin(a)))
    line(draw,points,ARC,1.35)
def draw_angle(draw,vertex,p1,p2,sweep,label=None):
    line(draw,[vertex,p1],RAY,1.25);line(draw,[vertex,p2],RAY,1.25);r=min(math.dist(vertex,p1),math.dist(vertex,p2))*.23;draw_arc(draw,vertex,p1,sweep,r);x,y=vertex;rr=3;draw.ellipse(((x-rr)*AA,(y-rr)*AA,(x+rr)*AA,(y+rr)*AA),fill=POINT)
    if label:draw.text(((x+8)*AA,(y+8)*AA),label,font=font(10*AA,True),fill=INK)

def angle_geometry(center,measure,length1,length2,start_deg):
    theta=math.radians(start_deg);p1=(center[0]+length1*math.cos(theta),center[1]+length1*math.sin(theta));theta2=theta+math.radians(measure);p2=(center[0]+length2*math.cos(theta2),center[1]+length2*math.sin(theta2));p1=tuple(round(v,4) for v in p1);p2=tuple(round(v,4) for v in p2);actual=marked_angle(center,p1,p2,measure>180);return p1,p2,actual
def safe_start(center,measure,lengths,box,rng):
    for _ in range(1000):
        start=rng.uniform(0,360);p1,p2,actual=angle_geometry(center,measure,*lengths,start);x0,y0,x1,y1=box
        if all(x0<=p[0]<=x1 and y0<=p[1]<=y1 for p in (p1,p2)):return start,p1,p2,actual
    raise RuntimeError('unable to place angle')
def choose_single_measure(i,rng):
    if i%5==0:return float(rng.choice((30,45,60,90,120,180)))
    while True:
        value=rng.uniform(10,350)
        if min(abs(value-k*90) for k in range(5))>6:return value
def single_scene(i,rng,size):
    w,h=size;v=(w/2,h/2+12);m=choose_single_measure(i,rng);lengths=(rng.uniform(125,175),rng.uniform(105,165));start,p1,p2,actual=safe_start(v,m,lengths,(24,35,w-24,h-24),rng)
    return {'angle_degrees':round(actual,6),'vertex':[round(x,4) for x in v],'ray_endpoints':[list(p1),list(p2)],'marked_sweep':'reflex' if actual>180 else 'minor','arc_sweep_degrees':round(actual,6)}
def angle_sum_bucket(total):return 'right' if abs(total-90)<=ANGLE_SUM_TOLERANCE else 'straight' if abs(total-180)<=ANGLE_SUM_TOLERANCE else 'neither'
def comparison_scene(i,rng,size):
    global COMPARISON_REJECTIONS
    w,h=size;occurrence=((i-1)//20)*7+((i-1)%20-8);target=('right','straight','neither')[occurrence%3]
    while True:
        measures=[rng.uniform(10,170),rng.uniform(10,170)];total=sum(measures);distances=(abs(total-90),abs(total-180))
        if abs(measures[0]-measures[1])>=8 and all(abs(d-ANGLE_SUM_TOLERANCE)>=ANGLE_SUM_BOUNDARY_MARGIN for d in distances) and angle_sum_bucket(total)==target:break
        COMPARISON_REJECTIONS+=1
    data=[]
    for j,(cx,m) in enumerate(((w*.27,measures[0]),(w*.73,measures[1]))):
        v=(cx,h*.57);lengths=(rng.uniform(75,115),rng.uniform(105,145));start,p1,p2,actual=safe_start(v,m,lengths,(12+j*w/2,55,(j+1)*w/2-12,h-28),rng);data.append({'vertex':[round(x,4) for x in v],'ray_endpoints':[list(p1),list(p2)],'angle_degrees':round(actual,6),'arc_sweep_degrees':round(actual,6)})
    return {'angles':data,'angle_1_degrees':data[0]['angle_degrees'],'angle_2_degrees':data[1]['angle_degrees'],'larger_angle':'Angle 1' if data[0]['angle_degrees']>data[1]['angle_degrees'] else 'Angle 2'}
def raw_triangle(target,rng):
    for _ in range(5000):
        a=(0.0,0.0);b=(rng.uniform(1.4,2.4),0.0)
        if target=='right':alpha=90+rng.uniform(-1.1,1.1)
        elif target=='acute':alpha=rng.uniform(42,75)
        else:alpha=rng.uniform(98,140)
        length=rng.uniform(1.0,2.2);c=(length*math.cos(math.radians(alpha)),-length*math.sin(math.radians(alpha)));angles=triangle_angles((a,b,c));klass='right' if any(abs(x-90)<=2 for x in angles) else 'acute' if max(angles)<90 else 'obtuse'
        if klass==target and min(angles)>5 and max(angles)<170:return (a,b,c)
    raise RuntimeError('triangle generation failed')
def triangle_scene(target,rng,size):
    raw=raw_triangle(target,rng);xs=[p[0] for p in raw];ys=[p[1] for p in raw];w,h=size;scale=min((w-110)/(max(xs)-min(xs)),(h-100)/(max(ys)-min(ys)));cx=w/2;cy=h/2+15;verts=[]
    for x,y in raw:verts.append((round(cx+(x-(min(xs)+max(xs))/2)*scale,4),round(cy+(y-(min(ys)+max(ys))/2)*scale,4)))
    angles=triangle_angles(verts);labels='ABC';largest=labels[max(range(3),key=lambda j:angles[j])];smallest=labels[min(range(3),key=lambda j:angles[j])]
    return {'triangle_vertices':[list(p) for p in verts],'interior_angles_degrees':[round(x,6) for x in angles],'triangle_class':target,'largest_angle_vertex':largest,'smallest_angle_vertex':smallest}

def render(path,size,scene_type,data):
    w,h=size;im=Image.new('RGB',(w*AA,h*AA),BG);d=ImageDraw.Draw(im);d.text((15*AA,12*AA),{'single':'Marked angle','comparison':'Compare the marked angles','triangle':'Triangle angles'}[scene_type],font=font(14*AA,True),fill=INK)
    if scene_type=='single':
        v=tuple(data['vertex']);p1,p2=map(tuple,data['ray_endpoints']);draw_angle(d,v,p1,p2,data['arc_sweep_degrees'],'V')
    elif scene_type=='comparison':
        for j,a in enumerate(data['angles']):
            v=tuple(a['vertex']);p1,p2=map(tuple,a['ray_endpoints']);draw_angle(d,v,p1,p2,a['arc_sweep_degrees']);d.text(((v[0]-32)*AA,43*AA),f'Angle {j+1}',font=font(12*AA,True),fill=INK)
        line(d,[(w/2,52),(w/2,h-20)],(72,76,77),.6)
    else:
        vertices=list(map(tuple,data['triangle_vertices']));line(d,vertices+[vertices[0]],RAY,1.35)
        for j,v in enumerate(vertices):
            rr=3;d.ellipse(((v[0]-rr)*AA,(v[1]-rr)*AA,(v[0]+rr)*AA,(v[1]+rr)*AA),fill=POINT);d.text(((v[0]+7)*AA,(v[1]-17)*AA),'ABC'[j],font=font(11*AA,True),fill=INK)
            prev=vertices[(j-1)%3];nxt=vertices[(j+1)%3];a1=math.atan2(prev[1]-v[1],prev[0]-v[0]);a2=math.atan2(nxt[1]-v[1],nxt[0]-v[0]);sweep=(math.degrees(a2-a1))%360
            if sweep>180:sweep-=360
            draw_arc(d,v,prev,sweep,22)
    im.resize(size,Image.Resampling.LANCZOS).save(path,'PNG')

def questions(iid,scene,row):
    if scene=='single':
        a=row['angle_degrees'];texts=("Is the marked angle acute (less than 90°), right (exactly 90°), or obtuse (greater than 90°)? Answer with one word.","Estimate the measure of the marked angle, rounded to the nearest 15 degrees. Answer with a number in curly brackets, e.g. {45}.","Is the marked angle greater than, less than, or approximately equal to a right angle (90 degrees)?","How many degrees is the shown angle away from a straight angle, rounded to the nearest degree?","If this angle were doubled, would the result still be less than a straight angle (180 degrees), or would it exceed a straight angle?");types=('single_angle_class','single_angle_nearest_15','single_vs_right','distance_from_straight_angle','single_doubled');gts=(class90(a),str(nearest(a,15)),'approximately equal to' if abs(a-90)<=5 else 'less than' if a<90 else 'greater than',str(round(abs(a-180))),'less than 180' if a*2<180 else 'exceeds 180');fmts=('one_word',{'type':'numeric_tolerance','absolute_tolerance':5,'answer_key_side_only':True},'choice','numeric','choice')
    elif scene=='comparison':
        a,b=row['angle_1_degrees'],row['angle_2_degrees'];small,large=sorted((a,b));texts=("How many separate angles are shown in this image?","Which angle is larger, Angle 1 or Angle 2? Answer with the label.","Approximately how many degrees larger is the bigger angle compared to the smaller one, rounded to the nearest 10 degrees?","If Angle 1 and Angle 2 were added together, answer 'right angle' if the sum is within 15 degrees of 90°, 'straight angle' if it is within 15 degrees of 180°, otherwise answer 'neither'.","If the smaller shown angle were doubled, would it be larger than, equal to, or smaller than the other angle?");types=('shown_angle_count','larger_angle','angle_difference_nearest_10','angle_sum_bucket','double_smaller_angle_compare');gts=('2',row['larger_angle'],str(nearest(abs(a-b),10)),angle_sum_bucket(a+b),'larger' if 2*small>large else 'equal to' if abs(2*small-large)<1e-9 else 'smaller');fmts=('numeric','label',{'type':'numeric_tolerance','absolute_tolerance':5,'answer_key_side_only':True},'choice','choice')
    else:
        texts=("How many vertices does the triangle have?","Is this triangle acute, right, or obtuse? Answer with one word.","Which vertex of the triangle has the largest interior angle? Answer with the vertex label.","The three interior angles of any triangle have what fixed total? Answer with a number in curly brackets.","If the smallest interior angle increased by 10 degrees while the other two stayed fixed, what would the new angle sum be, and would it still form a Euclidean triangle? Answer as sum,yes/no.");types=('triangle_vertex_count','triangle_class','largest_triangle_angle','triangle_angle_sum','increase_triangle_angle_validity');gts=('3',row['triangle_class'],row['largest_angle_vertex'],'180','190,no');fmts=('numeric','one_word','label','numeric','numeric')
    return [{'question_id':iid+f'_q{k+1}','question_text':texts[k],'question_type':types[k],'ground_truth':gts[k],'answer_format':fmts[k],'difficulty_level':k+1} for k in range(5)]
def scene_for(i):
    slot=(i-1)%20;return 'single' if slot<8 else 'comparison' if slot<15 else 'triangle'
def generate_one(i,images):
    rng=random.Random(i);size=(rng.randint(450,500),rng.randint(450,500));scene=scene_for(i)
    if scene=='single':data=single_scene(i,rng,size)
    elif scene=='comparison':data=comparison_scene(i,rng,size)
    else:data=triangle_scene(('acute','right','obtuse')[((i-1)//20)%3],rng,size)
    iid=f'angle_estimation_{i:04d}';render(images/f'{iid}.png',size,scene,data);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':list(size),'scene_type':scene,**data,'seed':i,'difficulty_score':round({'single':.44,'comparison':.55,'triangle':.62}[scene]+(.12 if scene=='single' and data['angle_degrees']>180 else 0),4),'dataset_version':DATASET_VERSION};row['questions']=questions(iid,scene,row);return row
def generate_dataset(n,output_dir,sample=False):
    global COMPARISON_REJECTIONS
    COMPARISON_REJECTIONS=0;root=Path(output_dir);images=root/'images';images.mkdir(parents=True,exist_ok=True);indices=(1,5,9,16,56) if sample else range(1,n+1);count=len(indices) if sample else n
    with (root/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for progress,i in enumerate(indices,1):
            f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
            if progress%250==0 or progress==count:print(f'Generated {progress}/{count}',flush=True)
    (root/'generation_stats.json').write_text(json.dumps({'angle_sum_threshold_degrees':ANGLE_SUM_TOLERANCE,'angle_sum_boundary_margin_degrees':ANGLE_SUM_BOUNDARY_MARGIN,'comparison_generation_rejections':COMPARISON_REJECTIONS},indent=2)+'\n',encoding='utf8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='.');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
