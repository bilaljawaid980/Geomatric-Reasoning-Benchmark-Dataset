"""Generate deterministic 3D voxel-combination reasoning puzzles."""
import argparse,json,random
from itertools import combinations
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);EDGE=(222,226,226);TOP=(115,159,169);LEFT=(75,123,135);RIGHT=(54,96,108)
DATASET_VERSION='combination3d-2.0.0';VERTICAL_AXIS='z'
AA=3;LETTERS='ABCD';DIRS=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))

def canonical(cubes):
    cubes={tuple(c) for c in cubes};mins=[min(c[i] for c in cubes) for i in range(3)]
    return tuple(sorted(tuple(c[i]-mins[i] for i in range(3)) for c in cubes))

def rz(c):x,y,z=c;return(-y,x,z)
def rx(c):x,y,z=c;return(x,-z,y)
def ry(c):x,y,z=c;return(z,y,-x)

def orientations(cubes,mode='z_only'):
    start=canonical(cubes);seen={start};todo=[start]
    rotations=(rz,) if mode=='z_only' else (rx,ry,rz)
    while todo:
        shape=todo.pop()
        for rotate in rotations:
            nxt=canonical(rotate(c) for c in shape)
            if nxt not in seen:seen.add(nxt);todo.append(nxt)
    return sorted(seen)

def placements(piece,target,mode):
    target=set(target);result=set()
    for shape in orientations(piece,mode):
        for anchor in shape:
            for destination in target:
                delta=tuple(destination[i]-anchor[i] for i in range(3))
                placed=frozenset(tuple(c[i]+delta[i] for i in range(3)) for c in shape)
                if placed<=target:result.add(placed)
    return sorted(result,key=lambda p:sorted(p))

def try_assemble_3d(pieces,target,rotation_axes='z_only'):
    target=frozenset(target)
    if sum(len(p) for p in pieces)!=len(target):return False
    options=[placements(p,target,rotation_axes) for p in pieces]
    if any(not x for x in options):return False
    order=sorted(range(len(pieces)),key=lambda i:len(options[i]))
    def search(depth,used):
        if depth==len(order):return used==target
        return any(search(depth+1,used|p) for p in options[order[depth]] if not used&p)
    return search(0,frozenset())

def connected(cubes):
    cubes=set(cubes);seen={next(iter(cubes))};todo=list(seen)
    while todo:
        c=todo.pop()
        for d in DIRS:
            q=tuple(c[i]+d[i] for i in range(3))
            if q in cubes and q not in seen:seen.add(q);todo.append(q)
    return seen==cubes

def gravity_valid(cubes):
    cubes=set(cubes);return all(z==0 or (x,y,z-1) in cubes for x,y,z in cubes)

def generate_valid_structure(n,rng):
    base_n=rng.randint(4,min(10,n));foot={(0,0)}
    while len(foot)<base_n:
        x,y=rng.choice(tuple(foot));dx,dy=rng.choice(((1,0),(-1,0),(0,1),(0,-1)));foot.add((x+dx,y+dy))
    heights={p:1 for p in foot}
    for _ in range(n-base_n):
        choices=[p for p,h in heights.items() if h<5];heights[rng.choice(choices)]+=1
    cubes=canonical((x,y,z) for (x,y),height in heights.items() for z in range(height))
    assert connected(cubes) and gravity_valid(cubes);return cubes

def partition(cubes,k,rng):
    cubes=set(cubes)
    for _ in range(100):
        root=rng.choice(tuple(cubes));seen={root};tree=[];stack=[root]
        while stack:
            c=stack[-1];neighbors=[]
            for d in DIRS:
                q=tuple(c[i]+d[i] for i in range(3))
                if q in cubes and q not in seen:neighbors.append(q)
            if neighbors:
                q=rng.choice(neighbors);seen.add(q);tree.append((c,q));stack.append(q)
            else:stack.pop()
        valid=[]
        for cut_tuple in combinations(range(len(tree)),k-1):
            cuts=set(cut_tuple);adj={c:[] for c in cubes}
            for i,(a,b) in enumerate(tree):
                if i not in cuts:adj[a].append(b);adj[b].append(a)
            parts=[];remaining=set(cubes)
            while remaining:
                start=remaining.pop();part={start};todo=[start]
                while todo:
                    c=todo.pop()
                    for q in adj[c]:
                        if q in remaining:remaining.remove(q);part.add(q);todo.append(q)
                parts.append(canonical(part))
            if len(parts)==k and min(map(len,parts))>=2:valid.append(parts)
        if valid:return rng.choice(valid)
    raise RuntimeError('could not partition target into nontrivial connected pieces')

