import argparse,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);INK=(220,222,224);AA=3;CHOICES='ABCD';ANGLES=(45,90,135,180,225,270,315)
DATASET_VERSION='rotation-matching-2.0.0';MIN_TURN_DEGREES=25.0;MIN_SYMMETRY_DISTANCE=.08
def rotate(vertices,angle):
 a=math.radians(angle);c,s=math.cos(a),math.sin(a);return [[round(c*x-s*y,6),round(s*x+c*y,6)] for x,y in vertices]
def reflect(vertices,axis_angle=0):
 # Reflect across a line through the origin with direction axis_angle.
 a=math.radians(axis_angle);c=math.cos(2*a);s=math.sin(2*a);return [[round(c*x+s*y,6),round(s*x-c*y,6)] for x,y in vertices]
def normalize(vertices):
 cx=sum(x for x,y in vertices)/len(vertices);cy=sum(y for x,y in vertices)/len(vertices);v=[[x-cx,y-cy] for x,y in vertices];r=max(math.hypot(x,y) for x,y in v);return [[x/r,y/r] for x,y in v]
def turning_angles(vertices):
 out=[]
 for i,p in enumerate(vertices):
  prev=vertices[i-1];nxt=vertices[(i+1)%len(vertices)];a=(p[0]-prev[0],p[1]-prev[1]);b=(nxt[0]-p[0],nxt[1]-p[1]);den=math.hypot(*a)*math.hypot(*b);cos=max(-1,min(1,(a[0]*b[0]+a[1]*b[1])/den));out.append(math.degrees(math.acos(cos)))
 return out
def set_distance(a,b):
 return max(max(min(math.hypot(x-u,y-v) for u,v in b) for x,y in a),max(min(math.hypot(x-u,y-v) for x,y in a) for u,v in b))
def asymmetric(vertices):
 rots=[rotate(vertices,a) for a in ANGLES]
 if min(set_distance(vertices,v) for v in rots)<MIN_SYMMETRY_DISTANCE:return False
 mirrored=reflect(vertices)
 return min(set_distance(mirrored,v) for v in [vertices]+rots)>=MIN_SYMMETRY_DISTANCE
def make_reference(rng,n):
 rejected=0
 for _ in range(1000):
  radii=[rng.uniform(.56,1) for _ in range(n)];angles=[];cur=rng.uniform(0,.5)
  gaps=[rng.uniform(.72,1.28) for _ in range(n)];scale=2*math.pi/sum(gaps)
  for g in gaps:angles.append(cur);cur+=g*scale
  v=normalize([[radii[k]*math.cos(angles[k]),radii[k]*math.sin(angles[k])] for k in range(n)])
  ds=[math.hypot(v[(k+1)%n][0]-v[k][0],v[(k+1)%n][1]-v[k][1]) for k in range(n)]
  if min(ds)>.32 and len({round(x,2) for x in ds})>=max(4,n-2) and min(turning_angles(v))>=MIN_TURN_DEGREES and asymmetric(v):return v,rejected
  rejected+=1
 raise RuntimeError('unable to generate asymmetric reference')
def placed(vertices,cx,cy,scale):return [[round(cx+x*scale,4),round(cy+y*scale,4)] for x,y in vertices]
def font(size):
 p=Path('C:/Windows/Fonts/arialbd.ttf');return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()
def render(path,size,reference,candidates):
 im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im);f=font(14*AA);rf=font(15*AA)
 rv=placed(reference,size[0]/2,115,67);d.line([(round(x*AA),round(y*AA)) for x,y in rv+[rv[0]]],fill=INK,width=round(1.25*AA),joint='curve');d.text((25*AA,28*AA),'Reference',font=rf,fill=INK)
 d.line([(18*AA,198*AA),((size[0]-18)*AA,198*AA)],fill=(90,92,94),width=2)
 xs=[size[0]*(k+.5)/4 for k in range(4)]
 for k,c in enumerate(candidates):
  v=placed(c['vertices'],xs[k],292,43);d.line([(round(x*AA),round(y*AA)) for x,y in v+[v[0]]],fill=INK,width=round(1.15*AA),joint='curve');bb=d.textbbox((0,0),c['choice_label'],font=f);d.text((round(xs[k]*AA-(bb[2]-bb[0])/2),222*AA),c['choice_label'],font=f,fill=INK)
 im.resize(size,Image.Resampling.LANCZOS).save(path)
