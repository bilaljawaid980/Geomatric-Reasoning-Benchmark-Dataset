"""Generate deterministic coordinate-geometry reasoning images."""
import argparse,json,math,random
from itertools import combinations
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);GRID=(58,63,66);AXIS=(181,189,192);POINT=(239,118,129);LABEL=(240,242,242);LABELS='ABCD';LIMIT=10;AA=3
def distance(a,b):return math.hypot(b[0]-a[0],b[1]-a[1])
def midpoint(a,b):return ((a[0]+b[0])/2,(a[1]+b[1])/2)
def collinear(a,b,c):return (b[1]-a[1])*(c[0]-a[0])==(c[1]-a[1])*(b[0]-a[0])
def pair_key(a,b):return f'{a}-{b}'
def fmt_num(x):return str(int(x)) if float(x).is_integer() else f'{x:.1f}'
def fmt_point(p):return f'({fmt_num(p[0])}, {fmt_num(p[1])})'
def valid_points(points,want_collinear):
    if len(set(points))!=len(points) or any(not(-8<=x<=8 and -8<=y<=8) for x,y in points):return False
    sq=[(a[0]-b[0])**2+(a[1]-b[1])**2 for a,b in combinations(points,2)]
    if min(sq,default=9)<5 or len(sq)!=len(set(sq)):return False
    triples=[t for t in combinations(range(len(points)),3) if collinear(*(points[i] for i in t))]
    return len(triples)==1 if want_collinear else not triples
def generate_points(n,want_collinear,rng):
    directions=((1,0),(0,1),(1,1),(1,-1),(2,1),(1,2),(2,-1),(1,-2))
    for _ in range(20000):
        if want_collinear:
            dx,dy=rng.choice(directions);ts=sorted(rng.sample(range(-4,5),3));x0=rng.randint(-2,2);y0=rng.randint(-2,2);points=[(x0+t*dx,y0+t*dy) for t in ts]
            if n==4:points.append((rng.randint(-8,8),rng.randint(-8,8)))
        else:points=[(rng.randint(-8,8),rng.randint(-8,8)) for _ in range(n)]
        if valid_points(points,want_collinear):return points
    raise RuntimeError('could not generate unambiguous points')
def all_geometry(points):
    distances={};midpoints={}
    for i,j in combinations(range(len(points)),2):
        key=pair_key(LABELS[i],LABELS[j]);distances[key]=float(f'{distance(points[i],points[j]):.2f}');midpoints[key]=list(midpoint(points[i],points[j]))
    triples=[ ''.join(LABELS[i] for i in t) for t in combinations(range(len(points)),3) if collinear(*(points[i] for i in t))]
    return distances,midpoints,triples
def font(size,bold=False):
    p=Path('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf');return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()
def plot_box(size):
    w,h=size;side=min(w-92,h-96);return ((w-side)/2,42,(w+side)/2,42+side)
def to_pixel(p,box):
    x,y=p;x0,y0,x1,y1=box;return (x0+(x+10)*(x1-x0)/20,y1-(y+10)*(y1-y0)/20)
def render(path,size,points):
    w,h=size;im=Image.new('RGB',(w*AA,h*AA),BG);d=ImageDraw.Draw(im);box=plot_box(size);x0,y0,x1,y1=box
    for k in range(-10,11):
        px,py=to_pixel((k,k),box);color=AXIS if k==0 else GRID;width=3*AA if k==0 else (2*AA if k%2==0 else AA);d.line((px*AA,y0*AA,px*AA,y1*AA),fill=color,width=width);d.line((x0*AA,py*AA,x1*AA,py*AA),fill=color,width=width)
    small=font(7*AA);origin=to_pixel((0,0),box)
    for k in range(-10,11,2):
        px,_=to_pixel((k,0),box);_,py=to_pixel((0,k),box)
        if k!=0:d.text((px*AA,(origin[1]+4)*AA),str(k),font=small,fill=AXIS,anchor='ma');d.text(((origin[0]-5)*AA,py*AA),str(k),font=small,fill=AXIS,anchor='rm')
    d.text(((x1+9)*AA,origin[1]*AA),'x',font=font(9*AA,True),fill=AXIS,anchor='lm');d.text((origin[0]*AA,(y0-7)*AA),'y',font=font(9*AA,True),fill=AXIS,anchor='ms');d.text((w/2*AA,14*AA),'Coordinate Geometry',font=font(12*AA,True),fill=LABEL,anchor='ma')
    offsets=((8,-14),(8,5),(-15,-14),(-15,5));lf=font(9*AA,True)
    for i,p in enumerate(points):
        px,py=to_pixel(p,box);r=4.5;d.ellipse(((px-r)*AA,(py-r)*AA,(px+r)*AA,(py+r)*AA),fill=POINT,outline=(248,218,221),width=2*AA);dx,dy=offsets[i];tx=px+dx;ty=py+dy
        if p[0]>7:tx=px-15
        if p[1]>7:ty=py+5
        bbox=d.textbbox((tx*AA,ty*AA),LABELS[i],font=lf);d.rounded_rectangle((bbox[0]-2*AA,bbox[1]-AA,bbox[2]+2*AA,bbox[3]+AA),radius=2*AA,fill=BG);d.text((tx*AA,ty*AA),LABELS[i],font=lf,fill=LABEL)
    im.resize(size,Image.Resampling.LANCZOS).save(path,'PNG')
