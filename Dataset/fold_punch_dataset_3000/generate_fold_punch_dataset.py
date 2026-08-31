"""Generate deterministic center-fold-and-punch spatial reasoning puzzles."""
import argparse,json,random
from dataclasses import dataclass
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

BG=(26,26,26);PAPER=(205,214,216);EDGE=(224,228,228);ACCENT=(72,196,216);GUIDE=(174,184,186);DOT=(12,12,12);AA=3;LETTERS='ABCD'
DATASET_VERSION='fold-punch-2.0.0';MIN_DISTRACTOR_DISPLACEMENT=0.04

@dataclass
class FoldState:
    bounds: tuple=(0.0,1.0,0.0,1.0)
    layers: tuple=((1.0,0.0,1.0,0.0),) # original x=sx*x+ox, y=sy*y+oy
    def apply(self,fold):
        xmin,xmax,ymin,ymax=self.bounds;axis=fold['axis'];direction=fold['direction'];new=[]
        if axis=='vertical':
            mid=(xmin+xmax)/2
            if direction=='right over left':bounds=(xmin,mid,ymin,ymax)
            else:bounds=(mid,xmax,ymin,ymax)
            for sx,ox,sy,oy in self.layers:
                new.extend(((sx,ox,sy,oy),(-sx,2*mid*sx+ox,sy,oy)))
        else:
            mid=(ymin+ymax)/2
            if direction=='top over bottom':bounds=(xmin,xmax,ymin,mid)
            else:bounds=(xmin,xmax,mid,ymax)
            for sx,ox,sy,oy in self.layers:
                new.extend(((sx,ox,sy,oy),(sx,ox,-sy,2*mid*sy+oy)))
        return FoldState(bounds,tuple(new))
    def punch_origins(self,punch):
        x,y=punch;return sorted({(round(sx*x+ox,6),round(sy*y+oy,6)) for sx,ox,sy,oy in self.layers})

def simulate_folds(sequence):
    states=[FoldState()]
    for fold in sequence:states.append(states[-1].apply(fold))
    return states

def generate_sequence(n,rng):
    sequence=[]
    for _ in range(n):
        axis=rng.choice(('horizontal','vertical'))
        direction=rng.choice(('top over bottom','bottom over top')) if axis=='horizontal' else rng.choice(('left over right','right over left'))
        sequence.append({'axis':axis,'direction':direction})
    return sequence

def alternate_punch(state,punch,rng):
    xmin,xmax,ymin,ymax=state.bounds
    for _ in range(100):
        q=(rng.uniform(xmin+.35*(xmax-xmin),xmax-.35*(xmax-xmin)),rng.uniform(ymin+.35*(ymax-ymin),ymax-.35*(ymax-ymin)))
        holes=state.punch_origins(q)
        if holes!=state.punch_origins(punch):return q,holes
    raise RuntimeError('could not create alternate punch')

def broken_symmetry(correct,rng):
    # Reflect the complete pattern about wrong axes while contracting it by
    # ten percent so every dot remains recoverable inside the answer panel.
    # This is a global structural error, never a one-hole coordinate nudge.
    result=sorted((round(1-.9*x,6),round(1-.9*y,6)) for x,y in correct)
    if len(set(result))!=len(correct) or result==list(correct):raise RuntimeError('wrong-axis reflection degenerated')
    return result,'shifted_vertical_and_horizontal_axes'

def make_candidates(correct,state,punch,correct_label,rng):
    _,wrong_positions=alternate_punch(state,punch,rng)
    wrong_symmetry,wrong_axis=broken_symmetry(correct,rng)
    wrong_count=list(correct);wrong_count.pop(rng.randrange(len(wrong_count)))
    other=[x for x in LETTERS if x!=correct_label];rng.shuffle(other);labels=[correct_label]+other
    roles=((correct,None,None),(wrong_count,'wrong_count',None),(wrong_positions,'wrong_positions',None),(wrong_symmetry,'wrong_symmetry',wrong_axis));candidates=[]
    for label,(holes,error,axis) in zip(labels,roles):candidates.append({'choice_label':label,'hole_positions':[list(p) for p in holes],'error_type':error,'wrong_symmetry_axis':axis})
    return sorted(candidates,key=lambda c:LETTERS.index(c['choice_label']))

