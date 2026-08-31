from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"};FIELDS=["dataset_version","difficulty_score","total_circle_count","total_overlapping_pairs","max_stack_depth","overlap_density","seed"]
def main():
 p=argparse.ArgumentParser();p.add_argument("annotations",type=Path);a=p.parse_args();rows=[];images=0;bad=[]
 for line in a.annotations.read_text(encoding="utf-8").splitlines():
  if not line:continue
  r=json.loads(line);images+=1
  if len(r["questions"])!=5:bad.append(r["id"])
  meta=json.dumps({k:r[k] for k in FIELDS},sort_keys=True,separators=(",",":"))
  for q in r["questions"]:rows.append({"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(r["image_path"]).name,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"]),"answer_format":json.dumps(q["answer_format"],sort_keys=True,separators=(",",":")) if isinstance(q["answer_format"],dict) else str(q["answer_format"]),"metadata":meta})
 out=a.annotations.parent;cols=["question_id","task","image","prompt","groundtruth","answer_format","metadata"]
 with (out/"dataset_final.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=cols,lineterminator="\n");w.writeheader();w.writerows(rows)
 with (out/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as f:
  for r in rows:f.write(json.dumps(r,separators=(",",":"))+"\n")
 with (out/"question_set.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=["question_id","task","image","prompt"],lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in rows)
 with (out/"answer_key.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=["question_id","task","image","prompt","groundtruth","answer_format"],lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in rows)
 counts=Counter(r["task"] for r in rows);print(f"Images: {images}\nRows: {len(rows)}\nExpected: {5*images}\nImages without 5 questions: {len(bad)}");[print(f"{x}: {counts[x]}") for x in TASKS.values()];assert len(rows)==5*images and not bad;print("Sanity check: PASS")
if __name__=="__main__":main()
