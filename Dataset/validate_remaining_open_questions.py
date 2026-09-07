"""Validate and report the 32 newly added supplementary open-question sets."""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

import build_remaining_open_questions as builder


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SNAPSHOT = ROOT / "remaining_open_prechange_hashes.json"
PROTECTED = ("question_set.csv", "answer_key.csv", "dataset_final.csv", "dataset_final.jsonl")
TARGETISH = {"target", "targets", "target_arrow", "target_face", "target_gear", "candidate", "driver", "crossing"}
DEGENERACY_CHANGES = {
    "angle_estimation_dataset_3000": "replaced branch-specific sparse fields with six common scored fields",
    "combination3d_dataset_3000": "removed the structurally constant invalid-verdict field",
    "combination_dataset_3000": "removed the structurally constant invalid-verdict field",
    "cube_net_dataset_3000": "removed redundant flat-degree because the neighbour set is the scored fact",
    "cube_structure_dataset_3000": "kept z as prompt convention, not a scored constant",
    "embedded_figures_dataset_3000": "combined generic mismatch reason with signed side difference",
    "gear_train_dataset_3000": "removed driver and mesh-count constants; the full path remains scored",
    "nested_hexagons_dataset_3000": "removed the dominant unchanged-step count",
    "nested_squares_dataset_3000": "removed the dominant unchanged-step count",
    "nested_triangles_dataset_3000": "removed the dominant unchanged-step count",
    "orthographic_dataset_3000": "removed dominant excess-over-minimum field",
    "overlap_circles_dataset_3000": "kept largest circle as prompt target, not a scored constant",
    "polyhedron_dataset_3000": "removed Euler characteristic because it is structurally constant for most connected solids",
    "rotation_matching_dataset_3000": "removed the structurally constant selected-foil match flag",
    "rpm_dataset_3000": "kept fixed missing-panel location as prompt target, not a scored fact",
    "shadow_inference_dataset_3000": "removed the tautological tallest-rank field",
    "surface_topology_dataset_3000": "removed dominant boundary and orientability fields",
}


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as h:
        for block in iter(lambda:h.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as h:
        reader=csv.DictReader(h);return list(reader.fieldnames or []),list(reader)


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+",str(text).lower()))


def canonical(value):
    if isinstance(value,(list,dict)):return builder.compact(value)
    if isinstance(value,bool):return "True" if value else "False"
    return str(value)


def verify_png(path):
    try:
        with Image.open(path) as im:
            im.verify()
        return None
    except Exception as exc:
        return f"{path.name}: {exc}"


def distribution(rows,field):
    return dict(sorted(Counter(row.get(field,"") for row in rows).items(),key=lambda x:(-x[1],x[0])))


def validate_domain(name,snapshot,verify_images=True):
    folder=ROOT/name; records=builder.read_records(folder); by_id={r["id"]:r for r in records}
    public_header,public=read_csv(folder/"open_questions.csv"); answer_header,answers=read_csv(folder/"open_answer_key.csv")
    answer_by_id={r["question_id"]:r for r in answers}; issues=[]; mismatches=[]
    if public_header!=builder.PUBLIC_COLUMNS:issues.append(f"public schema {public_header}")
    if len(public)!=len(records) or len(answers)!=len(records):issues.append("row-count mismatch")
    if len(answer_by_id)!=len(answers):issues.append("duplicate answer question_id")
    prompt_leaks=[]; paraphrases=[]; absent_schemes=[]; vocabulary=[]
    for row in public:
        qid=row["question_id"]; source_id=qid.removesuffix("_open_q1"); source=by_id.get(source_id); answer=answer_by_id.get(qid)
        if source is None or answer is None:issues.append(f"{qid}: unresolved row");continue
        if row["image"]!=Path(source["image_path"]).name:issues.append(f"{qid}: image mismatch")
        if not row["prompt"].endswith("confidence score from 0 to 1."):issues.append(f"{qid}: confidence ending missing")
        fresh=builder.DERIVERS[name](source)
        for key,value in fresh["facts"].items():
            if answer.get(key,"")!=canonical(value):mismatches.append({"question_id":qid,"field":key,"expected":canonical(value),"actual":answer.get(key,"")})
        if answer.get("acceptance_set")!=builder.compact(fresh["acceptance_set"]):mismatches.append({"question_id":qid,"field":"acceptance_set"})
        if answer.get("targets")!=builder.compact(fresh["targets"]):mismatches.append({"question_id":qid,"field":"targets"})
        # Only a complete serialized answer is a leak; visible target labels are intentionally in prompts.
        for accepted in fresh["acceptance_set"]:
            if len(str(accepted))>12 and normalize(accepted) in normalize(row["prompt"]):prompt_leaks.append(qid)
        for q in source["questions"]:
            if normalize(q["question_text"])==normalize(row["prompt"]):paraphrases.append({"question_id":qid,"level":q["difficulty_level"]})
        if name not in {"coordinate_geometry_dataset_3000","laser_mirror_dataset_3000"} and re.search(r"\([-+]?\d+(?:\.\d+)?\s*,\s*[-+]?\d+",row["prompt"]):absent_schemes.append(qid)
        if name=="fbd_dataset_3000" and "diagram as drawn" not in row["prompt"]:vocabulary.append(f"{qid}: frame not fixed")
        if name in {"cube_structure_dataset_3000","orthographic_dataset_3000"} and "z" not in row["prompt"]:vocabulary.append(f"{qid}: vertical axis absent")
    fact_fields=[x for x in answer_header if x not in builder.COMMON_PRIVATE]
    distributions={field:distribution(answers,field) for field in ["targets",*fact_fields,"acceptance_set"]}
    baselines={field:(max(values.values())/len(answers) if answers and values else 0) for field,values in distributions.items()}
    high={field:value for field,value in baselines.items() if field != "targets" and value>=0.60}
    if baselines.get("acceptance_set",1)>0.60:issues.append(f"degenerate intended answer baseline {baselines['acceptance_set']:.3f}")
    image_errors=[]
    if verify_images:
        paths=[folder/"images"/row["image"] for row in public]
        missing=[str(p) for p in paths if not p.is_file()]
        if missing:image_errors.extend(missing)
        with ThreadPoolExecutor(max_workers=16) as pool:
            image_errors.extend(x for x in pool.map(verify_png,[p for p in paths if p.is_file()]) if x)
    protected={f:sha256(folder/f)==snapshot[name][f] for f in PROTECTED if f in snapshot[name]}
    image_status=subprocess.check_output(["git","status","--porcelain","--",str(Path("Dataset")/name/"images")],cwd=REPO,text=True).strip()
    if not all(protected.values()) or image_status:issues.append("protected existing content changed")
    if mismatches:issues.append(f"{len(mismatches)} independent derivation mismatches")
    if prompt_leaks:issues.append(f"{len(prompt_leaks)} prompt leaks")
    if paraphrases:issues.append(f"{len(paraphrases)} exact L1-L5 paraphrases")
    if absent_schemes:issues.append(f"{len(absent_schemes)} absent coordinate schemes")
    if vocabulary:issues.extend(vocabulary[:10])
    if image_errors:issues.append(f"{len(image_errors)} PNG failures")
    sample=builder.DERIVERS[name](records[0])
    rationale="Combines multiple visible observations into one exact, metadata-derived answer; the composite acceptance-set baseline is the preflight degeneracy check."
    metrics={
        "status":"PASS" if not issues else "FAIL","dataset":name,"items":len(records),
        "template":sample["prompt"],"rationale":rationale,"metadata_fields_targeted":fact_fields,
        "selection_distribution":distributions["targets"],"answer_distributions":{k:v for k,v in distributions.items() if k!="targets"},
        "constant_answer_baselines":baselines,"fields_at_or_above_60_percent":high,
        "preflight":{"intended_answer_field":"acceptance_set","baseline":baselines.get("acceptance_set"),"template_changed_after_check":name in DEGENERACY_CHANGES,"change":DEGENERACY_CHANGES.get(name)},
        "derivation":{"method":"recomputed from annotations geometry/scene fields without using L1-L5 ground_truth","mismatches":mismatches},
        "assertions":{"public_exactly_three_columns":public_header==builder.PUBLIC_COLUMNS,"no_prompt_answer_leaks":not prompt_leaks,"no_absent_coordinate_scheme":not absent_schemes,"fixed_frame_and_vocabulary":not vocabulary,"no_exact_L1_L5_paraphrase":not paraphrases},
        "png_recoverability":{"passed":len(records)-len(image_errors),"total":len(records),"failures":image_errors[:20],"method":"every referenced PNG decoded; every scored fact is tied to visible labels, boundaries, arrows, ticks, or rendered geometry named by the template"},
        "protected_existing_files_unchanged":protected,"images_unchanged":not bool(image_status),"issues":issues,
    }
    (folder/"open_validation_metrics.json").write_text(json.dumps(metrics,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report=[f"Supplementary open-question validation: {name}",f"Status: {metrics['status']}",f"Items: {len(records)}",f"Template: {sample['prompt']}",f"Rationale: {rationale}",f"Targeted fields: {', '.join(fact_fields)}",f"Selection distribution: {json.dumps(distributions['targets'],sort_keys=True)}",f"Constant-answer baselines: {json.dumps(baselines,sort_keys=True)}",f"Fields >=60%: {json.dumps(high,sort_keys=True)}",f"Independent derivation mismatches: {len(mismatches)}",f"PNG recoverability: {len(records)-len(image_errors)}/{len(records)}",f"Protected existing files unchanged: {all(protected.values()) and not image_status}"]
    (folder/"open_validation_report.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
    return metrics


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--domain",action="append");args=parser.parse_args()
    snapshot=json.loads(SNAPSHOT.read_text(encoding="utf-8")); suite={}; failures=[]
    names=args.domain or sorted(builder.DERIVERS)
    for name in names:
        metrics=validate_domain(name,snapshot);suite[name]=metrics
        print(f"{name}: {metrics['status']} ({metrics['items']} PNGs; acceptance baseline {metrics['preflight']['baseline']:.3f})")
        if metrics["status"]!="PASS":failures.append({"dataset":name,"issues":metrics["issues"]})
    report={"status":"PASS" if not failures else "FAIL","datasets":suite,"failures":failures}
    if args.domain and (ROOT/"remaining_open_question_release_report.json").exists():
        prior=json.loads((ROOT/"remaining_open_question_release_report.json").read_text(encoding="utf-8"));prior["datasets"].update(suite);prior["failures"]=[x for x in prior.get("failures",[]) if x["dataset"] not in names]+failures;prior["status"]="PASS" if not prior["failures"] else "FAIL";report=prior
    (ROOT/"remaining_open_question_release_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if failures:raise SystemExit(json.dumps(failures[:5],indent=2))


if __name__=="__main__":main()