def font(size):
    path=Path('C:/Windows/Fonts/arialbd.ttf');return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default()

def dashed(draw,xy,fill,width,dash=6):
    x0,y0,x1,y1=xy
    if abs(x1-x0)<1:
        y=y0
        while y<y1:draw.line((x0*AA,y*AA,x1*AA,min(y+dash,y1)*AA),fill=fill,width=width);y+=dash*2
    else:
        x=x0
        while x<x1:draw.line((x*AA,y0*AA,min(x+dash,x1)*AA,y1*AA),fill=fill,width=width);x+=dash*2

def arrow(draw,start,end):
    sx,sy=start;ex,ey=end;draw.line((sx*AA,sy*AA,ex*AA,ey*AA),fill=ACCENT,width=3*AA)
    dx,dy=ex-sx,ey-sy;length=max(1,(dx*dx+dy*dy)**.5);ux,uy=dx/length,dy/length;px,py=-uy,ux
    pts=[(ex*AA,ey*AA),((ex-9*ux+5*px)*AA,(ey-9*uy+5*py)*AA),((ex-9*ux-5*px)*AA,(ey-9*uy-5*py)*AA)];draw.polygon(pts,fill=ACCENT)

def crosshair(draw,rect):
    x0,y0,x1,y1=rect;cx=(x0+x1)/2;cy=(y0+y1)/2
    draw.line((cx*AA,(y0+3)*AA,cx*AA,(y1-3)*AA),fill=GUIDE,width=AA)
    draw.line(((x0+3)*AA,cy*AA,(x1-3)*AA,cy*AA),fill=GUIDE,width=AA)

def dot(draw,x,y,diameter):
    r=diameter/2;draw.ellipse(((x-r)*AA,(y-r)*AA,(x+r)*AA,(y+r)*AA),fill=DOT,outline=EDGE,width=max(2,round(.75*AA)))

def map_rect(bounds,box):
    xmin,xmax,ymin,ymax=bounds;x0,y0,x1,y1=box;maxdim=max(xmax-xmin,ymax-ymin);scale=min((x1-x0-8)/maxdim,(y1-y0-8)/maxdim);cx=(x0+x1)/2;cy=(y0+y1)/2
    return (cx-(xmax-xmin)*scale/2,cy-(ymax-ymin)*scale/2,cx+(xmax-xmin)*scale/2,cy+(ymax-ymin)*scale/2),scale

def draw_fold_step(draw,state,fold,box,index):
    rect,scale=map_rect(state.bounds,box);x0,y0,x1,y1=rect;draw.rectangle(tuple(v*AA for v in rect),fill=PAPER,outline=EDGE,width=2*AA)
    xmin,xmax,ymin,ymax=state.bounds
    if fold['axis']=='vertical':
        line=(x0+x1)/2;dashed(draw,(line,y0,line,y1),ACCENT,3*AA);right=fold['direction']=='right over left';arrow(draw,(line+(x1-x0)*(.30 if right else -.30),(y0+y1)/2),(line+(x1-x0)*(-.20 if right else .20),(y0+y1)/2))
    else:
        line=(y0+y1)/2;dashed(draw,(x0,line,x1,line),ACCENT,3*AA);top=fold['direction']=='top over bottom';arrow(draw,((x0+x1)/2,line-(y1-y0)*(.30 if top else -.30)),((x0+x1)/2,line+(y1-y0)*(.20 if top else -.20)))
    draw.text(((box[0]+3)*AA,(box[1]+1)*AA),str(index),font=font(10*AA),fill=EDGE)

def original_to_box(point,box):
    x,y=point;x0,y0,x1,y1=box;return (x0+x*(x1-x0),y1-y*(y1-y0))