def grow_polycube(n,rng):
    cubes={(0,0,0)}
    while len(cubes)<n:
        c=rng.choice(tuple(cubes));d=rng.choice(DIRS);cubes.add(tuple(c[i]+d[i] for i in range(3)))
    return canonical(cubes)

def compositions(total,k,rng):
    while True:
        cuts=sorted(rng.sample(range(1,total),k-1));parts=[b-a for a,b in zip([0]+cuts,cuts+[total])]
        if min(parts)>=2:return parts

def make_near_miss(total,target,rng):
    for _ in range(1000):
        k=rng.randint(2,3);pieces=[grow_polycube(n,rng) for n in compositions(total,k,rng)]
        if not try_assemble_3d(pieces,target,'all'):return pieces
    raise RuntimeError('could not construct full-rotation-resistant near miss')

def make_wrong_count(correct,rng):
    pieces=[list(p) for p in correct];i=max(range(len(pieces)),key=lambda j:len(pieces[j]));shape=set(pieces[i]);boundary=[]
    for c in shape:
        for d in DIRS:
            q=tuple(c[a]+d[a] for a in range(3))
            if q not in shape:boundary.append(q)
    shape.add(rng.choice(boundary));pieces[i]=list(canonical(shape));return [canonical(p) for p in pieces]

def tipped(pieces,rotate):return [canonical(rotate(c) for c in p) for p in pieces]

def build_geometry(n,rng):
    tumble_transforms=[rx,ry,lambda c:rx(rz(c)),lambda c:ry(rz(c))]
    for _ in range(800):
        target=generate_valid_structure(n,rng)
        try:correct=partition(target,rng.randint(2,3),rng)
        except RuntimeError:continue
        rng.shuffle(tumble_transforms)
        for transform in tumble_transforms:
            tumble=tipped(correct,transform)
            if not try_assemble_3d(tumble,target,'z_only') and try_assemble_3d(tumble,target,'all'):
                near=make_near_miss(n,target,rng);wrong=make_wrong_count(correct,rng)
                return target,correct,near,wrong,tumble
    raise RuntimeError('could not construct verified 3D puzzle')

def iso_project(c):
    x,y,z=c;return((x-y)*.8660254,(x+y)*.5-z)

def cube_hidden(c,cubes):
    x,y,z=c;s=set(cubes);return any((x+k,y+k,z+k) in s for k in range(1,16))

def face_vertices(c,face):
    x,y,z=c
    if face=='top':return ((x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1))
    if face=='right':return ((x+1,y,z),(x+1,y+1,z),(x+1,y+1,z+1),(x+1,y,z+1))
    return ((x,y+1,z),(x+1,y+1,z),(x+1,y+1,z+1),(x,y+1,z+1))

def visible_faces(cubes):
    cubes={tuple(c) for c in cubes};faces=[]
    for c in cubes:
        if cube_hidden(c,cubes):continue
        x,y,z=c
        if (x,y,z+1) not in cubes:faces.append((c,'top'))
        if (x+1,y,z) not in cubes:faces.append((c,'right'))
        if (x,y+1,z) not in cubes:faces.append((c,'left'))
    return sorted(faces,key=lambda item:(sum(item[0]),item[0][2],{'left':0,'right':1,'top':2}[item[1]]))

