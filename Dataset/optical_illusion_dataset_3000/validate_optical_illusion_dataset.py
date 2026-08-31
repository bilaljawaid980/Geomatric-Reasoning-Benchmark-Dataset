"""Independently validate optical-illusion geometry, labels, tables, and PNG targets."""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
from PIL import Image,ImageChops,ImageStat

BACKGROUND=(253,250,244);TARGET=(23,74,105)
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}

def half_up(value):return (2*value.numerator+value.denominator)//(2*value.denominator)
def primitive_value(g):return g["x2"]-g["x1"] if g["kind"]=="line" else g["diameter"]
def actual_relation(a,b):return "equal" if a==b else ("A" if a>b else "B")
def counterfactual(appearance,actual):
 changed=actual=="equal" or appearance!=actual;truth="actually equal" if actual=="equal" else f"element {actual} is actually bigger";return f"{'yes' if changed else 'no'}; {truth}"
def hardcoded_appearance(row):
 contexts=row["construction"]["contexts"]
 if row["illusion_type"]=="muller_lyer":matches=[label for label in ("A","B") if contexts[label]=="outward"]
 elif row["illusion_type"]=="ponzo":
  matches=[label for label in ("A","B") if contexts[label]=="near_convergence"]
  ys={label:row["construction"]["elements"][label]["y"] for label in ("A","B")}
  if matches and ys[matches[0]]!=min(ys.values()):return None
 else:matches=[label for label in ("A","B") if contexts[label]=="small_surrounds"]
 return matches[0] if len(matches)==1 else None
def expected_questions(row):
 a=primitive_value(row["construction"]["elements"]["A"]);b=primitive_value(row["construction"]["elements"]["B"]);actual=actual_relation(a,b);appearance=hardcoded_appearance(row);pct=Fraction(abs(a-b)*100,min(a,b)) if a!=b else Fraction(0)
 return [("comparison_element_count","2","integer"),("contextual_apparent_size",appearance,"A or B"),("actual_size_comparison",actual,"equal, A, or B"),("true_size_percent_difference",str(half_up(pct)),"integer percentage in curly brackets"),("remove_illusion_context",counterfactual(appearance,actual),"yes/no; actual relation")]
def close(pixel,target,tolerance=10):return max(abs(pixel[i]-target[i]) for i in range(3))<=tolerance
def color_near(image,point,radius=5):
 x0,y0=(round(v) for v in point)
 return any(close(image.getpixel((x,y)),TARGET) for y in range(max(0,y0-radius),min(image.height,y0+radius+1)) for x in range(max(0,x0-radius),min(image.width,x0+radius+1)))
def png_issues(image,row):
 issues=[];iid=row["id"]
 if image.size!=tuple(row["canvas_size"]):issues.append(f"{iid}: PNG size")
 if sum(ImageStat.Stat(image).var)<80:issues.append(f"{iid}: blank/low-variance PNG")
 if not close(image.getpixel((4,4)),BACKGROUND,5):issues.append(f"{iid}: background")
 for label in ("A","B"):
  g=row["construction"]["elements"][label]
  if g["kind"]=="line":
   for fraction in (.08,.3,.5,.7,.92):
    if not color_near(image,(g["x1"]+(g["x2"]-g["x1"])*fraction,g["y"]),6):issues.append(f"{iid}: PNG target {label} missing at {fraction}");break
  else:
   radius=g["diameter"]/2
   for point in ((g["cx"]-radius,g["cy"]),(g["cx"]+radius,g["cy"]),(g["cx"],g["cy"]-radius),(g["cx"],g["cy"]+radius)):
    if not color_near(image,point,7):issues.append(f"{iid}: PNG circle {label} outline missing");break
 return issues
def read_csv(path):
 with path.open("r",encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))
