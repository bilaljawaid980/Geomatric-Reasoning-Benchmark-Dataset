"""Flatten FBD annotations into public and private question tables."""
import csv,json
from collections import Counter
from pathlib import Path

TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
META=("difficulty_score","scenario_type","preset","physics_parameters","net_force_magnitude","resulting_acceleration_m_s2","is_equilibrium","seed")
def clean(value):return json.dumps(value,ensure_ascii=False,separators=(",",":"),sort_keys=True) if isinstance(value,(dict,list)) else str(value)
def write(path,fields,rows):
 with path.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
def main():
 root=Path(__file__).resolve().parent;records=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x];public=[];private=[];final=[];counts=Counter()
 for row in records:
  if len(row.get("questions",[]))!=5:raise ValueError(f"{row.get('id')}: expected five questions")
  metadata=json.dumps({k:row.get(k) for k in META},ensure_ascii=False,separators=(",",":"),sort_keys=True);image=Path(row["image_path"]).name
  for q in row["questions"]:
   task=TASKS[q["difficulty_level"]];base={"question_id":q["question_id"],"task":task,"image":image,"prompt":q["question_text"]};truth=clean(q["ground_truth"]);fmt=clean(q["answer_format"])
   public.append(base);private.append({**base,"groundtruth":truth,"answer_format":fmt});final.append({"task":task,"image":image,"prompt":q["question_text"],"groundtruth":truth,"metadata":metadata});counts[task]+=1
 write(root/"question_set.csv",["question_id","task","image","prompt"],public);write(root/"answer_key.csv",["question_id","task","image","prompt","groundtruth","answer_format"],private);write(root/"dataset_final.csv",["task","image","prompt","groundtruth","metadata"],final)
 with (root/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for row in final:h.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
 expected=len(records)*5
 if not(len(public)==len(private)==len(final)==expected):raise ValueError("flatten row-count mismatch")
 print(f"Images: {len(records)}\nRows written: {expected}");[print(f"  {task}: {counts[task]}") for task in TASKS.values()];print("Sanity check: PASS")
if __name__=="__main__":main()
