"""Flatten v7 nested-polygon annotations without exposing raw generation metadata."""
import csv,json
from pathlib import Path

TASKS={1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}
META_KEYS=("difficulty_score","rotation_mode","reduction_mode","step_reduction_factors","reduction_factor_span","factor_progression_direction","extrapolation_reduction_factor","line_width_px","seed","parameter_seed","symmetry_modulus_degrees","cumulative_rotation_degrees","cumulative_rotation_fraction","target_cumulative_rotation_degrees","generation_attempt","generation_rejections")

def flatten(annotations):
 annotations=Path(annotations);root=annotations.parent
 records=[json.loads(line) for line in annotations.read_text(encoding="utf-8").splitlines() if line]
 final=[];public=[];private=[]
 for record in records:
  metadata=json.dumps({key:record.get(key) for key in META_KEYS},ensure_ascii=False,separators=(",",":"));image=Path(record["image_path"]).name
  for question in record["questions"]:
   base={"dataset_version":record["dataset_version"],"question_id":question["question_id"],"task":TASKS[question["difficulty_level"]],"image":image,"prompt":question["question_text"]};groundtruth=str(question["ground_truth"])
   public.append(base);private.append({**base,"groundtruth":groundtruth,"answer_format":question["answer_format"]});final.append({"dataset_version":record["dataset_version"],"task":base["task"],"image":image,"prompt":base["prompt"],"groundtruth":groundtruth,"metadata":metadata})
 def write(name,fields,rows):
  with (root/name).open("w",encoding="utf-8-sig",newline="") as handle:
   writer=csv.DictWriter(handle,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows(rows)
 write("question_set.csv",["dataset_version","question_id","task","image","prompt"],public)
 write("answer_key.csv",["dataset_version","question_id","task","image","prompt","groundtruth","answer_format"],private)
 write("dataset_final.csv",["dataset_version","task","image","prompt","groundtruth","metadata"],final)
 with (root/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as handle:
  for row in final:handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
 if len(final)!=5*len(records):raise ValueError("v7 flattened row count mismatch")
 for path in (root/"question_set.csv",root/"answer_key.csv",root/"dataset_final.csv",root/"dataset_final.jsonl"):
  text=path.read_text(encoding="utf-8-sig")
  if "offset_intended" in text or "offset_requested_pre_containment" in text:raise ValueError(f"private offset field leaked into {path.name}")
 print(f"Images: {len(records)}\nRows written: {len(final)}\nSanity check: PASS")
