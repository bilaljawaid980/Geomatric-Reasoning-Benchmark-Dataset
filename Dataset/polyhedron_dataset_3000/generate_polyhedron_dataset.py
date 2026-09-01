import argparse,itertools,json,math,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
BG=(26,26,26);INK=(118,172,190);AA=3;PHI=(1+5**.5)/2;VERSION='polyhedron-5.0.0'
def unique(points):
 out=[]
 for p in points:
  p=np.array(p,float)
  if not any(np.linalg.norm(p-q)<1e-7 for q in out):out.append(p)
 return np.array(out)
def hull_faces(v):
 n=len(v);planes={};eps=1e-7
 for i,j,k in itertools.combinations(range(n),3):
  normal=np.cross(v[j]-v[i],v[k]-v[i]);ln=np.linalg.norm(normal)
  if ln<eps:continue
  normal/=ln;d=(v-v[i])@normal
  if np.all(d<=eps) or np.all(d>=-eps):
   if np.mean(d)>0:normal=-normal
   off=float(normal@v[i]);key=tuple(np.round(np.r_[normal,off],6));idx=tuple(np.where(np.abs(v@normal-off)<1e-5)[0]);planes[idx]=normal
 faces=[]
 for idx,normal in planes.items():
  if len(idx)<3:continue
  c=v[list(idx)].mean(0);u=v[idx[0]]-c;u/=np.linalg.norm(u);w=np.cross(normal,u);order=sorted(idx,key=lambda z:math.atan2((v[z]-c)@w,(v[z]-c)@u));faces.append(order)
 return faces
def edges_from_faces(faces):return sorted({tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1])})
def mesh(v):
 v=unique(v);f=hull_faces(v);return {'vertices':v,'faces':f,'edges':edges_from_faces(f)}
def truncate(m,t=1/3):
 pts=[]
 for a,b in m['edges']:pts.extend(((1-t)*m['vertices'][a]+t*m['vertices'][b],(1-t)*m['vertices'][b]+t*m['vertices'][a]))
 return mesh(pts)
def rectify(m):return mesh([(m['vertices'][a]+m['vertices'][b])/2 for a,b in m['edges']])
def dual(m):
 pts=[]
 for f in m['faces']:
  p=m['vertices'][f];n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n);c=p.mean(0)
  if n@c<0:n=-n
  pts.append(n/(n@c))
 return mesh(pts)
TET=mesh([(1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1)]);CUBE=mesh(list(itertools.product((-1,1),repeat=3)));OCT=mesh([(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)])
ICO=mesh([(0,a,b) for a in (-1,1) for b in (-PHI,PHI)]+[(a,b,0) for a in (-1,1) for b in (-PHI,PHI)]+[(b,0,a) for a in (-1,1) for b in (-PHI,PHI)])
DOD=dual(ICO);TT=truncate(TET);TC=truncate(CUBE);TO=truncate(OCT);CO=rectify(CUBE);ID=rectify(ICO)
RCO=mesh(unique([p for perm in set(itertools.permutations((1,1,1+2**.5))) for signs in itertools.product((-1,1),repeat=3) for p in [tuple(perm[k]*signs[k] for k in range(3))]]))
def compound(parts):
 verts=[];faces=[];edges=[];off=0
 for m in parts:
  verts.extend(m['vertices']);faces.extend([[x+off for x in f] for f in m['faces']]);edges.extend([(a+off,b+off) for a,b in m['edges']]);off+=len(m['vertices'])
 return {'vertices':np.array(verts),'faces':faces,'edges':edges}
TET2={'vertices':-TET['vertices'],'faces':TET['faces'],'edges':TET['edges']}
SPECS=[]
def face_shape_type(faces):
 arities={len(face) for face in faces}
 return {frozenset({3}):'triangles',frozenset({4}):'squares',frozenset({5}):'pentagons'}.get(frozenset(arities),'mixed')
def add(name,cls,m,convex,shape,counts=None):
 v,e,f=(len(m['vertices']),len(m['edges']),len(m['faces'])) if counts is None else counts
 derived_shape=face_shape_type(m['faces'])
 assert shape==derived_shape,(name,shape,derived_shape)
 SPECS.append({'name':name,'class':cls,'mesh':m,'is_convex':convex,'face_shape_types':derived_shape,'vertex_count':v,'edge_count':e,'face_count':f})
for x in [('tetrahedron',TET,'triangles'),('cube',CUBE,'squares'),('octahedron',OCT,'triangles'),('dodecahedron',DOD,'pentagons'),('icosahedron',ICO,'triangles')]:add(x[0],'Platonic',x[1],True,x[2])
for x in [('truncated tetrahedron',TT),('cuboctahedron',CO),('truncated cube',TC),('truncated octahedron',TO),('rhombicuboctahedron',RCO),('icosidodecahedron',ID)]:add(x[0],'Archimedean',x[1],True,'mixed')
for name,m in [('triakis tetrahedron',dual(TT)),('rhombic dodecahedron',dual(CO)),('triakis octahedron',dual(TC)),('rhombic triacontahedron',dual(ID))]:add(name,'Catalan',m,True,face_shape_type(m['faces']))
add('stella octangula','Compound',compound([TET,TET2]),False,'triangles',(8,12,8));add('compound of cube and octahedron','Compound',compound([CUBE,OCT]),False,'mixed',(14,24,14))
# The former two entries reused the regular icosahedron/dodecahedron face complexes
# and merely injected face diagonals.  Name and classify the geometry that is
# actually stored and rendered; edge arrays always come from face boundaries.
add('icosahedron','Platonic',ICO,True,'triangles');add('dodecahedron','Platonic',DOD,True,'pentagons')
assert len(SPECS)==19
for s in SPECS:
 assert len(s['mesh']['faces'])==s['face_count']
 assert len(s['mesh']['edges'])==s['edge_count']
 assert face_shape_type(s['mesh']['faces'])==s['face_shape_types']
 components=2 if s['class']=='Compound' else 1
 assert s['vertex_count']-s['edge_count']+s['face_count']==2*components,(s['name'],s['vertex_count'],s['edge_count'],s['face_count'])
