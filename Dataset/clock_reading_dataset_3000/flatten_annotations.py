"""Flatten clock-reading annotations into suite tables."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
def main():
 p=argparse.ArgumentParser();p.add_argument("annotations",nargs="?",type=Path);a=p.parse_args();path=a.annotations or Path(__file__).resolve().parent/"annotations.jsonl";source=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x];rows=[]
 for item in source:
  metadata=json.dumps({k:item[k] for k in ("difficulty_score","hour","minute","hour_angle","minute_angle","angle_between_hands","seed")},sort_keys=True,separators=(",",":"))
  for q in item["questions"]:rows.append({"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(item["image_path"]).name,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"]),"metadata":metadata})
 output=path.parent;final=["task","image","prompt","groundtruth","metadata"]
 with (output/"dataset_final.csv").open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=final,lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in final} for r in rows)
 with (output/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for r in rows:h.write(json.dumps({k:r[k] for k in final},ensure_ascii=False,separators=(",",":"))+"\n")
 for name,cols in (("question_set.csv",["question_id","task","image","prompt"]),("answer_key.csv",["question_id","task","image","prompt","groundtruth"])):
  with (output/name).open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=cols,lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in cols} for r in rows)
 counts=Counter(r["task"] for r in rows);print(f"Images: {len(source)}\nRows written: {len(rows)}");[print(f"  {task}: {counts[task]}") for task in TASKS.values()]
 if len(rows)!=5*len(source):raise SystemExit("row-count check failed")
 print("Sanity check: PASS")
if __name__=="__main__":main()