def table_issues(root,records):
 issues=[];paths=[root/"question_set.csv",root/"answer_key.csv",root/"dataset_final.csv"]
 if not all(path.exists() for path in paths):return ["flattened tables missing"]
 public,private,final=map(read_csv,paths);expected=[(row,q) for row in records for q in row["questions"]]
 if not len(public)==len(private)==len(final)==len(expected):return ["flattened row-count mismatch"]
 if "groundtruth" in public[0] or "answer_format" in public[0]:issues.append("public table leaks private fields")
 for i,((row,q),pub,priv,flat) in enumerate(zip(expected,public,private,final),1):
  base={"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(row["image_path"]).name,"prompt":q["question_text"]}
  if any(pub.get(k)!=v for k,v in base.items()):issues.append(f"public row {i}")
  if any(priv.get(k)!=v for k,v in base.items()) or priv.get("groundtruth")!=str(q["ground_truth"]):issues.append(f"answer row {i}")
  if flat.get("groundtruth")!=str(q["ground_truth"]):issues.append(f"final row {i}")
 return issues
def validate(root):
 root=Path(root);records=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];issues=[];types=Counter();equal=defaultdict(Counter);alignment=defaultdict(Counter)
 for position,row in enumerate(records,1):
  iid=row["id"];types[row["illusion_type"]]+=1;equal[row["illusion_type"]][row["are_actually_equal"]]+=1
  try:
   a=primitive_value(row["construction"]["elements"]["A"]);b=primitive_value(row["construction"]["elements"]["B"]);actual=actual_relation(a,b);appearance=hardcoded_appearance(row);is_equal=a==b;pct=Fraction(abs(a-b)*100,min(a,b)) if not is_equal else Fraction(0);matches=None if is_equal else actual==appearance
   if row["illusion_type"] not in ("muller_lyer","ponzo","ebbinghaus"):issues.append(f"{iid}: illusion type")
   if row["illusion_type"]=="ebbinghaus":
    for label in ("A","B"):
     target=row["construction"]["elements"][label];context=row["construction"]["contexts"][label];ratio=Fraction(row["construction"]["small_context_ratio_fraction"] if context=="small_surrounds" else row["construction"]["large_context_ratio_fraction"]);cd=float(Fraction(target["diameter"])*ratio);ring=target["diameter"]/2+cd/2+(13 if context=="small_surrounds" else 9);extent=ring+cd/2;canvas=row["canvas_size"][0]
     if target["cx"]-extent<0 or target["cx"]+extent>canvas or target["cy"]-extent<0 or target["cy"]+extent>canvas:issues.append(f"{iid}: clipped Ebbinghaus context {label}")
   if appearance not in ("A","B"):issues.append(f"{iid}: invalid directional context")
   if (a,b)!=(row["element_a_true_value"],row["element_b_true_value"]):issues.append(f"{iid}: primitive measurement")
   if row["are_actually_equal"]!=is_equal or row["matches_illusion_direction"]!=matches:issues.append(f"{iid}: equality/alignment")
   if row["illusion_appears_larger_element"]!=appearance:issues.append(f"{iid}: illusion direction")
   expected_word="longer" if row["illusion_type"]!="ebbinghaus" else "bigger"
   if row["illusion_direction"]!=f"{appearance}_appears_{expected_word}":issues.append(f"{iid}: direction text")
   if Fraction(row["percent_difference_fraction"])!=pct or abs(row["percent_difference"]-float(pct))>1e-10:issues.append(f"{iid}: percent difference")
   if not is_equal:alignment[row["illusion_type"]][matches]+=1
   expected=expected_questions(row)
   if len(row["questions"])!=5 or [q["difficulty_level"] for q in row["questions"]]!=[1,2,3,4,5]:issues.append(f"{iid}: question schema")
   else:
    for q,want in zip(row["questions"],expected):
     if (q["question_type"],str(q["ground_truth"]))!=want[:2]:issues.append(f"{q['question_id']}: ground truth")
    level2=row["questions"][1]["question_text"].lower()
    if "typical human viewer" not in level2 or "perceive" not in level2:issues.append(f"{iid}: Level 2 human-perception frame is not explicit")
  except Exception as exc:issues.append(f"{iid}: exception {exc}")
  path=root/row["image_path"]
  if not path.exists():issues.append(f"{iid}: missing PNG")
  else:
   with Image.open(path) as source:image=source.convert("RGB");image.load()
   issues.extend(png_issues(image,row))
  if position%500==0:print(f"Validated {position}/{len(records)}",flush=True)
 if len(records)==3000:
  if types!={"muller_lyer":1050,"ponzo":1050,"ebbinghaus":900}:issues.append(f"type balance {dict(types)}")
  for kind,total in types.items():
   if equal[kind][True]!=total//2 or equal[kind][False]!=total//2:issues.append(f"{kind}: equal balance")
   if abs(alignment[kind][True]-alignment[kind][False])>1:issues.append(f"{kind}: alignment balance")
 issues.extend(table_issues(root,records))
 report={"images_checked":len(records),"questions_checked":sum(len(r["questions"]) for r in records),"mismatches":len(issues),"illusion_type_distribution":dict(types),"equality_distribution":{k:{str(x).lower():y for x,y in v.items()} for k,v in equal.items()},"unequal_alignment_distribution":{k:{str(x).lower():y for x,y in v.items()} for k,v in alignment.items()},"direction_rules":{"muller_lyer":"outward fins appear longer","ponzo":"nearer convergence appears longer","ebbinghaus":"smaller surrounds make center appear bigger"},"issues":issues}
 (root/"validation_metrics.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 lines=["Optical Illusion Dataset Validation Report","="*45,f"Total images checked: {report['images_checked']}",f"Total questions checked: {report['questions_checked']}",f"Total mismatches found: {len(issues)}","",f"Illusion types: {dict(types)}",f"Equality by type: {report['equality_distribution']}",f"Unequal alignment by type: {report['unequal_alignment_distribution']}","","Hard-coded perceptual direction rules:","  Müller-Lyer: outward fins appear longer","  Ponzo: the element nearer convergence appears longer","  Ebbinghaus: smaller surrounds make the center appear bigger","","Issues:"]+([f"  {x}" for x in issues] if issues else ["  None"])+["",f"Summary: {'PASS' if not issues else 'FAIL'}"]
 (root/"validation_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines));return len(issues)
def main():
 p=argparse.ArgumentParser();p.add_argument("root",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();raise SystemExit(1 if validate(a.root) else 0)
if __name__=="__main__":main()