def rotation(ry,tx):
 y=math.radians(ry);x=math.radians(tx);Ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]]);Rx=np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]]);return Rx@Ry
def visible_faces(v,faces,R):
 q=v@R.T;n=0
 for f in faces:
  p=q[f];normal=np.cross(p[1]-p[0],p[2]-p[0]);c=p.mean(0)
  if normal@c<0:normal=-normal
  if normal[2]>1e-8:n+=1
 return n
def render(path,size,m,ry,tx,scale):
 R=rotation(ry,tx);q=m['vertices']@R.T;rad=max(np.ptp(q[:,0]),np.ptp(q[:,1]));q=q*(scale/rad);q2=np.c_[size[0]/2+q[:,0],size[1]/2-q[:,1]];im=Image.new('RGB',(size[0]*AA,size[1]*AA),BG);d=ImageDraw.Draw(im)
 for a,b in m['edges']:d.line([(round(q2[a,0]*AA),round(q2[a,1]*AA)),(round(q2[b,0]*AA),round(q2[b,1]*AA))],fill=INK,width=round(1.05*AA))
 im.resize(size,Image.Resampling.LANCZOS).save(path);return q2
def questions(iid,row,rng):
 qs=[{'question_id':iid+'_q1','question_text':'How many faces does this solid have in total, including hidden faces?','question_type':'face_count','ground_truth':str(row['face_count']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':"Is this solid convex or non-convex? Answer 'convex' or 'non-convex'.",'question_type':'convexity','ground_truth':'convex' if row['is_convex'] else 'non-convex','answer_format':'choice','difficulty_level':2}]
 t=rng.choice(('shape','visible','vertices'))
 if t=='shape':text='What shape are the faces of this solid — triangles, squares, pentagons, or a mix of shapes?';typ='face_shapes';gt=row['face_shape_types'];fmt='choice'
 elif t=='visible':text='How many faces of this solid face toward the camera from this viewing angle?';typ='visible_face_count';gt=str(row['visible_face_count']);fmt='numeric'
 else:text='How many vertices (corner points) does this solid have?';typ='vertex_count';gt=str(row['vertex_count']);fmt='numeric'
 qs.append({'question_id':iid+'_q3','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':3})
 z=rng.random()
 if row['is_convex'] and z<.45:text=f"Using Euler's formula, if this solid has {row['vertex_count']} vertices and {row['edge_count']} edges, how many faces must it have?";typ='euler_face_count';gt=str(2-row['vertex_count']+row['edge_count']);fmt='numeric'
 elif z<.7:text='Is this solid composed of overlapping shapes forming a compound structure? Answer yes or no.';typ='is_compound';gt='yes' if row['solid_class']=='Compound' else 'no';fmt='yes_no'
 else:text='Which family does this solid belong to: Platonic, Archimedean, Catalan, Compound, or Non-convex?';typ='solid_family';gt=row['solid_class'];fmt='choice'
 qs.append({'question_id':iid+'_q4','question_text':text,'question_type':typ,'ground_truth':gt,'answer_format':fmt,'difficulty_level':4})
 qs.append({'question_id':iid+'_q5','question_text':'If one face were removed from this solid while all remaining faces stayed fixed, would the result still be a closed surface to which the closed-surface Euler formula directly applies? Answer yes or no.','question_type':'remove_face_closed_surface','ground_truth':'no','answer_format':'yes_no','difficulty_level':5});return qs
def generate_one(i,images):
 rng=random.Random(i);s=SPECS[(i-1)%len(SPECS)];w=rng.randint(450,500);h=rng.randint(450,500);ry=rng.uniform(0,360);tx=rng.uniform(15,45);scale=rng.uniform(250,330);iid=f'polyhedron_{i:04d}';render(images/f'{iid}.png',(w,h),s['mesh'],ry,tx,scale);vf=visible_faces(s['mesh']['vertices'],s['mesh']['faces'],rotation(ry,tx));row={'id':iid,'image_path':f'images/{iid}.png','canvas_size':[w,h],'dataset_version':VERSION,'solid_name':s['name'],'solid_class':s['class'],'face_count':s['face_count'],'edge_count':s['edge_count'],'vertex_count':s['vertex_count'],'is_convex':s['is_convex'],'face_shape_types':s['face_shape_types'],'viewing_angle':{'rotation_y':round(ry,6),'tilt_x':round(tx,6)},'visible_face_count':vf,'vertices':np.round(s['mesh']['vertices'],8).tolist(),'faces':[[int(x) for x in f] for f in s['mesh']['faces']],'edges':[[int(a),int(b)] for a,b in s['mesh']['edges']],'seed':i};row['questions']=questions(iid,row,rng);return row
def generate_dataset(n,out):
 out=Path(out);images=out/'images';images.mkdir(parents=True,exist_ok=True)
 with (out/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for i in range(1,n+1):
   f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
   if i%250==0 or i==n:print(f'Generated {i}/{n}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='polyhedron_dataset_3000');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(5 if a.sample else a.n,a.output_dir)
if __name__=='__main__':main()
