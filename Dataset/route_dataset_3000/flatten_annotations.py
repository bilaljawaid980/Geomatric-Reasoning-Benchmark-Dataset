"""Flatten image-level route annotations into one row per question."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path

COLUMNS=["task","image","prompt","groundtruth","metadata"]
TASK_BY_LEVEL={1:"Image Description",2:"Route Counting",3:"Comparative Reasoning",4:"Compound Reasoning"}
META_FIELDS=["difficulty_score","num_routes","num_endpoints","colors_used","crossing_count","line_width_px","seed"]

def clean_groundtruth(value,question_type):
 """Convert structured answers into concise, human-checkable plain strings."""
 if value is None:return ""
 if isinstance(value,list):return ", ".join(str(x) for x in value)
 if isinstance(value,dict):
  if "letter" in value:return str(value["letter"])
  if "pair" in value:return str(value["pair"])
  if "letters" in value:return ", ".join(str(x) for x in value["letters"])
  if "pairs" in value:return ", ".join(str(x) for x in value["pairs"])
  return ", ".join(f"{k}: {value[k]}" for k in sorted(value))
 if isinstance(value,bool):return "yes" if value else "no"
 return str(value)

def flatten(annotation_path:Path,output_dir:Path):
 rows=[];image_count=0;question_counts={};bad_question_counts=[]
 with annotation_path.open(encoding="utf-8") as f:
  for line_number,line in enumerate(f,1):
   if not line.strip():continue
   entry=json.loads(line);image_count+=1;questions=entry.get("questions",[]);question_counts[entry["id"]]=len(questions)
   if len(questions)!=4:bad_question_counts.append((entry["id"],len(questions)))
   metadata=json.dumps({k:entry.get(k) for k in META_FIELDS},sort_keys=True,separators=(",",":"),ensure_ascii=False)
   image=Path(entry["image_path"]).name
   for q in questions:
    typ=q.get("question_type","");level=q.get("difficulty_level");rows.append({"task":TASK_BY_LEVEL.get(level,f"Unknown Level {level}"),"image":image,"prompt":q.get("question_text",""),"groundtruth":clean_groundtruth(q.get("ground_truth"),typ),"metadata":metadata})
 output_dir.mkdir(parents=True,exist_ok=True);csv_path=output_dir/"dataset_final.csv";jsonl_path=output_dir/"dataset_final.jsonl"
 with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=COLUMNS,lineterminator="\n");w.writeheader();w.writerows(rows)
 with jsonl_path.open("w",encoding="utf-8",newline="\n") as f:
  for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
 # Sanity check by re-reading both outputs rather than trusting in-memory rows.
 with csv_path.open(encoding="utf-8-sig",newline="") as f:csv_rows=list(csv.DictReader(f))
 with jsonl_path.open(encoding="utf-8") as f:jsonl_rows=[json.loads(x) for x in f if x.strip()]
 expected=sum(question_counts.values());strict_expected=4*image_count;tasks=Counter(r["task"] for r in csv_rows)
 errors=[]
 if len(csv_rows)!=expected:errors.append(f"CSV has {len(csv_rows)} rows; expected {expected}")
 if len(jsonl_rows)!=expected:errors.append(f"JSONL has {len(jsonl_rows)} rows; expected {expected}")
 if [r.keys() for r in csv_rows[:1]] and list(csv_rows[0].keys())!=COLUMNS:errors.append("CSV columns differ from required order")
 print(f"Images read: {image_count}");print(f"Total rows written: {len(rows)}")
 for level in range(1,5):print(f"{TASK_BY_LEVEL[level]}: {tasks[TASK_BY_LEVEL[level]]}")
 print(f"Expected rows (4 × images): {strict_expected}")
 if bad_question_counts:
  print(f"Images without exactly 4 questions: {len(bad_question_counts)}")
  for iid,n in bad_question_counts:print(f"  {iid}: {n} question(s)")
 else:print("Images without exactly 4 questions: 0")
 print(f"CSV reread rows: {len(csv_rows)}");print(f"JSONL reread rows: {len(jsonl_rows)}")
 if errors:raise RuntimeError("; ".join(errors))
 if not bad_question_counts and expected!=strict_expected:raise RuntimeError("row count is not exactly 4 × image count")
 print("Sanity check: PASS");return csv_path,jsonl_path

def main():
 p=argparse.ArgumentParser();p.add_argument("annotations",type=Path);p.add_argument("--output-dir",type=Path,default=None);a=p.parse_args();out=a.output_dir or a.annotations.parent;csv_path,jsonl_path=flatten(a.annotations,out);print(f"CSV: {csv_path}");print(f"JSONL: {jsonl_path}")
if __name__=="__main__":main()
