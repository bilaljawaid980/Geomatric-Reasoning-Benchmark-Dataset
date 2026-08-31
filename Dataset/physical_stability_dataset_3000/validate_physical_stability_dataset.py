"""Independent validator for cumulative center-of-mass stack stability."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


FILL_RGB = [
    (216, 233, 238),
    (242, 216, 179),
    (220, 231, 200),
    (230, 216, 234),
    (240, 213, 209),
]
COM_RGB = (180, 62, 53)
TASKS = {
    1: "Image Description",
    2: "Basic Relational Reasoning",
    3: "Comparative Reasoning",
    4: "Compound Reasoning",
    5: "Extrapolative/Counterfactual Reasoning",
}


def exact_com(blocks):
    mass=sum(int(b["mass"]) for b in blocks)
    return sum(int(b["mass"])*Fraction(str(b["center_of_mass_x"])) for b in blocks)/mass


def fresh_check(blocks):
    joints=[];first=None
    for index,upper in enumerate(blocks):
        support=blocks[0] if index==0 else blocks[index-1]
        below="ground" if index==0 else support["label"]
        combined=exact_com(blocks[index:])
        left=Fraction(str(support["x_position"]));right=left+Fraction(str(support["width"]))
        stable=left<=combined<=right
        joints.append({"below":below,"upper":upper["label"],"supported":[b["label"] for b in blocks[index:]],"combined":combined,"range":(left,right),"stable":stable})
        if not stable and first is None:first=upper["label"]
    return first is None,first,joints


def relative(upper,lower):
    a=Fraction(str(upper["center_of_mass_x"]));b=Fraction(str(lower["center_of_mass_x"]))
    return "left" if a<b else "right" if a>b else "directly above"


def stability_answer(first,blocks):
    if first is None:return "stable"
    index=next(i for i,b in enumerate(blocks) if b["label"]==first)
    below="ground" if index==0 else f"block {blocks[index-1]['label']}"
    return f"tips between block {first} and {below}"


def removal_answer(blocks):
    top=blocks[-1]["label"]
    stable,first,_=fresh_check(blocks[:-1])
    if stable:return f"stable; after removing block {top}, every cumulative center of mass remains within its supporting base"
    index=next(i for i,b in enumerate(blocks[:-1]) if b["label"]==first)
    below="ground" if index==0 else f"block {blocks[index-1]['label']}"
    return f"unstable; after removing block {top}, the cumulative center of mass at the joint between block {first} and {below} lies outside its supporting base"


def expected_question(row,q,stable,first):
    blocks=row["blocks"];kind=q["question_type"]
    if kind=="block_count":return str(len(blocks))
    if kind=="relative_center_of_mass":
        label=row["level2_upper_block"];index=next(i for i,b in enumerate(blocks) if b["label"]==label)
        return relative(blocks[index],blocks[index-1])
    if kind=="largest_support_offset":
        offsets={b["label"]:abs(Fraction(str(b["center_of_mass_x"]))-Fraction(str(blocks[i-1]["center_of_mass_x"]))) for i,b in enumerate(blocks) if i}
        maximum=max(offsets.values());leaders=[label for label,value in offsets.items() if value==maximum]
        if len(leaders)!=1:raise ValueError(f"ambiguous maximum offset: {leaders}")
        return leaders[0]
    if kind=="whole_stack_stability":return stability_answer(first,blocks)
    if kind=="remove_top_recheck_stability":return removal_answer(blocks)
    raise ValueError(f"unknown question type: {kind}")


def csv_rows(path):
    if not path.exists():return None
    with path.open(encoding="utf-8-sig",newline="") as h:return sum(1 for _ in csv.DictReader(h))


def exact_color_mask(image, rgb):
    channels=image.split()
    masks=[channel.point(lambda value,target=target:255 if value==target else 0) for channel,target in zip(channels,rgb)]
    return ImageChops.multiply(ImageChops.multiply(masks[0],masks[1]),masks[2])


def validate_rendered_blocks(image, row):
    """Read the final PNG and independently recover each flat-fill rectangle."""
    issues=[];iid=row["id"];blocks=row["blocks"]
    for index,rgb in enumerate(FILL_RGB):
        mask=exact_color_mask(image,rgb);bbox=mask.getbbox();pixels=mask.histogram()[255]
        if index>=len(blocks):
            if pixels>20:issues.append(f"{iid}: PNG contains unexpected block-fill color for index {index}")
            continue
        block=blocks[index]
        if bbox is None:
            issues.append(f"{iid}: PNG is missing rendered block {block['label']}")
            continue
        left,top,right,bottom=bbox
        expected=(block["x_position"],block["y_position"],block["x_position"]+block["width"],block["y_position"]+block["height"])
        # Rounded outline and antialiasing inset the exact-color interior by 4-7 px.
        edge_insets=(left-expected[0],top-expected[1],expected[2]-right,expected[3]-bottom)
        if any(not 2<=inset<=9 for inset in edge_insets):
            issues.append(f"{iid}: PNG bounds for block {block['label']} {bbox} disagree with geometry {expected}")
        if pixels < 0.45*block["width"]*block["height"]:
            issues.append(f"{iid}: visible fill area for block {block['label']} is too small ({pixels})")
        cx=int(round(block["center_of_mass_x"]));cy=int(round(block["center_of_mass_y"]))
        found_com=False
        for y in range(max(0,cy-3),min(image.height,cy+4)):
            for x in range(max(0,cx-3),min(image.width,cx+4)):
                if image.getpixel((x,y))==COM_RGB:found_com=True;break
            if found_com:break
        if not found_com:issues.append(f"{iid}: PNG COM marker missing at block {block['label']} center")
    return issues


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))


def validate_flat_files(root, annotations):
    """Cross-check every flattened question against its owning image annotation."""
    issues=[];expected=[]
    for row in annotations:
        image=Path(row["image_path"]).name
        for question in row["questions"]:
            expected.append({
                "question_id":question["question_id"],
                "task":TASKS[question["difficulty_level"]],
                "image":image,
                "prompt":question["question_text"],
                "groundtruth":str(question["ground_truth"]),
            })
    question_rows=read_csv(root/"question_set.csv");answer_rows=read_csv(root/"answer_key.csv");final_rows=read_csv(root/"dataset_final.csv")
    if list(question_rows[0])!=["question_id","task","image","prompt"]:issues.append("tables: question_set.csv has unexpected columns")
    if list(answer_rows[0])!=["question_id","task","image","prompt","groundtruth"]:issues.append("tables: answer_key.csv has unexpected columns")
    if list(final_rows[0])!=["task","image","prompt","groundtruth","metadata"]:issues.append("tables: dataset_final.csv has unexpected columns")
    if not (len(question_rows)==len(answer_rows)==len(final_rows)==len(expected)):
        issues.append(f"tables: row counts differ expected={len(expected)} question={len(question_rows)} answer={len(answer_rows)} final={len(final_rows)}")
        return issues
    seen=set()
    for index,(wanted,question,answer,final) in enumerate(zip(expected,question_rows,answer_rows,final_rows),1):
        qid=wanted["question_id"]
        if qid in seen:issues.append(f"tables: duplicate question ID {qid}")
        seen.add(qid)
        for key in ("question_id","task","image","prompt"):
            if question.get(key)!=wanted[key]:issues.append(f"tables: question_set row {index} {key} mismatch for {qid}")
            if answer.get(key)!=wanted[key]:issues.append(f"tables: answer_key row {index} {key} mismatch for {qid}")
        if answer.get("groundtruth")!=wanted["groundtruth"]:issues.append(f"tables: answer_key ground truth mismatch for {qid}")
        for key in ("task","image","prompt","groundtruth"):
            if final.get(key)!=wanted[key]:issues.append(f"tables: dataset_final row {index} {key} mismatch for {qid}")
        try:
            metadata=json.loads(final["metadata"])
            annotation=annotations[(index-1)//5]
            for key in ("difficulty_score","num_blocks","is_stable","tipping_joint","counterfactual_scenario","seed"):
                if metadata.get(key)!=annotation[key]:issues.append(f"tables: metadata {key} mismatch for {qid}")
        except Exception as exc:issues.append(f"tables: invalid metadata for {qid} ({exc})")
    return issues


def validate(root:Path):
    rows=[json.loads(x) for x in (root/"annotations.jsonl").read_text(encoding="utf-8").splitlines() if x]
    issues=[];stable_counts=Counter();after_counts=Counter();scenario_counts=Counter();qtypes=Counter();block_counts=Counter()
    for row in rows:
        iid=row.get("id","<missing>");blocks=row["blocks"];block_counts[len(blocks)]+=1;scenario_counts[row["counterfactual_scenario"]]+=1
        try:
            if len(blocks)!=row["num_blocks"] or not 2<=len(blocks)<=5:issues.append(f"{iid}: invalid block count")
            labels=[b["label"] for b in blocks]
            if labels!=[chr(ord('A')+i) for i in range(len(blocks))]:issues.append(f"{iid}: labels are not bottom-to-top A..")
            for i,b in enumerate(blocks):
                if b["mass"]!=b["width"]*b["height"]:issues.append(f"{iid}: {b['label']} mass != area")
                if Fraction(str(b["center_of_mass_x"]))!=Fraction(str(b["x_position"]))+Fraction(b["width"],2):issues.append(f"{iid}: {b['label']} COM-x mismatch")
                if Fraction(str(b["center_of_mass_y"]))!=Fraction(str(b["y_position"]))+Fraction(b["height"],2):issues.append(f"{iid}: {b['label']} COM-y mismatch")
                expected_bottom=515 if i==0 else blocks[i-1]["y_position"]
                if b["y_position"]+b["height"]!=expected_bottom:issues.append(f"{iid}: {b['label']} does not rest vertically on support")
                if i:
                    left=max(b["x_position"],blocks[i-1]["x_position"]);right=min(b["x_position"]+b["width"],blocks[i-1]["x_position"]+blocks[i-1]["width"])
                    if right<=left:issues.append(f"{iid}: {b['label']} has no horizontal contact overlap")
            stable,first,joints=fresh_check(blocks);stable_counts[stable]+=1
            if row["is_stable"]!=stable or row["tipping_joint"]!=first:issues.append(f"{iid}: overall stability/tipping joint mismatch")
            if first is not None:
                failures=[j["upper"] for j in joints if not j["stable"]]
                if first!=failures[0]:issues.append(f"{iid}: tipping joint is not lowest failure")
            stored=row["per_joint_stability"]
            if len(stored)!=len(joints):issues.append(f"{iid}: per-joint count mismatch")
            else:
                for actual,saved in zip(joints,stored):
                    if saved["joint_between"]!=[actual["below"],actual["upper"]] or saved["blocks_above"]!=actual["supported"] or Fraction(saved["combined_com_x_fraction"])!=actual["combined"] or saved["is_stable_at_this_joint"]!=actual["stable"]:issues.append(f"{iid}: stored joint data mismatch at {actual['upper']}")
            reduced_stable,reduced_first,reduced_joints=fresh_check(blocks[:-1]);after_counts[reduced_stable]+=1
            reduced=row["after_top_removal"]
            if reduced["is_stable"]!=reduced_stable or reduced["tipping_joint"]!=reduced_first:issues.append(f"{iid}: top-removal result mismatch")
            questions=row.get("questions",[])
            if len(questions)!=5 or [q.get("difficulty_level") for q in questions]!=[1,2,3,4,5]:issues.append(f"{iid}: expected five ordered questions")
            else:
                for q in questions:
                    qtypes[q["question_type"]]+=1;expected=expected_question(row,q,stable,first)
                    if str(q["ground_truth"])!=expected:issues.append(f"{iid}: {q['question_type']} {q['ground_truth']!r} != {expected!r}")
        except Exception as exc:issues.append(f"{iid}: validation exception ({exc})")
        image_path=root/row["image_path"]
        if not image_path.exists():issues.append(f"{iid}: missing PNG")
        else:
            try:
                with Image.open(image_path) as image:
                    image.load()
                    if image.size!=(600,600) or image.mode!="RGB":issues.append(f"{iid}: expected 600x600 RGB PNG")
                    if sum(ImageStat.Stat(image).var)<100:issues.append(f"{iid}: PNG appears blank")
                    issues.extend(validate_rendered_blocks(image.convert("RGB"),row))
            except Exception as exc:issues.append(f"{iid}: unreadable PNG ({exc})")
    if len(rows)>=3000:
        expected_scenarios={"stable_remains_stable","stable_becomes_unstable","unstable_becomes_stable","unstable_remains_unstable"}
        if set(scenario_counts)!=expected_scenarios:issues.append(f"dataset: scenario set mismatch")
        if any(scenario_counts[s]!=750 for s in expected_scenarios):issues.append(f"dataset: scenarios not exactly balanced: {scenario_counts}")
        if stable_counts!={True:1500,False:1500}:issues.append(f"dataset: original stability not balanced: {stable_counts}")
        if after_counts!={True:1500,False:1500}:issues.append(f"dataset: removal stability not balanced: {after_counts}")
        for filename in ("dataset_final.csv","question_set.csv","answer_key.csv"):
            count=csv_rows(root/filename)
            if count!=15000:issues.append(f"dataset: {filename} has {count}, expected 15000")
        issues.extend(validate_flat_files(root,rows))
    report=["Physical Stability Dataset Validation Report","============================================",f"Total images checked: {len(rows)}",f"Total questions checked: {sum(qtypes.values())}",f"Total mismatches found: {len(issues)}","","Original stability:",*[f"  {k}: {v}" for k,v in sorted(stable_counts.items())],"","After top removal:",*[f"  {k}: {v}" for k,v in sorted(after_counts.items())],"","Scenario distribution:",*[f"  {k}: {v}" for k,v in sorted(scenario_counts.items())],"","Block-count distribution:",*[f"  {k}: {v}" for k,v in sorted(block_counts.items())],"","Question types:",*[f"  {k}: {v}" for k,v in sorted(qtypes.items())],"","Issues:",*(issues if issues else ["  None"]),"","Summary: "+("PASS" if not issues else "FAIL")]
    text="\n".join(report)+"\n";(root/"validation_report.txt").write_text(text,encoding="utf-8");print(text);return not issues


def main():
    p=argparse.ArgumentParser();p.add_argument("dataset",nargs="?",type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();raise SystemExit(0 if validate(a.dataset) else 1)


if __name__=="__main__":main()
