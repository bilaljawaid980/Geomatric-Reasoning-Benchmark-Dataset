"""Flatten physical-stability annotations to five-level suite tables."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


TASKS = {1:"Image Description",2:"Basic Relational Reasoning",3:"Comparative Reasoning",4:"Compound Reasoning",5:"Extrapolative/Counterfactual Reasoning"}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("annotations",nargs="?",type=Path);args=parser.parse_args()
    path=args.annotations or Path(__file__).resolve().parent/"annotations.jsonl"
    source=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    rows=[]
    for item in source:
        metadata=json.dumps({key:item[key] for key in ("difficulty_score","num_blocks","is_stable","tipping_joint","counterfactual_scenario","seed")},sort_keys=True,separators=(",",":"))
        for q in item["questions"]:
            rows.append({"question_id":q["question_id"],"task":TASKS[q["difficulty_level"]],"image":Path(item["image_path"]).name,"prompt":q["question_text"],"groundtruth":str(q["ground_truth"]),"metadata":metadata})
    output=path.parent;final=["task","image","prompt","groundtruth","metadata"]
    with (output/"dataset_final.csv").open("w",encoding="utf-8-sig",newline="") as h:
        w=csv.DictWriter(h,fieldnames=final,lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in final} for r in rows)
    with (output/"dataset_final.jsonl").open("w",encoding="utf-8",newline="\n") as h:
        for r in rows:h.write(json.dumps({k:r[k] for k in final},ensure_ascii=False,separators=(",",":"))+"\n")
    qcols=["question_id","task","image","prompt"];acols=qcols+["groundtruth"]
    for name,cols in (("question_set.csv",qcols),("answer_key.csv",acols)):
        with (output/name).open("w",encoding="utf-8-sig",newline="") as h:
            w=csv.DictWriter(h,fieldnames=cols,lineterminator="\n");w.writeheader();w.writerows({k:r[k] for k in cols} for r in rows)
    counts=Counter(r["task"] for r in rows);print(f"Images: {len(source)}\nRows written: {len(rows)}")
    for task in TASKS.values():print(f"  {task}: {counts[task]}")
    if len(rows)!=5*len(source):raise SystemExit("row-count sanity check failed")
    print("Sanity check: PASS")


if __name__=="__main__":main()