def render_layout(size):
    w,h=size;divider=150;mid=(h+divider)/2
    panels=((0,divider+3,w/2,mid),(w/2,divider+3,w,mid),(0,mid,w/2,h),(w/2,mid,w,h));boxes=[]
    for x0,y0,x1,y1 in panels:
        side=min(y1-y0-6,x1-x0-42);boxes.append((x0+(x1-x0-side)/2,y0+3,x0+(x1-x0+side)/2,y0+3+side))
    return divider,panels,boxes

def render(path,size,sequence,states,punch,candidates):
    w,h=size;im=Image.new('RGB',(w*AA,h*AA),BG);draw=ImageDraw.Draw(im);title=font(13*AA);label=font(12*AA)
    draw.text((10*AA,7*AA),'Fold sequence',fill=EDGE,font=title);step_y=(24,147);count=len(sequence)+1;gap=6;step_w=(w-20-gap*(count-1))/count
    for i,(state,fold) in enumerate(zip(states[:-1],sequence)):draw_fold_step(draw,state,fold,(10+i*(step_w+gap),step_y[0],10+i*(step_w+gap)+step_w,step_y[1]),i+1)
    final_box=(10+len(sequence)*(step_w+gap),step_y[0],10+len(sequence)*(step_w+gap)+step_w,step_y[1]-18);rect,_=map_rect(states[-1].bounds,final_box);draw.rectangle(tuple(v*AA for v in rect),fill=PAPER,outline=EDGE,width=2*AA);crosshair(draw,rect)
    xmin,xmax,ymin,ymax=states[-1].bounds;x0,y0,x1,y1=rect;px=x0+(punch[0]-xmin)/(xmax-xmin)*(x1-x0);py=y1-(punch[1]-ymin)/(ymax-ymin)*(y1-y0);dot(draw,px,py,max(7,min(x1-x0,y1-y0)*.06));draw.text(((final_box[0]+3)*AA,(final_box[1]+1)*AA),'Punch',font=font(9*AA),fill=EDGE)
    caption=font(6*AA);cx=(final_box[0]+final_box[2])/2;draw.text((cx*AA,133*AA),'(full-size view)',font=caption,fill=GUIDE,anchor='mm');draw.text((cx*AA,141*AA),'fully folded sheet',font=caption,fill=GUIDE,anchor='mm')
    divider,panels,boxes=render_layout(size);draw.line((10*AA,divider*AA,(w-10)*AA,divider*AA),fill=(85,89,90),width=2)
    for candidate,panel,box in zip(candidates,panels,boxes):
        x0,y0,x1,y1=panel;draw.text(((x0+8)*AA,(box[1]+2)*AA),candidate['choice_label'],fill=EDGE,font=label);draw.rectangle(tuple(v*AA for v in box),fill=PAPER,outline=EDGE,width=2*AA);crosshair(draw,box);diameter=max(7,(box[2]-box[0])*.055)
        for point in candidate['hole_positions']:
            hx,hy=original_to_box(point,box);dot(draw,hx,hy,diameter)
    im.resize((w,h),Image.Resampling.LANCZOS).save(path,'PNG')

def rerender_dataset(root):
    root=Path(root);rows=[json.loads(line) for line in (root/'annotations.jsonl').open(encoding='utf8')]
    for i,row in enumerate(rows,1):
        states=simulate_folds(row['fold_sequence']);render(root/row['image_path'],tuple(row['canvas_size']),row['fold_sequence'],states,tuple(row['punch_position']),row['candidates'])
        if i%250==0 or i==len(rows):print(f'Re-rendered {i}/{len(rows)}',flush=True)

