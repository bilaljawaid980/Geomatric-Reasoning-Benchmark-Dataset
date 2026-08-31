import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw
BG=(26,26,26);INK=(137,105,180);AA=3
TYPES=('rotational_2','rotational_3','rotational_4','rotational_6','mirror_horizontal','mirror_vertical','mirror_both');BREAKS=('fill','rotation','position','size')
def rot(p,a):c=math.cos(a);s=math.sin(a);return(p[0]*c-p[1]*s,p[0]*s+p[1]*c)
def shape(x,y,a,size,orbit):return {'center':[round(x,4),round(y,4)],'rotation_angle':round(a%90,4),'size':round(size,4),'filled':False,'orbit_id':orbit}
def base_shapes(kind,rng):
 out=[]
 if kind.startswith('rotational_'):
  n=int(kind.rsplit('_',1)[1]);orbits=3 if n==2 else 2 if n in (3,4) else 1
  for o in range(orbits):
   radius=72+o*48+rng.uniform(-7,7);phase=rng.uniform(0,math.tau/n);a0=rng.uniform(8,82);size=rng.uniform(18,25)
   for k in range(n):
    ang=phase+math.tau*k/n;x,y=rot((radius,0),ang);out.append(shape(x,y,a0+360*k/n,size,o))
 elif kind in ('mirror_horizontal','mirror_vertical'):
  for o in range(4):
   x=rng.uniform(30,125)*(1 if o%2 else -1);y=rng.uniform(28,125);a=rng.uniform(8,82);size=rng.uniform(18,25)
   if kind=='mirror_horizontal':out.extend((shape(x,y,a,size,o),shape(x,-y,-a,size,o)))
   else:out.extend((shape(x,y,a,size,o),shape(-x,y,-a,size,o)))
 else:
  for o in range(2):
   x=rng.uniform(42,125);y=rng.uniform(42,125);a=rng.uniform(8,82);size=rng.uniform(18,25)
   out.extend((shape(x,y,a,size,o),shape(-x,y,-a,size,o),shape(x,-y,-a,size,o),shape(-x,-y,a,size,o)))
 return out
def loc(p):
 x,y=p
 if abs(x)<28 and abs(y)<28:return 'center'
 v='top' if y<0 else 'bottom';h='left' if x<0 else 'right'
 return v+'-'+h
def pos_transform(p,kind):
 x,y=p
 if kind.startswith('rotational_'):return rot((x,y),math.tau/int(kind.rsplit('_',1)[1]))
 if kind=='mirror_horizontal':return(x,-y)
 if kind=='mirror_vertical':return(-x,y)
 return(-x,y)
def partner_count(shapes,kind,tol=2):
 count=0
 for i,s in enumerate(shapes):
  tx,ty=pos_transform(s['center'],kind)
  if any(j!=i and math.hypot(t['center'][0]-tx,t['center'][1]-ty)<=tol for j,t in enumerate(shapes)):count+=1
 return count
