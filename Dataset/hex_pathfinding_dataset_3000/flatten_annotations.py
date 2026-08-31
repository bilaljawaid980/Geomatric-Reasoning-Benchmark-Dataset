import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"};META_KEYS=("difficulty_score","grid_radius","num_hole_tiles","hole_density","shortest_path_length","num_alternate_shortest_paths","seed")
def main():
 p=argparse.ArgumentParser();p.add_argument("annotations",nargs="?",type=Path,default=Path(__file__).resolve().parent/"annotations.jsonl");a=p.parse_args();root=a.annotations.parent;rows=[json.loads(x) for x in a.annotations.read_text().splitlines() if x];public=[];private=[];final=[];counts=Counter()
 for row in rows:
  meta=json.dumps({k:row.get(k) for k in META_KEYS},separators=(",",":"));image=Path(row["image_path"]).name
  for q in row["questions"]:
   task=TASKS[q["difficulty_level"]];base={"question_id":q["question_id"],"task":task,"image":image,"prompt":q["question_text"]};public.append(base);private.append({**base,"groundtruth":str(q["ground_truth"]),"answer_format":q["answer_format"]});final.append({"task":task,"image":image,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"]),"metadata":meta});counts[task]+=1
 def write(name,fields,data):
  with (root/name).open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(data)
 write("question_set.csv",["question_id","task","image","prompt"],public);write("answer_key.csv",["question_id","task","image","prompt","groundtruth","answer_format"],private);write("dataset_final.csv",["task","image","prompt","groundtruth","metadata"],final)
 with (root/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as h:
  for row in final:h.write(json.dumps(row,separators=(",",":"))+"\n")
 if len(final)!=5*len(rows):raise ValueError("row count")
 print(f"Images: {len(rows)}\nRows written: {len(final)}\nTasks: {dict(counts)}\nSanity check: PASS")
if __name__=="__main__":main()