def questions(iid,row,rng):
    qs=[{'question_id':iid+'_q1','question_text':'How many fold steps are shown before the paper is punched?','question_type':'fold_count','ground_truth':str(row['num_folds']),'answer_format':'numeric','difficulty_level':1},{'question_id':iid+'_q2','question_text':'How many holes will appear when the paper is fully unfolded?','question_type':'unfolded_hole_count','ground_truth':str(row['num_holes']),'answer_format':'numeric','difficulty_level':2},{'question_id':iid+'_q3','question_text':'Which of the four unfolded patterns (A, B, C, D) correctly shows where the holes will appear? Answer with the letter.','question_type':'correct_pattern_choice','ground_truth':row['correct_answer_choice'],'answer_format':'letter','difficulty_level':3}]
    kind=rng.choice(('positions','count','half'))
    if kind=='positions':q={'question_text':'Which candidate has the correct number of holes but in the wrong positions?','question_type':'wrong_positions_choice','ground_truth':next(c['choice_label'] for c in row['candidates'] if c['error_type']=='wrong_positions'),'answer_format':'letter'}
    elif kind=='count':q={'question_text':'Which candidate has the wrong total number of holes?','question_type':'wrong_count_choice','ground_truth':next(c['choice_label'] for c in row['candidates'] if c['error_type']=='wrong_count'),'answer_format':'letter'}
    else:q={'question_text':"If the last fold were removed, would the unfolded hole count be 'exactly half' or have a 'different relationship'?",'question_type':'remove_last_fold','ground_truth':'exactly half','answer_format':'short_text'}
    qs.append({'question_id':iid+'_q4','difficulty_level':4,**q})
    if int(iid[-4:])%3:q5={'question_text':'If one additional fold were made and the punch stayed away from the new crease, how many holes would appear after fully unfolding?','question_type':'additional_fold_hole_count','ground_truth':str(row['num_holes']*2),'answer_format':'numeric'}
    else:q5={'question_text':"If the last fold were removed, would the unfolded hole count be 'exactly half' or have a 'different relationship'?",'question_type':'remove_last_fold','ground_truth':'exactly half','answer_format':'short_text'}
    qs.append({'question_id':iid+'_q5','difficulty_level':5,**q5});return qs

def generate_one(i,images):
    rng=random.Random(i);size=(rng.randint(550,650),rng.randint(400,450));num_folds=2 if i%2 else 3;sequence=generate_sequence(num_folds,rng);states=simulate_folds(sequence);xmin,xmax,ymin,ymax=states[-1].bounds;punch=(round(rng.uniform(xmin+.35*(xmax-xmin),xmax-.35*(xmax-xmin)),6),round(rng.uniform(ymin+.35*(ymax-ymin),ymax-.35*(ymax-ymin)),6));correct=states[-1].punch_origins(punch)
    assert len(correct)==2**num_folds;correct_label=LETTERS[(i-1)%4];candidates=make_candidates(correct,states[-1],punch,correct_label,rng);iid=f'fold_punch_{i:04d}';render(images/f'{iid}.png',size,sequence,states,punch,candidates)
    row={'id':iid,'dataset_version':DATASET_VERSION,'image_path':f'images/{iid}.png','canvas_size':list(size),'coordinate_frame':'normalized_original_sheet_xy','minimum_distractor_displacement':MIN_DISTRACTOR_DISPLACEMENT,'num_folds':num_folds,'fold_sequence':sequence,'punch_position':list(punch),'final_folded_bounds':list(states[-1].bounds),'unfolded_hole_positions':[list(p) for p in correct],'num_holes':len(correct),'correct_answer_choice':correct_label,'candidates':candidates,'seed':i,'difficulty_score':round(.42+.18*(num_folds-2)+.04*len(set(f['axis'] for f in sequence)),4)};row['questions']=questions(iid,row,rng);return row

def generate_dataset(n,output_dir,sample=False):
    root=Path(output_dir);images=root/'images';images.mkdir(parents=True,exist_ok=True);count=5 if sample else n
    with (root/'annotations.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for i in range(1,count+1):
            f.write(json.dumps(generate_one(i,images),sort_keys=True,separators=(',',':'))+'\n')
            if i%250==0 or i==count:print(f'Generated {i}/{count}',flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3000);p.add_argument('--output-dir',default='.');p.add_argument('--sample',action='store_true');p.add_argument('--rerender-only',action='store_true');a=p.parse_args();rerender_dataset(a.output_dir) if a.rerender_only else generate_dataset(a.n,a.output_dir,a.sample)
if __name__=='__main__':main()
