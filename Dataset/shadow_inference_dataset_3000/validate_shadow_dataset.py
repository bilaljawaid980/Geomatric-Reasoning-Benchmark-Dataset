import argparse,json,math
from collections import Counter
from pathlib import Path
from PIL import Image
BG=(26,26,26);FLOOR_TOP=(58,58,58);FLOOR_BOTTOM=(74,74,74)
def project(o,g,e):
 a=math.radians(o['effective_light_azimuth_degrees']);base=o['width_px']/2;physical=o['height_px']/math.tan(math.radians(e))*.55+base;dx=-math.sin(a)*physical;dy=-(.14+.26*((math.cos(a)+1)/2))*physical;l=math.hypot(dx,dy);return o['position'][0]+dx,g+dy,l,math.degrees(math.atan2(dy,dx)),base
def horizon_for(r):return max(18,round(min([r['ground_y']]+[o['shadow_position'][1]-o['base_radius_px']*.9 for o in r['objects']])-18))
def floor_value(y,horizon,height):
 t=max(0,min(1,(y-horizon)/max(1,height-horizon)));return sum(FLOOR_TOP[k]+(FLOOR_BOTTOM[k]-FLOOR_TOP[k])*t for k in range(3))/3
def pixel_matches_shadow(im,x,y,horizon,radius=3):
 expected=floor_value(y,horizon,im.height);matches=0;total=0
 for yy in range(max(0,round(y)-radius),min(im.height,round(y)+radius+1)):
  for xx in range(max(0,round(x)-radius),min(im.width,round(x)+radius+1)):
   p=im.getpixel((xx,yy));total+=1;chroma=max(p)-min(p);lum=sum(p)/3
   if chroma<=9 and lum<=expected-5:matches+=1
 return matches>=max(1,total//8)
def silhouette(o,g):
 x=o['position'][0];sx,sy=o['shadow_position'];base=o['base_radius_px'];vx=sx-x;vy=sy-g
 if o['type']=='cube':return [(x-base,g),(x+base,g),(sx+base*.62,sy),(sx-base*.62,sy)]
 points=[]
 for k in range(25):
  t=k/24;cx=x+vx*t;cy=g+vy*t;hw=base*.78*math.sin(math.pi*t);points.extend(((cx-hw,cy),(cx+hw,cy)))
 return points
def bucket(a):
 a%=360;return 'front' if a>=315 or a<45 else 'right' if a<135 else 'back' if a<225 else 'left'
def validate(root,limit=None):
 root=Path(root);issues=[];types=Counter();lines=(root/'annotations.jsonl').read_text(encoding='utf8').splitlines()
 if limit is not None:lines=lines[:limit]
 for line in lines:
  r=json.loads(line);iid=r['id'];p=root/r['image_path']
  az=r['light_azimuth_degrees']%360
  if min(abs(az),abs(az-180),abs(az-360))<30-1e-9:issues.append(f'{iid}: forbidden near-axis azimuth {az}')
  if r.get('dataset_version')!='shadow-inference-2.0.0':issues.append(f'{iid}: dataset version mismatch')
  if not p.exists():issues.append(f'{iid}: missing image');continue
  with Image.open(p) as src:
   im=src.convert('RGB')
   if list(im.size)!=r['canvas_size']:issues.append(f'{iid}: canvas mismatch')
  horizon=horizon_for(r)
  if max(abs(im.getpixel((5,5))[k]-BG[k]) for k in range(3))>3:issues.append(f'{iid}: dark sky color mismatch')
  near=im.getpixel((5,min(im.height-2,horizon+10)));bottom=im.getpixel((5,im.height-5))
  if not (max(near)-min(near)<=4 and max(bottom)-min(bottom)<=4 and sum(bottom)>sum(near)>sum(BG)+40):issues.append(f'{iid}: floor gradient mismatch')
  objs=r['objects'];bad=[o['index'] for o in objs if not o['consistent']];expected_bad=[r['inconsistent_object_index']] if r['has_inconsistent_shadow'] else []
  if len(objs)!=r['num_objects']:issues.append(f'{iid}: object count mismatch')
  if bad!=expected_bad:issues.append(f'{iid}: consistency mismatch')
  for o in objs:
   x,y,l,a,base=project(o,r['ground_y'],r['light_elevation_degrees']);sx,sy=o['shadow_position']
   if max(abs(x-sx),abs(y-sy),abs(l-o['shadow_length']),abs(a-o['shadow_screen_angle_degrees']),abs(base-o.get('base_radius_px',-99)))>.08:issues.append(f"{iid}: shadow geometry mismatch {o['index']}")
   ox=o['position'][0];g=r['ground_y'];vx=x-ox;vy=y-g
   center=[(ox+vx*t,g+vy*t) for t in (.12,.28,.48,.68,.86,.96)]
   if sum(pixel_matches_shadow(im,px,py,horizon) for px,py in center)<5:issues.append(f"{iid}: PNG shadow centerline/endpoint mismatch {o['index']}")
   width_sections=[]
   for t in (.35,.5,.65):
    mid=(ox+vx*t,g+vy*t);profile=math.sin(math.pi*t) if o['type']!='cube' else 1;half=base*(.42 if o['type']!='cube' else .34)*profile;width_sections.append(all(pixel_matches_shadow(im,px,py,horizon) for px,py in ((mid[0]-half,mid[1]),(mid[0]+half,mid[1]))))
   if sum(width_sections)<2:issues.append(f"{iid}: PNG shadow width mismatch {o['index']}")
   contacts=[(ox+vx*t,g+vy*t) for t in (.06,.10,.14)]
   if not any(pixel_matches_shadow(im,*point,horizon) for point in contacts):issues.append(f"{iid}: PNG shadow base-contact mismatch {o['index']}")
   if y>g+1e-6:issues.append(f"{iid}: shadow endpoint below ground {o['index']}")
   sil=silhouette(o,g)
   if any(px<2 or px>im.width-2 or py<2 or py>g+1e-6 for px,py in sil):issues.append(f"{iid}: rendered shadow silhouette clipped {o['index']}")
   if min(py for px,py in sil)<horizon-1:issues.append(f"{iid}: shadow extends above rendered floor {o['index']}")
   if abs(sx-o['position'][0])<18:issues.append(f"{iid}: shadow lateral extent below 18px {o['index']}")
  qs=r.get('questions',[])
  if len(qs)!=5 or [q.get('difficulty_level') for q in qs]!=[1,2,3,4,5]:issues.append(f'{iid}: question structure mismatch');continue
  for q in qs:
   t=q['question_type'];types[t]+=1
   if t=='object_count':e=str(len(objs))
   elif t=='same_light_source':e='no' if bad else 'yes'
   elif t=='light_direction_bucket':e=bucket(r['light_azimuth_degrees'])
   elif t=='longest_shadow':e=max(objs,key=lambda o:o['shadow_length'])['color']
   elif t=='light_height_class':e='high' if r['light_elevation_degrees']>45 else 'low'
   elif t=='inconsistent_shadow_object':e=objs[r['inconsistent_object_index']]['color']
   elif t=='elevation_nearest_15':e=str(int(math.floor(r['light_elevation_degrees']/15+.5)*15))
   elif t=='opposite_azimuth_length_change':e='same'
   elif t=='raise_light_elevation':e='shorter'
   else:issues.append(f'{iid}: unknown type {t}');continue
   if q['ground_truth']!=e:issues.append(f'{iid}: {t} answer mismatch')
 report=[f'Total images checked: {len(lines)}',f'Total mismatches found: {len(issues)}','Question distribution:']+[f'  {k}: {v}' for k,v in sorted(types.items())]+[f"Summary: {'PASS' if not issues else 'FAIL'}"]+issues;(root/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf8');print('\n'.join(report[:16]));return len(lines),issues
def main():
 p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--limit',type=int);a=p.parse_args();_,x=validate(a.dataset,a.limit);raise SystemExit(bool(x))
if __name__=='__main__':main()