def questions(iid,row):
 broken=row['is_broken'];qs=[{'question_id':iid+'_q1','question_text':'How many shapes are in this pattern?','question_type':'shape_count','ground_truth':str(row['num_shapes']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':"Is this pattern symmetric, or is there an element that breaks the symmetry? Answer 'symmetric' or 'broken'.",'question_type':'symmetry_status','ground_truth':'broken' if broken else 'symmetric','answer_format':'choice','difficulty_level':2}]
 if broken:text='Which shape breaks the symmetry? Answer with its approximate location, such as top-left, top-right, bottom-left, bottom-right, or center.';typ='broken_location';gt=row['broken_location']
 else:text="What type of symmetry does this pattern have — rotational or mirror/reflective? Answer 'rotational' or 'mirror'.";typ='symmetry_family';gt='rotational' if row['symmetry_type'].startswith('rotational') else 'mirror'
 qs.append({'question_id':iid+'_q3','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':'location' if broken else 'choice','difficulty_level':3})
 if broken:text="In what way does the odd shape differ — filled instead of outlined, rotated at a different angle, shifted out of position, or a different size?";typ='break_type';gt={'fill':'filled','rotation':'rotated','position':'shifted','size':'different size'}[row['break_type']];fmt='choice'
 elif row['seed']%2:text='If this pattern were rotated 90 degrees, would it look identical to its current appearance? Answer yes or no.';typ='rotation_90_invariant';gt='yes' if row['symmetry_type'] in ('rotational_4','rotational_6') else 'no';fmt='yes_no'
 else:text='How many shapes are positioned at the exact symmetric location of another shape? Answer with a number.';typ='symmetric_partner_count';gt=str(row['symmetric_partner_count']);fmt='numeric'
 qs.append({'question_id':iid+'_q4','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':4});return qs
def render(path,size,shapes):
 w,h=size;im=Image.new('RGB',(w*AA,h*AA),BG);d=ImageDraw.Draw(im)
 for s in shapes:
  cx=w/2+s['center'][0];cy=h/2+s['center'][1];r=s['size']/2;a=math.radians(s['rotation_angle']);pts=[]
  for k in range(4):
   q=a+math.pi/4+k*math.pi/2;pts.append((round((cx+r*math.cos(q))*AA),round((cy+r*math.sin(q))*AA)))
  if s['filled']:d.polygon(pts,fill=INK)
  else:d.line(pts+[pts[0]],fill=INK,width=round(1.2*AA),joint='curve')
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def generate_one(i,images):
 rng=random.Random(i);w=rng.randint(400,450);h=rng.randint(400,450);kind=TYPES[(i-1)%7]
 for _ in range(200):
  shapes=base_shapes(kind,rng)
  if min(math.hypot(a['center'][0]-b['center'][0],a['center'][1]-b['center'][1]) for j,a in enumerate(shapes) for b in shapes[j+1:])>=38:break
 else:raise RuntimeError('could not place separated symmetry orbits')
 broken=i%2==1;bt=None;bi=None
 if broken:
  bt=BREAKS[((i-1)//2)%4];bi=rng.randrange(len(shapes));s=shapes[bi]
  if bt=='fill':s['filled']=True
  elif bt=='rotation':s['rotation_angle']=round((s['rotation_angle']+rng.choice((-27,27)))%90,4)
  elif bt=='position':
   x,y=s['center'];m=max(1,math.hypot(x,y));shift=rng.uniform(11,16);ux,uy=x/m,y/m;candidates=[(x+ux*shift,y+uy*shift),(x-ux*shift,y-uy*shift),(x-uy*shift,y+ux*shift),(x+uy*shift,y-ux*shift)];others=[t['center'] for j,t in enumerate(shapes) if j!=bi];best=max(candidates,key=lambda p:min(math.hypot(p[0]-q[0],p[1]-q[1]) for q in others));s['center']=[round(best[0],4),round(best[1],4)]
  else:s['size']=round(s['size']*rng.choice((.68,1.38)),4)
 for j,s in enumerate(shapes):s['index']=j
 iid=f'symmetry_pattern_{i:04d}';render(images/f'{iid}.png',(w,h),shapes);row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'symmetry_type':kind,'is_broken':broken,'break_type':bt,'broken_shape_index':bi,'broken_shape_position':shapes[bi]['center'] if broken else None,'broken_location':loc(shapes[bi]['center']) if broken else None,'num_shapes':len(shapes),'shapes':shapes,'symmetric_partner_count':partner_count(shapes,kind),'seed':i,'difficulty_score':round(.3+.25*broken+.08*(len(shapes)-6)+.12*(bt in ('position','rotation')),4)};row['questions']=questions(iid,row);return row
def generate_dataset(n,out):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True)
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for i in range(1,n+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
   if i%250==0 or i==n:print(f'Generated {i}/{n}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='symmetry_pattern_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=='__main__':main()
