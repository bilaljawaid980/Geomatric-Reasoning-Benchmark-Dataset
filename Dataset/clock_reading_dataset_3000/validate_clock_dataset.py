"""Independent metadata, question-table, and PNG validator for clock reading."""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter
from fractions import Fraction
from pathlib import Path
from PIL import Image,ImageStat

CENTER=(300,300);HOUR_LENGTH=120;MINUTE_LENGTH=178;HOUR_RGB=(47,111,104);MINUTE_RGB=(180,62,53)
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}

def fresh_angles(hour,minute):return Fraction((hour%12)*30)+Fraction(minute,2),Fraction(minute*6)
def fresh_smaller(a,b):
 d=abs(a-b)%360;return min(d,Fraction(360)-d)
def half_up(v):return (2*v.numerator+v.denominator)//(2*v.denominator)
def advance(hour,minute):
 total=((hour%12)*60+minute+20)%720;h=total//60;return (12 if h==0 else h),total%60
def endpoint(angle,length,t=1):
 rad=math.radians(float(angle));return (CENTER[0]+length*t*math.sin(rad),CENTER[1]-length*t*math.cos(rad))
def color_near(image,rgb,point,radius):
 x0,y0=map(lambda v:int(round(v)),point)
 for y in range(max(0,y0-radius),min(image.height,y0+radius+1)):
  for x in range(max(0,x0-radius),min(image.width,x0+radius+1)):
   # LANCZOS downsampling can shift a solid channel by one or two values.
   # A tight per-channel tolerance still distinguishes the two hand colors
   # from each other, the face, ticks, numerals, and pivot.
   pixel=image.getpixel((x,y))
   if max(abs(pixel[channel]-rgb[channel]) for channel in range(3))<=3:return True
 return False
def validate_rendered_hands(image,row):
 issues=[];iid=row["id"];ha,ma=fresh_angles(row["hour"],row["minute"])
 for name,angle,length,rgb,radius in (("hour",ha,HOUR_LENGTH,HOUR_RGB,7),("minute",ma,MINUTE_LENGTH,MINUTE_RGB,4)):
  for fraction in (.35,.65,.92):
   if not color_near(image,rgb,endpoint(angle,length,fraction),radius):issues.append(f"{iid}: PNG {name} hand misses expected angle at {fraction:.2f} length")
  if not color_near(image,rgb,endpoint(angle,length,.98),radius+1):issues.append(f"{iid}: PNG {name} endpoint/length mismatch")
 return issues
def expected_answer(row,q):
 hour,minute=row["hour"],row["minute"];ha,ma=fresh_angles(hour,minute);kind=q["question_type"]
 if kind=="hour_recently_passed":return str(hour)
 if kind=="minute_before_after_six":return "before" if minute<30 else "after"
 if kind=="exact_clock_time":return f"{hour:02d}:{minute:02d}"
 if kind=="smaller_hand_angle":return str(half_up(fresh_smaller(ha,ma)))
 if kind=="angle_after_twenty_minutes":
  nh,nm=advance(hour,minute);nha,nma=fresh_angles(nh,nm);return str(half_up(fresh_smaller(nha,nma)))
 raise ValueError(kind)
def read_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def validate_tables(root,rows):
 issues=[];expected=[]
 for row in rows:
  for q in row["questions"]:expected.append({"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"])})
 question=read_csv(root/"question_set.csv");answer=read_csv(root/"answer_key.csv");final=read_csv(root/"dataset_final.csv")
 if list(question[0])!=["question_id","task","image","prompt"]:issues.append("tables: bad question_set columns")
 if list(answer[0])!=["question_id","task","image","prompt","groundtruth"]:issues.append("tables: bad answer_key columns")
 if not(len(question)==len(answer)==len(final)==len(expected)):return issues+[f"tables: row count mismatch {len(question)}/{len(answer)}/{len(final)}/{len(expected)}"]
 seen=set()
 for i,(want,q,a,f) in enumerate(zip(expected,question,answer,final),1):
  if want["question_id"] in seen:issues.append(f"tables: duplicate {want['question_id']}")
  seen.add(want["question_id"])
  for key in ("question_id","task","image","prompt"):
   if q.get(key)!=want[key]:issues.append(f"tables: question row {i} {key} mismatch")
   if a.get(key)!=want[key]:issues.append(f"tables: answer row {i} {key} mismatch")
  if a.get("groundtruth")!=want["groundtruth"]:issues.append(f"tables: answer ground truth mismatch {want['question_id']}")
  for key in ("task","image","prompt","groundtruth"):
   if f.get(key)!=want[key]:issues.append(f"tables: final row {i} {key} mismatch")
 return issues
