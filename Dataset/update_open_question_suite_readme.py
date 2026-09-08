"""Update root documentation for the 34-domain supplementary open set."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATASETS=ROOT/"Dataset"


def main():
    path=ROOT/"README.md";text=path.read_text(encoding="utf-8-sig")
    manifests={folder.name:json.loads((folder/"build_manifest.json").read_text(encoding="utf-8")) for folder in sorted(DATASETS.glob("*_dataset_*")) if (folder/"build_manifest.json").is_file()}
    open_total=sum(int(manifest.get("open_questions",manifest["images"])) for manifest in manifests.values())
    lines=[]
    for line in text.splitlines():
        match=re.search(r"\(Dataset/([^/]+)/\)",line)
        if match and match.group(1) in manifests:
            manifest=manifests[match.group(1)];parts=[x.strip() for x in line.strip().split("|")[1:-1]]
            validation_index=next(i for i,x in enumerate(parts) if "PASS" in x)
            base="5,000" if manifest["images"]==1000 else "15,000";open_count=int(manifest.get("open_questions",manifest["images"]))
            line=f"| {parts[0]} | {parts[1]} | {manifest['dataset_version']} | {manifest['images']:,} | {base} + {open_count:,} open | {parts[validation_index]} | {parts[validation_index+1]} |"
        lines.append(line)
    text="\n".join(lines)+"\n"
    text=re.sub(r"\| \*\*Total\*\* \| \*\*34 sub-benchmarks\*\* \|[^\n]+", f"| **Total** | **34 sub-benchmarks** | — | **100,000** | **500,000 + {open_total:,} open** | **34/34 PASS** | **Broad visual, spatial, geometric, topological, analytic, inductive, optical, and mechanical reasoning** |", text)
    old=re.compile(r"The suite-level files in `combined/` are rebuilt.*?The original(?: question and answer)? CSVs remain available for non-viewer workflows\.",re.S)
    new=(f"The suite-level files in `combined/` are rebuilt from dataset directories discovered by `build_manifest.json`, not from a hardcoded list. The five-level combined files include all 34 datasets: 33 datasets at 15,000 questions each plus `projectile_motion_dataset_1000` at 5,000 questions, for 500,000 questions and 500,000 answers. The eligibility-filtered supplementary set contains {open_total:,} open questions and {open_total:,} open answer rows in `all_open_questions_combined.csv` and `all_open_answers_combined.csv`; exclusions are recorded per domain in each build manifest and validation report. The supplementary set does not alter the five-level totals or structure. The Hub's `default` configuration loads the sharded five-level answer Parquet view, including embedded image bytes, prompt, ground truth, and answer format. The separate `annotations` configuration contains one row per image with the combined scene metadata. The original CSVs remain available for non-viewer workflows.")
    text,n=old.subn(new,text)
    if n==0 and new not in text:raise RuntimeError("Combined-suite paragraph not found")
    overview=f"\nEligible images additionally have one domain-specific, parameterized open-ended question using the exact wording in `OPEN_QUESTION_SPEC.md`, with a visual justification and confidence score. Numeric facts store their scoring tolerance. The {open_total:,} supplementary rows are released separately from the fixed five-level ladder, and all exclusions are explicit.\n"
    anchor="This repository generates datasets and ground truth. It does not run models, score predictions, or provide an evaluation harness."
    text=re.sub(r"\nEvery image additionally has one domain-specific, parameterized open-ended question.*?fixed five-level ladder\.\n",overview,text)
    path.write_text(text,encoding="utf-8")
    print(f"Updated root README for {open_total:,} supplementary open questions")


if __name__=="__main__":main()
