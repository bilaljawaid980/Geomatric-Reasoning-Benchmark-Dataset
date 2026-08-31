from __future__ import annotations
import argparse,json,math
from pathlib import Path
from generate_line_intersection_dataset import compute_intersections,is_self_intersecting
def validate(root):
 issues=[];checked=0
 for line in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines():
  if not line:continue
  r=json.loads(line);checked+=1;iid=r["id"];red=r["red_points"];blue=r["blue_points"]
  if not (root/r["image_path"]).is_file():issues.append(f"{iid}: missing image")
  try:ints=compute_intersections(red,blue,True)
  except ValueError as e:issues.append(f"{iid}: degenerate intersection: {e}");continue
  if len(ints)!=r["total_intersections"]:issues.append(f"{iid}: intersection count mismatch")
  if ints!=r["intersections"]:issues.append(f"{iid}: intersection coordinates mismatch")
  derived={"red_segment_count":str(len(red)-1),"blue_segment_count":str(len(blue)-1),"intersection_count":str(len(ints)),"higher_at_start":"red" if red[0][1]<blue[0][1] else "blue","red_end_relation":"above" if red[-1][1]<blue[-1][1] else "below","intersection_parity":"odd" if (red[0][1]<blue[0][1])!=(red[-1][1]<blue[-1][1]) else "even","remove_first_red_segment":str(len(ints)-sum(p["red_segment_index"]==0 for p in ints))}
  derived["leftmost_intersection_side"]=("left" if ints[0]["x"]<r["canvas_size"][0]/2 else "right") if ints else None;left=sum(p["x"]<r["canvas_size"][0]/2 for p in ints);derived["intersection_half_counts"]=f"{left},{len(ints)-left}"
  for q in r["questions"]:
   actual=derived.get(q["question_type"])
   if actual is None:issues.append(f"{iid}: unavailable/unknown question {q['question_type']}")
   elif actual!=q["ground_truth"]:issues.append(f"{iid}/{q['question_id']}: stored={q['ground_truth']}, actual={actual}")
  if len(r["questions"])!=4 or [q["difficulty_level"] for q in r["questions"]]!=[1,2,3,4]:issues.append(f"{iid}: invalid question levels")
  if is_self_intersecting(red)!=r["red_self_intersecting"] or is_self_intersecting(blue)!=r["blue_self_intersecting"]:issues.append(f"{iid}: self-intersection flag mismatch")
 return checked,issues
def main():
 p=argparse.ArgumentParser();p.add_argument("dataset",type=Path);a=p.parse_args();n,e=validate(a.dataset);report=a.dataset/"validation_report.txt";report.write_text(f"Total images checked: {n}\nTotal mismatches found: {len(e)}\nSummary: {'PASS' if not e else 'FAIL'}\n"+("\n".join(e)+"\n" if e else ""),encoding="utf-8");print(report.read_text());raise SystemExit(bool(e))
if __name__=="__main__":main()