def projection_bounds(cubes):
    faces=visible_faces(cubes);raw=[iso_project(v) for c,f in faces for v in face_vertices(c,f)]
    return faces,min(x for x,y in raw),max(x for x,y in raw),min(y for x,y in raw),max(y for x,y in raw)

def draw_structure(draw,cubes,box,forced_scale=None):
    faces,minx,maxx,miny,maxy=projection_bounds(cubes)
    x0,y0,x1,y1=box;scale=forced_scale or min((x1-x0-8)/max(.1,maxx-minx),(y1-y0-8)/max(.1,maxy-miny));ox=(x0+x1)/2-scale*(minx+maxx)/2;oy=(y0+y1)/2-scale*(miny+maxy)/2
    colors={'top':TOP,'left':LEFT,'right':RIGHT}
    for c,f in faces:
        points=[((ox+scale*x)*AA,(oy+scale*y)*AA) for x,y in map(iso_project,face_vertices(c,f))]
        draw.polygon(points,fill=colors[f]);draw.line(points+[points[0]],fill=EDGE,width=max(2,round(.7*AA)),joint='curve')

def font(size):
    path=Path('C:/Windows/Fonts/arialbd.ttf');return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default()

def candidate_piece_boxes(panel,count):
    x0,y0,x1,y1=panel;left=x0+28;right=x1-8;gap=5;width=(right-left-gap*(count-1))/count
    return [(left+i*(width+gap),y0+27,left+i*(width+gap)+width,y1-6) for i in range(count)]

def render(path,size,target,candidates):
    w,h=size;image=Image.new('RGB',(w*AA,h*AA),BG);draw=ImageDraw.Draw(image);title=font(14*AA);label=font(13*AA)
    draw.text((18*AA,12*AA),'Target',fill=EDGE,font=title);draw_structure(draw,target,(65,28,w-65,180))
    draw.line(((14*AA,192*AA),((w-14)*AA,192*AA)),fill=(74,77,78),width=2)
    panels=((0,198,w/2,335),(w/2,198,w,335),(0,335,w/2,h),(w/2,335,w,h))
    for candidate,panel in zip(candidates,panels):
        x0,y0,x1,y1=panel;draw.text(((x0+10)*AA,(y0+7)*AA),candidate['choice_label'],fill=EDGE,font=label)
        boxes=candidate_piece_boxes(panel,len(candidate['pieces']));scales=[]
        for piece,box in zip(candidate['pieces'],boxes):
            _,minx,maxx,miny,maxy=projection_bounds(piece);scales.append(min((box[2]-box[0]-8)/max(.1,maxx-minx),(box[3]-box[1]-8)/max(.1,maxy-miny)))
        common=min(scales)
        for piece,box in zip(candidate['pieces'],boxes):draw_structure(draw,piece,box,common)
    image.resize((w,h),Image.Resampling.LANCZOS).save(path,'PNG')

