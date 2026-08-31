"""Flatten optical-illusion annotations into public and private tables."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
META_KEYS=("difficulty_score","illusion_type","element_a_true_value","element_b_true_value","are_actually_equal","illusion_direction","matches_illusion_direction","percent_difference","seed")
def main():
 p=argparse.ArgumentParser();p.add_argument("annotations",nargs="?",type=Path,default=Path(__file__).resolve().parent/"annotations.jsonl");a=p.parse_args();root=a.annotations.parent;records=[json.loads(x) for x in a.annotations.read_text(encoding="utf-8").splitlines() if x];final=[];public=[];private=[];counts=Counter()
 for row in records:
  if len(row["questions"])!=5:raise ValueError(f"{row['id']}: expected five questions")
  metadata=json.dumps({key:row.get(key) for key in META_KEYS},ensure_ascii=False,separators=(",",":"));image=Path(row["image_path"]).name
  for q in row["questions"]:
   task=TASKS[q["difficulty_level"]];base={"question_id":q["question_id"],"task":task,"image":image,"prompt":q["question_text"]};public.append(base);private.append({**base,"groundtruth":str(q["ground_truth"]),"answer_format":q["answer_format"]});final.append({"task":task,"image":image,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"]),"metadata":metadata});counts[task]+=1
 def write(name,fields,rows):
  with (root/name).open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
 write("question_set.csv",["question_id","task","image","prompt"],public);write("answer_key.csv",["question_id","task","image","prompt","groundtruth","answer_format"],private);write("dataset_final.csv",["task","image","prompt","groundtruth","metadata"],final)
 with (root/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for row in final:h.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
 if len(final)!=5*len(records):raise ValueError("flatten row-count mismatch")
 print(f"Images: {len(records)}\nRows written: {len(final)}\nTasks: {dict(counts)}\nSanity check: PASS")
if __name__=="__main__":main()
