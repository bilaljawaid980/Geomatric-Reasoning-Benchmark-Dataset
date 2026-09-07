"""Final cross-domain release invariants for all supplementary open questions."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
OUT=ROOT/"open_question_suite_report.json"
PROTECTED=("question_set.csv","answer_key.csv","dataset_final.csv","dataset_final.jsonl")


def sha256(path):
    d=hashlib.sha256()
    with path.open("rb") as h:
        for b in iter(lambda:h.read(1024*1024),b""):d.update(b)
    return d.hexdigest()


def git_bytes(relative):
    raw=subprocess.check_output(["git","show",f"HEAD:{relative}"],cwd=REPO)
    if raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raw=subprocess.run(["git","lfs","smudge"],cwd=REPO,input=raw,stdout=subprocess.PIPE,check=True).stdout
    return raw


def annotation_payload(raw):
    result=[]
    for line in raw.decode("utf-8-sig").splitlines():
        if line:
            row=json.loads(line);row.pop("dataset_version",None);result.append(row)
    return result


def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))


def main():
    remaining=json.loads((ROOT/"remaining_open_prechange_hashes.json").read_text(encoding="utf-8"))
    prior=json.loads((ROOT/"open_question_prechange_hashes.json").read_text(encoding="utf-8"))
    combined=json.loads((ROOT/"combined_open_question_report.json").read_text(encoding="utf-8"))
    domains={};failures=[]
    for manifest_path in sorted(ROOT.glob("*_dataset_*/build_manifest.json")):
        folder=manifest_path.parent;name=folder.name;manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        public=rows(folder/"open_questions.csv");private=rows(folder/"open_answer_key.csv")
        metrics=json.loads((folder/"open_validation_metrics.json").read_text(encoding="utf-8"))
        expected=int(manifest["images"]);issues=[]
        if len(public)!=expected or len(private)!=expected:issues.append("open row count mismatch")
        if list(public[0]) != ["question_id","image","prompt"]:issues.append("public schema mismatch")
        if metrics.get("status","PASS")!="PASS" or metrics.get("issues"):issues.append("domain validator failed")
        snap=remaining.get(name) or prior.get(name,{})
        protected={}
        for file in PROTECTED:
            key=file if file in snap else file.replace(".","_")+"_sha256"
            if file in snap: expected_hash=snap[file]
            else:
                legacy={"question_set.csv":"question_set_sha256","answer_key.csv":"answer_key_sha256","dataset_final.csv":"dataset_final_csv_sha256","dataset_final.jsonl":"dataset_final_jsonl_sha256"}
                expected_hash=snap.get(legacy[file])
            if expected_hash:protected[file]=sha256(folder/file)==expected_hash
        rel=(Path("Dataset")/name/"annotations.jsonl").as_posix()
        payload_same=annotation_payload(git_bytes(rel))==annotation_payload((folder/"annotations.jsonl").read_bytes())
        image_status=subprocess.check_output(["git","status","--porcelain","--",str(Path("Dataset")/name/"images")],cwd=REPO,text=True).strip()
        if not all(protected.values()) or not payload_same or image_status:issues.append("protected content changed")
        domains[name]={"dataset_version":manifest["dataset_version"],"images":expected,"open_questions":len(public),"open_answers":len(private),"validation_status":"PASS" if not issues else "FAIL","constant_answer_baselines":metrics["constant_answer_baselines"],"fields_at_or_above_60_percent":metrics.get("fields_at_or_above_60_percent",metrics.get("fields_over_60_percent",{})),"derivation_mismatches":len(metrics.get("derivation",{}).get("mismatches",metrics.get("derivation_mismatches",[]))),"png_recoverability":metrics["png_recoverability"],"protected_files_unchanged":protected,"annotation_payload_unchanged_except_version":payload_same,"images_unchanged":not bool(image_status),"issues":issues}
        if issues:failures.append({"dataset":name,"issues":issues})
    report={"status":"PASS" if not failures else "FAIL","datasets":domains,"totals":{"domains":len(domains),"images":sum(x["images"] for x in domains.values()),"open_questions":sum(x["open_questions"] for x in domains.values()),"open_answers":sum(x["open_answers"] for x in domains.values())},"combined_open":combined,"protected_scope":"images, renderers, existing five-level questions and answers unchanged; annotations changed only in dataset_version","failures":failures}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"totals":report["totals"],"failures":failures},indent=2))
    if failures:raise SystemExit(1)


if __name__=="__main__":main()