def make_questions(iid,row,rng):
    questions=[
      {'question_id':iid+'_q1','question_text':'How many individual cubes make up the target structure?','question_type':'target_cube_count','ground_truth':str(row['target_cube_count']),'answer_format':'numeric','difficulty_level':1},
      {'question_id':iid+'_q2','question_text':'Which set of pieces (A, B, C, or D) can be assembled using only translation and rotation around the vertical axis to exactly form the target structure? Answer with the letter.','question_type':'assembly3d_choice','ground_truth':row['correct_answer_choice'],'answer_format':'letter','difficulty_level':2}]
    if rng.random()<.5:
        c=rng.choice(row['candidates']);q={'question_text':f"How many separate pieces are shown in candidate {c['choice_label']}?",'question_type':'candidate_piece_count','ground_truth':str(len(c['pieces'])),'answer_format':'numeric','candidate_label':c['choice_label']}
    else:
        c=rng.choice([x for x in row['candidates'] if not x['is_valid_assembly']]);q={'question_text':f"Does candidate {c['choice_label']} have the same total number of cubes as the target? Answer yes or no.",'question_type':'candidate_same_count','ground_truth':'yes' if c['total_cube_count']==row['target_cube_count'] else 'no','answer_format':'yes_no','candidate_label':c['choice_label']}
    questions.append({'question_id':iid+'_q3','difficulty_level':3,**q})
    kind=rng.choice(('tumble','wrong','height'))
    if kind=='tumble':q={'question_text':'Which candidate has the correct cube count and piece shapes but would require tipping a piece onto a different face, rather than only spinning it around the vertical axis?','question_type':'requires_3d_tumble_choice','ground_truth':next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='requires_3d_tumble'),'answer_format':'letter'}
    elif kind=='wrong':q={'question_text':'Which candidate has the wrong total number of cubes compared to the target?','question_type':'wrong_count_choice','ground_truth':next(c['choice_label'] for c in row['candidates'] if c['failure_reason']=='wrong_count'),'answer_format':'letter'}
    else:
        height=max(c[2] for c in row['target_cubes'])-min(c[2] for c in row['target_cubes'])+1
        q={'question_text':"Give the target's total cube count and maximum height along the vertical z-axis in layers as count,height.",'question_type':'target_count_and_height','ground_truth':f"{row['target_cube_count']},{height}",'answer_format':'count,height'}
    questions.append({'question_id':iid+'_q4','difficulty_level':4,**q})
    if rng.random()<.5:
        q={'question_text':"If the correctly assembled structure were rotated 90 degrees around the vertical z-axis as a whole, would it be the 'same shape, different angle' or a 'different structure'?",'question_type':'whole_group_rotation','ground_truth':'same shape, different angle','answer_format':'short_text'}
    else:
        height=max(c[2] for c in row['target_cubes'])-min(c[2] for c in row['target_cubes'])+1
        q={'question_text':'If one cube were added directly above a highest cube, what would the new total cube count and maximum height along the vertical z-axis be? Answer as count,height.','question_type':'add_cube_above_highest','ground_truth':f"{row['target_cube_count']+1},{height+1}",'answer_format':'count,height'}
    questions.append({'question_id':iid+'_q5','difficulty_level':5,**q});return questions

def generate_one(i,images):
    rng=random.Random(i);size=(rng.randint(550,620),rng.randint(420,480));n=rng.randint(8,14);target,correct,near,wrong,tumble=build_geometry(n,rng)
    correct_label=LETTERS[(i-1)%4];other=[x for x in LETTERS if x!=correct_label];rng.shuffle(other);labels=[correct_label]+other
    roles=((correct,None),(near,'gap_or_overlap'),(wrong,'wrong_count'),(tumble,'requires_3d_tumble'));candidates=[]
    for label,(pieces,reason) in zip(labels,roles):candidates.append({'choice_label':label,'pieces':[[list(c) for c in p] for p in pieces],'total_cube_count':sum(map(len,pieces)),'is_valid_assembly':reason is None,'failure_reason':reason})
    candidates.sort(key=lambda c:LETTERS.index(c['choice_label']));iid=f'combination3d_{i:04d}'
    render(images/f'{iid}.png',size,target,candidates)
    row={'id':iid,'dataset_version':DATASET_VERSION,'image_path':f'images/{iid}.png','canvas_size':list(size),'coordinate_frame':'right_handed_xyz','vertical_axis':VERTICAL_AXIS,'renderer_projection':'screen_x=0.8660254*(x-y); screen_y=0.5*(x+y)-z','permitted_piece_rotation_axes':['z'],'target_cubes':[list(c) for c in target],'target_cube_count':n,'gravity_supported':True,'candidates':candidates,'correct_answer_choice':correct_label,'seed':i,'difficulty_score':round(.35+.04*(n-8)+.07*(len(correct)-2),4)}
    row['questions']=make_questions(iid,row,rng);return row

def generate_dataset(n,output_dir,sample=False):
    root=Path(output_dir);images=root/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
    with (root/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as handle:
        for i in range(1,count+1):
            handle.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
            if i%250==0 or i==count:print(f'Generated {i}/{count}',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='.');p.add_argument('--sample',action='store_true');a=p.parse_args();generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
