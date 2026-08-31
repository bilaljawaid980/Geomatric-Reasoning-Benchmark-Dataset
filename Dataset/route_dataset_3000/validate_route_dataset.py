"""Validate route_dataset annotations against stored route-level ground truth."""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path

def pair_key(a,b):return "".join(sorted((a,b)))

def validate(dataset_dir:Path)->tuple[int,list[str]]:
 annotation_path=dataset_dir/"annotations.jsonl";issues=[];checked=0
 if not annotation_path.is_file():raise FileNotFoundError(annotation_path)
 with annotation_path.open(encoding="utf-8") as f:
  for line_number,line in enumerate(f,1):
   if not line.strip():continue
   try:row=json.loads(line)
   except Exception as exc:issues.append(f"line {line_number}: invalid JSON: {exc}");continue
   checked+=1;iid=row.get("id",f"line_{line_number}");routes=row.get("routes",[]);letters=row.get("endpoint_letters",[])
   image=dataset_dir/row.get("image_path","")
   if not image.is_file():issues.append(f"{iid}: referenced image missing: {row.get('image_path')}")
   colors=[r.get("color") for r in routes]
   duplicates=sorted(c for c,n in Counter(colors).items() if n>1)
   if duplicates:issues.append(f"{iid}: duplicate route colors: {duplicates}")
   for index,r in enumerate(routes):
    if r.get("start") not in letters:issues.append(f"{iid}: route {index} start {r.get('start')!r} not in endpoint_letters")
    if r.get("end") not in letters:issues.append(f"{iid}: route {index} end {r.get('end')!r} not in endpoint_letters")
   pair_counts=Counter(pair_key(r["start"],r["end"]) for r in routes if r.get("start")!=r.get("end"))
   degree=Counter()
   for r in routes:degree[r["start"]]+=1;degree[r["end"]]+=1
   questions=row.get("questions",[])
   if len(questions)!=4:issues.append(f"{iid}: expected 4 questions, found {len(questions)}")
   if [q.get("difficulty_level") for q in questions]!=[1,2,3,4]:issues.append(f"{iid}: difficulty levels are not ordered [1, 2, 3, 4]")
   all_pairs=[letters[i]+letters[j] for i in range(len(letters)) for j in range(i+1,len(letters))]
   for q in questions:
    typ=q.get("question_type");actual=None
    if typ=="count_routes_between_pair":
     try:
      pair=q["question_text"].split("from ",1)[1].split(". Answer",1)[0].split(" to ");actual=str(pair_counts[pair_key(pair[0],pair[1])])
     except Exception as exc:issues.append(f"{iid}/{q.get('question_id')}: cannot parse letter pair: {exc}");continue
    elif typ=="most_connected_pair":
     maximum=max(pair_counts.values(),default=0);winners=sorted(p for p,n in pair_counts.items() if n==maximum)
     actual=winners[0] if len(winners)==1 else None
    elif typ=="highest_degree_letter":
     maximum=max((degree[x] for x in letters),default=0);winners=sorted(x for x in letters if degree[x]==maximum)
     actual=winners[0] if len(winners)==1 else None
    elif typ=="single_route_pairs":actual=sorted(p for p,n in pair_counts.items() if n==1)
    elif typ=="letter_degree":
     try:letter=q["question_text"].split("letter ",1)[1].split(" ",1)[0];actual=str(degree[letter])
     except Exception as exc:issues.append(f"{iid}/{q.get('question_id')}: cannot parse degree letter: {exc}");continue
    elif typ=="total_routes":actual=str(len(routes))
    elif typ=="num_routes_visible":actual=str(len(routes))
    elif typ=="num_labeled_endpoints":actual=str(len(letters))
    elif typ=="self_loop":actual="yes" if any(r["start"]==r["end"] for r in routes) else "no"
    elif typ=="zero_connection_pair":
     zero=sorted(p for p in all_pairs if pair_counts[p]==0);stored=q.get("ground_truth");actual=stored if ((stored=="none" and not zero) or stored in zero) else "<invalid-zero-pair>"
    elif typ=="degree_ordering":
     freq=Counter(degree[x] for x in letters);actual=[f"{x} (degree {degree[x]}{'—tie' if freq[degree[x]]>1 else ''})" for x in sorted(letters,key=lambda x:(-degree[x],x))]
    else:issues.append(f"{iid}/{q.get('question_id')}: unknown question_type {typ!r}");continue
    if actual!=q.get("ground_truth"):issues.append(f"{iid}/{q.get('question_id')}: {typ} mismatch; stored={q.get('ground_truth')!r}, recomputed={actual!r}")
 return checked,issues

def write_report(dataset_dir:Path,checked:int,issues:list[str])->Path:
 report=dataset_dir/"validation_report.txt";ids=sorted({x.split(":",1)[0].split("/",1)[0] for x in issues})
 lines=["ROUTE DATASET VALIDATION REPORT","="*31,f"Total images checked: {checked}",f"Total mismatches found: {len(issues)}",f"Images/lines with mismatches: {len(ids)}",f"Summary: {'PASS' if not issues else 'FAIL'}",""]
 if issues:lines += ["MISMATCH DETAILS","-"*16,*issues]
 else:lines += ["All referenced images exist.","All supported question ground truths match route recounts.","No duplicate colors occur within any image.","All route endpoints exist in endpoint_letters."]
 report.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n");return report

def main():
 p=argparse.ArgumentParser();p.add_argument("dataset_dir",type=Path);a=p.parse_args();checked,issues=validate(a.dataset_dir);report=write_report(a.dataset_dir,checked,issues);print(report.read_text(encoding="utf-8"));print(f"Report: {report}");raise SystemExit(1 if issues else 0)
if __name__=="__main__":main()
