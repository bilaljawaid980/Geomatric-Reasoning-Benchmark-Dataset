"""Generate deterministic CAPTURe-style occluded-pattern counting images."""
import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw

BG=(26,26,26);AA=3
PALETTE=((74,190,205),(239,177,82),(190,125,220),(102,201,139),(232,112,126),(118,157,230))
PATTERNS=('grid','circle','triangle');SHAPES=('dot','square','triangle');STYLES=('seamless','visible_box')

def grid_pattern(rows,cols,box):
    x0,y0,x1,y1=box;xs=[x0+i*(x1-x0)/(cols-1) for i in range(cols)];ys=[y0+i*(y1-y0)/(rows-1) for i in range(rows)]
    return [(round(x,3),round(y,3)) for y in ys for x in xs]
def circle_pattern(n,box):
    x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2;r=min(x1-x0,y1-y0)/2
    return [(round(cx+r*math.cos(-math.pi/2+2*math.pi*i/n),3),round(cy+r*math.sin(-math.pi/2+2*math.pi*i/n),3)) for i in range(n)]
def triangle_pattern(k,box):
    x0,y0,x1,y1=box;cx=(x0+x1)/2;points=[]
    for row in range(k):
        y=y0+row*(y1-y0)/(k-1);span=(x1-x0)*row/(k-1);left=cx-span/2
        for col in range(row+1):points.append((round(cx if row==0 else left+col*span/row,3),round(y,3)))
    return points

def inside(p,b):x,y=p;x0,y0,x1,y1=b;return x0<=x<=x1 and y0<=y<=y1
def distance_to_rect(p,b):
    x,y=p;x0,y0,x1,y1=b;dx=max(x0-x,0,x-x1);dy=max(y0-y,0,y-y1);return math.hypot(dx,dy)
def valid_occluder(points,bounds,radius):
    hidden=[p for p in points if inside(p,bounds)];total=len(points)
    if len(hidden)<2 or len(hidden)/total<.15 or len(hidden)/total>.60 or total-len(hidden)<math.ceil(.4*total):return False
    x0,y0,x1,y1=bounds
    for p in points:
        x,y=p
        if inside(p,bounds):
            if min(x-x0,x1-x,y-y0,y1-y)<radius+2:return False
        elif distance_to_rect(p,bounds)<radius+2:return False
    return True

def grid_occluder(points,rows,cols,radius,rng):
    xs=sorted({x for x,y in points});ys=sorted({y for x,y in points});candidates=[]
    for r0 in range(rows):
      for r1 in range(r0,rows):
       for c0 in range(cols):
        for c1 in range(c0,cols):
         if r0==0 and r1==rows-1 or c0==0 and c1==cols-1:continue
         bx0=xs[c0]-(xs[1]-xs[0])*.42;bx1=xs[c1]+(xs[1]-xs[0])*.42;by0=ys[r0]-(ys[1]-ys[0])*.42;by1=ys[r1]+(ys[1]-ys[0])*.42;b=(bx0,by0,bx1,by1)
         if valid_occluder(points,b,radius):candidates.append(b)
    if not candidates:raise RuntimeError('no valid grid occluder')
    return rng.choice(candidates)

def general_occluder(points,pattern_box,radius,rng):
    x0,y0,x1,y1=pattern_box;xs=sorted({p[0] for p in points});ys=sorted({p[1] for p in points});xb=[x0-radius-4]+[(a+b)/2 for a,b in zip(xs,xs[1:])]+[x1+radius+4];yb=[y0-radius-4]+[(a+b)/2 for a,b in zip(ys,ys[1:])]+[y1+radius+4];candidates=[]
    for _ in range(500):
        xa,xbv=sorted(rng.sample(xb,2));ya,ybv=sorted(rng.sample(yb,2));b=(xa,ya,xbv,ybv)
        if valid_occluder(points,b,radius):
            visible=[p for p in points if not inside(p,b)]
            if max(x for x,y in visible)-min(x for x,y in visible)>.45*(x1-x0) and max(y for x,y in visible)-min(y for x,y in visible)>.45*(y1-y0):candidates.append(b)
    if not candidates:raise RuntimeError('no valid occluder')
    return rng.choice(candidates)

def draw_object(draw,point,shape,radius,color):
    x,y=point;x*=AA;y*=AA;r=radius*AA
    if shape=='dot':draw.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=(235,239,239),width=max(2,round(.65*AA)))
    elif shape=='square':draw.rectangle((x-r,y-r,x+r,y+r),fill=color,outline=(235,239,239),width=max(2,round(.65*AA)))
    else:draw.polygon(((x,(y-r)),(x-r*.92,y+r*.78),(x+r*.92,y+r*.78)),fill=color);draw.line(((x,y-r),(x-r*.92,y+r*.78),(x+r*.92,y+r*.78),(x,y-r)),fill=(235,239,239),width=max(2,round(.65*AA)),joint='curve')