def validate(root):
 rows=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];issues=[];relations=Counter();hours=Counter();minutes=Counter();qtypes=Counter();rollovers=0
 for row in rows:
  iid=row.get("id","<missing>");hour,minute=row["hour"],row["minute"];hours[hour]+=1;minutes[minute]+=1;relations[row["minute_relation_to_six"]]+=1
  try:
   if not 1<=hour<=12 or not 0<=minute<=59 or minute==30:issues.append(f"{iid}: invalid/ambiguous time")
   ha,ma=fresh_angles(hour,minute);angle=fresh_smaller(ha,ma)
   if angle<12:issues.append(f"{iid}: hands are too close for reliable visual separation")
   if Fraction(row["hour_angle_fraction"])!=ha or Fraction(row["minute_angle_fraction"])!=ma or Fraction(row["angle_between_hands_fraction"])!=angle:issues.append(f"{iid}: stored original angles mismatch")
   nh,nm=advance(hour,minute);nha,nma=fresh_angles(nh,nm);nangle=fresh_smaller(nha,nma);stored=row["after_twenty_minutes"]
   if stored["hour"]!=nh or stored["minute"]!=nm or Fraction(stored["hour_angle_fraction"])!=nha or Fraction(stored["minute_angle_fraction"])!=nma or Fraction(stored["angle_between_hands_fraction"])!=nangle:issues.append(f"{iid}: stored +20 minute angles mismatch")
   if nm<minute:rollovers+=1
   questions=row.get("questions",[])
   if len(questions)!=5 or [q.get("difficulty_level") for q in questions]!=[1,2,3,4,5]:issues.append(f"{iid}: expected five ordered questions")
   else:
    for q in questions:
     qtypes[q["question_type"]]+=1;expected=expected_answer(row,q)
     if str(q["ground_truth"])!=expected:issues.append(f"{iid}: {q['question_type']} {q['ground_truth']!r} != {expected!r}")
  except Exception as exc:issues.append(f"{iid}: validation exception ({exc})")
  path=root/row["image_path"]
  if not path.exists():issues.append(f"{iid}: missing PNG")
  else:
   try:
    with Image.open(path) as image:
     image.load();image=image.convert("RGB")
     if image.size!=(600,600):issues.append(f"{iid}: expected 600x600 PNG")
     if sum(ImageStat.Stat(image).var)<100:issues.append(f"{iid}: PNG appears blank")
     issues.extend(validate_rendered_hands(image,row))
   except Exception as exc:issues.append(f"{iid}: unreadable PNG ({exc})")
 if len(rows)>=3000:
  if relations!={"before":1500,"after":1500}:issues.append(f"dataset: relation imbalance {relations}")
  if set(hours)!=set(range(1,13)):issues.append("dataset: missing hour values")
  if set(minutes)!=set(range(60))-{30}:issues.append("dataset: minute coverage mismatch")
  for name in ("dataset_final.csv","question_set.csv","answer_key.csv"):
   if len(read_csv(root/name))!=15000:issues.append(f"dataset: {name} row count mismatch")
  issues.extend(validate_tables(root,rows))
 report=["Clock Reading Dataset Validation Report","=======================================",f"Total images checked: {len(rows)}",f"Total questions checked: {sum(qtypes.values())}",f"Total mismatches found: {len(issues)}",f"Minute rollovers checked: {rollovers}","","Minute relation distribution:",*[f"  {k}: {v}" for k,v in sorted(relations.items())],"","Hour distribution:",*[f"  {k}: {v}" for k,v in sorted(hours.items())],"","Question types:",*[f"  {k}: {v}" for k,v in sorted(qtypes.items())],"","Issues:",*(issues if issues else ["  None"]),"","Summary: "+("PASS" if not issues else "FAIL")]
 text="\n".join(report)+"\n";(root/"validation_report.txt").write_text(text,encoding="utf-8");print(text);return not issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();raise SystemExit(0 if validate(a.dataset) else 1)
if __name__=="__main__":main()