def questions(iid,row,rng):
 angle=row['correct_rotation_angle'];qs=[{'question_id':iid+'_q1','question_text':'How many vertices (corners) does the reference figure have?','question_type':'reference_vertex_count','ground_truth':str(row['num_reference_vertices']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':f'Which candidate shows the reference figure rigidly rotated {angle} degrees clockwise? Answer with the letter.','question_type':'target_angle_rotation_choice','ground_truth':row['correct_answer_choice'],'answer_format':'letter','difficulty_level':2}]
 probe=rng.choice([c for c in row['candidates'] if c['transformation_type']!='reflection']);label=probe['choice_label'];text=f'By how many degrees clockwise is candidate {label} rotated relative to the reference? Choose 45, 90, 135, 180, 225, 270, or 315 degrees.'
 qs.append({'question_id':iid+'_q3','question_text':text,'question_type':'candidate_rotation_angle','ground_truth':str(probe['applied_angle']),'answer_format':'numeric','difficulty_level':3,'candidate_label':label})
 reflection=next(c for c in row['candidates'] if c['transformation_type']=='reflection')
 qs.append({'question_id':iid+'_q4','question_text':'Exactly one candidate is a reflection (mirror image) rather than a rotation. Which one? Answer with the letter.','question_type':'reflection_choice','ground_truth':reflection['choice_label'],'answer_format':'letter','difficulty_level':4})
 extra=90;total=(angle+extra)%360 or 360
 qs.append({'question_id':iid+'_q5','question_text':f'If the reference were first rotated by the target angle of {angle} degrees clockwise and then rotated an additional {extra} degrees clockwise, what would the total normalized rotation be? Answer from 45, 90, 135, 180, 225, 270, 315, or 360 degrees.','question_type':'additional_rotation_angle','ground_truth':str(total),'answer_format':'numeric','difficulty_level':5,'additional_angle':extra});return qs
def generate_one(i,images):
 rng=random.Random(i);w=rng.randint(500,550);h=rng.randint(350,400);n=rng.randint(5,8);ref,rejections=make_reference(rng,n);angle=ANGLES[(i-1)%len(ANGLES)];correct=CHOICES[(i-1)%4];reflection_label=CHOICES[(CHOICES.index(correct)+1+rng.randrange(3))%4];base_reflected=reflect(rotate(ref,angle),0);wrong_angles=[a for a in ANGLES if a!=angle and min((a-angle)%360,(angle-a)%360)>=45];rng.shuffle(wrong_angles);wrong_iter=iter(wrong_angles);cands=[]
 for lab in CHOICES:
  if lab==correct:v=rotate(ref,angle);kind='target_rotation';applied=angle;is_correct=True
  elif lab==reflection_label:v=base_reflected;kind='reflection';applied=angle;is_correct=False
  else:applied=next(wrong_iter);v=rotate(ref,applied);kind='wrong_angle_rotation';is_correct=False
  cands.append({'choice_label':lab,'transformation_type':kind,'applied_angle':applied,'vertices':v,'is_correct':is_correct})
 iid=f'rotation_match_{i:04d}';render(images/f'{iid}.png',(w,h),ref,cands);row={'id':iid,'dataset_version':DATASET_VERSION,'image_path':f'images/{iid}.png','canvas_size':[w,h],'coordinate_frame':'image_plane_clockwise_degrees','reference_vertices':ref,'correct_rotation_angle':angle,'correct_answer_choice':correct,'reflection_answer_choice':reflection_label,'candidates':cands,'num_reference_vertices':n,'minimum_turning_angle_degrees':round(min(turning_angles(ref)),6),'minimum_turn_guard_degrees':MIN_TURN_DEGREES,'reference_generation_rejections':rejections,'seed':i,'difficulty_score':round(.34+.055*(n-5)+.08*(angle not in (90,180,270)),4)};row['questions']=questions(iid,row,rng);return row
def generate_dataset(n,out,sample=False):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for i in range(1,count+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
   if i%250==0 or i==count:print(f'Generated {i}/{count}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='rotation_matching_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