def render(path,size,positions,bounds,style,shape,radius,color):
    w,h=size;im=Image.new('RGB',(w*AA,h*AA),BG);draw=ImageDraw.Draw(im)
    for p in positions:draw_object(draw,p,shape,radius,color)
    x0,y0,x1,y1=bounds;rect=tuple(round(v*AA) for v in bounds)
    if style=='seamless':draw.rectangle(rect,fill=BG)
    else:
        draw.rectangle(rect,fill=(47,52,56),outline=(154,164,168),width=2*AA)
        # restrained diagonal hatch makes the occluding surface unmistakable
        step=14*AA
        start=int((x0-y1)*AA)-int((h+w)*AA)
        for offset in range(start,int((x1-y0)*AA)+step,step):
            pts=[]
            for yy in (y0*AA,y1*AA):
                xx=offset+yy
                if x0*AA<=xx<=x1*AA:pts.append((xx,yy))
            for xx in (x0*AA,x1*AA):
                yy=xx-offset
                if y0*AA<=yy<=y1*AA:pts.append((xx,yy))
            if len(pts)>=2:draw.line((pts[0],pts[1]),fill=(65,72,77),width=AA)
    im.resize((w,h),Image.Resampling.LANCZOS).save(path,'PNG')

def questions(iid,row):return [
 {'question_id':iid+'_q1','question_text':'How many objects are clearly visible (not hidden behind the occluder) in this image?','question_type':'visible_object_count','ground_truth':str(row['visible_object_count']),'answer_format':'numeric','difficulty_level':1},
 {'question_id':iid+'_q2','question_text':'Assuming the pattern continues behind the occluded region, how many objects are there in total? Answer with a number in curly brackets, e.g. {12}.','question_type':'total_object_count','ground_truth':str(row['total_object_count']),'answer_format':'numeric','difficulty_level':2},
 {'question_id':iid+'_q3','question_text':'What type of pattern do the objects form - a grid, a circle, or a triangular arrangement? Answer with one word.','question_type':'pattern_type','ground_truth':row['pattern_type'],'answer_format':'one_word','difficulty_level':3},
 {'question_id':iid+'_q4','question_text':'How many objects are hidden behind the occluded region specifically (not counting the visible ones)? Answer with a number in curly brackets.','question_type':'occluded_object_count','ground_truth':str(row['occluded_object_count']),'answer_format':'numeric','difficulty_level':4}]

def generate_one(i,images):
    rng=random.Random(i);size=(rng.randint(450,550),rng.randint(450,550));w,h=size;pattern=PATTERNS[(i-1)%3];shape=SHAPES[((i-1)+(i-1)//3)%3];style=STYLES[(i-1)%2];radius=rng.randint(8,11);box=(72,68,w-72,h-68)
    if pattern=='grid':
        rows=rng.randint(3,6);cols=rng.randint(3,6);positions=grid_pattern(rows,cols,box);params={'rows':rows,'cols':cols};bounds=grid_occluder(positions,rows,cols,radius,rng)
    elif pattern=='circle':
        n=rng.randint(6,14);positions=circle_pattern(n,box);params={'n_objects':n};bounds=general_occluder(positions,box,radius,rng)
    else:
        k=rng.randint(3,5);positions=triangle_pattern(k,box);params={'k':k};bounds=general_occluder(positions,box,radius,rng)
    flags=[inside(p,bounds) for p in positions];hidden=sum(flags);total=len(positions);iid=f'occluded_pattern_{i:04d}';color=PALETTE[(i-1)%len(PALETTE)];render(images/f'{iid}.png',size,positions,bounds,style,shape,radius,color)
    row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':list(size),'pattern_type':pattern,'pattern_params':params,'shape_type':shape,'object_color':list(color),'object_radius_px':radius,'total_object_count':total,'visible_object_count':total-hidden,'occluded_object_count':hidden,'occluder_bounds':[round(v,3) for v in bounds],'occluder_style':style,'object_positions':[{'x':p[0],'y':p[1],'occluded':flag} for p,flag in zip(positions,flags)],'seed':i,'difficulty_score':round(.32+.4*hidden/total+.08*(pattern!='grid')+.06*(style=='seamless'),4)};row['questions']=questions(iid,row);return row

def generate_dataset(n,output_dir,sample=False):
    root=Path(output_dir);images=root/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
    with (root/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for i in range(1,count+1):
            f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
            if i%250==0 or i==count:print(f'Generated {i}/{count}',flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='.');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
