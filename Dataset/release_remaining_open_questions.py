"""Apply version, manifest, README, and open-annotation metadata for the 34-domain rewrite."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import build_remaining_open_questions as builder

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
SOURCE_COMMIT=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()


def bumped(version,name):
    if version=="legacy-current":
        slug=name.rsplit("_dataset_",1)[0].replace("_","-")
        return f"{slug}-2.0.0"
    match=re.match(r"(.+)-(\d+)\.(\d+)\.(\d+)$",version)
    if not match:raise ValueError(f"Cannot bump {name}: {version}")
    return f"{match.group(1)}-{int(match.group(2))+1}.0.0"


def rewrite_jsonl_version(path,version):
    rows=[]
    with path.open(encoding="utf-8-sig") as h:
        for line in h:
            if line.strip():
                row=json.loads(line);row["dataset_version"]=version;rows.append(row)
    with path.open("w",encoding="utf-8",newline="\n") as h:
        for row in rows:h.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")


def main():
    release=json.loads((ROOT/"remaining_open_question_release_report.json").read_text(encoding="utf-8"))
    versions={}
    for name in sorted(builder.DERIVERS):
        folder=ROOT/name; manifest_path=folder/"build_manifest.json";manifest=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        old=str(manifest.get("dataset_version","legacy-current"));new=bumped(old,name);versions[name]={"before":old,"after":new}
        rewrite_jsonl_version(folder/"annotations.jsonl",new);rewrite_jsonl_version(folder/"open_annotations.jsonl",new)
        manifest["dataset_version"]=new
        manifest["open_questions"]=int(manifest["images"])
        manifest["open_question_files"]=["open_questions.csv","open_answer_key.csv","open_annotations.jsonl"]
        constraints=manifest.setdefault("constraint_set",{})
        constraints.update({
            "existing_five_level_questions_unchanged":True,
            "open_question_count_per_image":1,
            "open_public_fields_exact":["question_id","image","prompt"],
            "open_ground_truth_rederived_from_scene_metadata":True,
            "open_prompt_no_unrendered_coordinate_scheme":True,
            "open_maximum_subfacts":3,
            "open_no_deterministically_redundant_subfacts":True,
            "open_no_none_placeholders":True,
            "open_numeric_tolerances_stored_and_stated":True,
            "open_prompt_does_not_name_reasoning_trap":True,
            "open_png_recoverability_all_items":True,
            "open_composite_answer_baseline_below_0_60":True,
        })
        manifest["open_question_builder"]="../build_remaining_open_questions.py"
        manifest["open_question_validator"]="../validate_remaining_open_questions.py"
        manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        metrics=release["datasets"][name]
        readme_path=folder/"README.md";text=readme_path.read_text(encoding="utf-8-sig")
        heading="### Supplementary open-ended questions"
        if heading in text:text=text.split(heading)[0].rstrip()+"\n"
        section=(
            f"\n{heading}\n\nVersion `{new}` rewrites the one parameterized free-response question per image without changing any image or existing five-level question or answer. Each plain-English prompt scores at most three visible sub-facts, does not name its own reasoning trap, requires a brief visual justification, and ends with a confidence score from 0 to 1.\n\n"
            "- `open_questions.csv` is public and contains exactly `question_id,image,prompt`.\n"
            "- `open_answer_key.csv` is answer-key-side and contains separate partial-credit fields, an exhaustive `acceptance_set`, deterministic `targets`, and machine-readable `tolerances` for every numeric field.\n"
            "- `open_annotations.jsonl` is answer-key-side and adds the complete derivation and scoring declaration.\n"
            "- `open_validation_metrics.json` contains full target and answer distributions, constant-answer baselines, prompt/schema checks, independent metadata derivation results, and exhaustive PNG recovery results.\n\n"
            f"The composite acceptance-set baseline is `{metrics['composite_answer_baseline']:.6f}`. "
            f"Scored fields at or above 60% after template revision: `{json.dumps(metrics['fields_at_or_above_60_percent'],sort_keys=True)}`. "
            f"Targeted fields: `{', '.join(metrics['subfacts'])}`. "
            "Do not provide `open_answer_key.csv`, `open_annotations.jsonl`, or the closed-set `annotations.jsonl` to a model under evaluation because they expose answer-side scene metadata.\n"
        )
        readme_path.write_text(text.rstrip()+"\n"+section,encoding="utf-8")
    for name,change in versions.items():
        release["datasets"][name]["dataset_version_before"]=change["before"]
        release["datasets"][name]["dataset_version_after"]=change["after"]
    release["version_bumps"]=versions;release["source_commit_before_release"]=SOURCE_COMMIT
    (ROOT/"remaining_open_question_release_report.json").write_text(json.dumps(release,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(versions,indent=2))


if __name__=="__main__":main()