def questions(iid,row,rng):
    labels=list(row['points']);pairs=list(row['all_pairwise_distances']);q_label=rng.choice(labels);pair=rng.choice(pairs)
    qs=[{'question_id':iid+'_q1','question_text':f'What are the coordinates of point {q_label}?','question_type':'point_coordinates','ground_truth':fmt_point(row['points'][q_label]),'answer_format':'coordinate','difficulty_level':1,'point_label':q_label},{'question_id':iid+'_q2','question_text':f"What is the distance between point {pair[0]} and point {pair[2]}, rounded to 2 decimal places?",'question_type':'pair_distance','ground_truth':f"{row['all_pairwise_distances'][pair]:.2f}",'answer_format':'numeric_2dp','difficulty_level':2,'point_pair':pair}]
    kind=rng.choice(('midpoint','farthest','closest'))
    if kind=='midpoint':
        p=rng.choice(pairs);q={'question_text':f"What are the coordinates of the midpoint between point {p[0]} and point {p[2]}?",'question_type':'pair_midpoint','ground_truth':fmt_point(row['all_pairwise_midpoints'][p]),'answer_format':'coordinate','point_pair':p}
    else:
        fn=max if kind=='farthest' else min;p=fn(pairs,key=lambda x:row['all_pairwise_distances'][x]);q={'question_text':f"Which two points are {kind} together? Answer with both labels.",'question_type':kind+'_pair','ground_truth':f'{p[0]} and {p[2]}','answer_format':'label_pair'}
    qs.append({'question_id':iid+'_q3','difficulty_level':3,**q})
    choices=['distance_vs_10','sum_x']+(['triple_collinearity'] if len(labels)>=3 else []);kind=rng.choice(choices)
    if kind=='triple_collinearity':
        triples=[''.join(t) for t in combinations(labels,3)];true=row['collinear_labels']
        if true and (len(triples)==1 or rng.random()<.7):triple=''.join(true)
        else:triple=rng.choice([t for t in triples if list(t)!=true])
        pts=[row['points'][x] for x in triple];gt='yes' if collinear(*pts) else 'no';q={'question_text':f'Are points {triple[0]}, {triple[1]}, and {triple[2]} collinear (do they lie on one straight line)? Answer yes or no.','question_type':'triple_collinearity','ground_truth':gt,'answer_format':'yes_no','point_triple':triple}
    elif kind=='distance_vs_10':
        p=rng.choice(pairs);d=row['all_pairwise_distances'][p];gt='greater than' if d>10 else 'less than' if d<10 else 'equal to';q={'question_text':f"The distance from point {p[0]} to point {p[2]} is {d:.2f} units. Is this greater than, less than, or equal to 10 units?",'question_type':'distance_vs_10','ground_truth':gt,'answer_format':'choice','point_pair':p}
    else:q={'question_text':'What is the sum of the x-coordinates of all points in this image?','question_type':'sum_x_coordinates','ground_truth':str(sum(p[0] for p in row['points'].values())),'answer_format':'integer'}
    qs.append({'question_id':iid+'_q4','difficulty_level':4,**q});return qs
def generate_one(i,images):
    rng=random.Random(i);size=(rng.randint(500,550),rng.randint(500,550));n=2+(i-1)%3;group=(i-1)//3;want=n>2 and group%20<9;coords=generate_points(n,want,rng);points={LABELS[j]:list(p) for j,p in enumerate(coords)};distances,midpoints,triples=all_geometry(coords);iid=f'coordinate_geometry_{i:04d}';render(images/f'{iid}.png',size,coords);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':list(size),'grid_range':[-10,10],'points':points,'num_points':n,'is_collinear_triple':bool(triples),'collinear_labels':list(triples[0]) if triples else [],'all_pairwise_distances':distances,'all_pairwise_midpoints':midpoints,'seed':i,'difficulty_score':round(.3+.12*(n-2)+.2*bool(triples),4)};row['questions']=questions(iid,row,rng);return row
def generate_dataset(n,output_dir,sample=False):
    root=Path(output_dir);images=root/'images';images.mkdir(parents=True,exist_ok=True);indices=(1,2,3,23,24) if sample else range(1,n+1);count=len(indices) if sample else n
    with (root/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for progress,i in enumerate(indices,1):
            f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
            if progress%250==0 or progress==count:print(f'Generated {progress}/{count}',flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='.');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
