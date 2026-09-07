"""Write the human-readable audit report for the 34-domain open-question rewrite."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parent

def main():
    suite=json.loads((ROOT/"open_question_suite_report.json").read_text(encoding="utf-8"))
    combined=json.loads((ROOT/"combined_open_question_report.json").read_text(encoding="utf-8"))
    lines=[
        "# Open-question rewrite and verification",
        "",
        "## Pre-change diagnosis",
        "",
        "- `compass_bearing_0115`: A→B is 162.33927134° under 0°=north, clockwise-positive bearings. The eight sector boundaries are 22.5°, 67.5°, 112.5°, 157.5°, 202.5°, 247.5°, 292.5°, and 337.5°. The value lies in south [157.5°, 202.5°), so the stored word is correct. It is 4.83927134° from the south/south-east boundary. The deterministic open target was within 10° of a boundary in 1,304/3,000 items; considering any directed landmark pair, 2,689/3,000 items and 11,746/27,000 bearings had at least one such case. The rewritten prompt now states the exact sector rule.",
        "- `combination3d_0150`: `len(target_cubes)=11`. One cube, `(0,0,0)`, is fully occluded by the renderer-equivalent visibility test; 10 cubes survive that test. `target_cube_count` counts all cubes. Across the domain, 1,901/3,000 targets contain at least one fully hidden cube, with 3,128 hidden cubes total. The target-total sub-fact was removed.",
        "- `cube_net_0103`: for face A, flat edge-neighbours are C and E from `net_edge_neighbors`, the opposite is F from `opposite_pairs`, and folded neighbours are B, C, D, and E from `cube_adjacent_faces`. All 3,000 records satisfy the complement invariant. The redundant folded-adjacency list was removed.",
        "- No error was found in any closed L1–L5 ground-truth value, so none was changed.",
        "",
        "The pre-change suite sweep found that the shared generator recomputed open facts in 31 domains and its validator called the same derivation functions, so that check was circular. The replacement validator has separate formulas and geometry traversal and never calls the builder's derivation functions. Direct stored values are used only when they are closed-question-validated scene fields; derived values are recomputed independently.",
        "",
        "## Final templates and scored sub-facts",
        "",
        "| Dataset | Version | Sub-facts | Example generated prompt | Highest field baseline |",
        "|---|---|---|---|---:|",
    ]
    for name,m in suite["datasets"].items():
        highest=max(m["constant_answer_baselines"].values())
        prompt=m["template"].replace("|","\\|")
        old_raw=subprocess.check_output(["git","show",f"HEAD:Dataset/{name}/build_manifest.json"],cwd=ROOT.parent,text=True)
        old_version=json.loads(old_raw)["dataset_version"]
        lines.append(f"| `{name}` | `{old_version}` → `{m['dataset_version']}` | `{', '.join(m['subfacts'])}` | {prompt} | {highest:.4f} |")
    lines += [
        "",
        "## Validation result",
        "",
        f"- Domain validators: {suite['status']} ({suite['totals']['domains']}/34).",
        f"- Independent ground-truth mismatches: {sum(x['derivation_mismatches'] for x in suite['datasets'].values())}.",
        f"- PNG recovery: {sum(x['png_recovery']['passed'] for x in suite['datasets'].values()):,}/{sum(x['png_recovery']['total'] for x in suite['datasets'].values()):,}.",
        "- Every item has at most three sub-facts; every numeric sub-fact has a stated and stored tolerance; no `none` placeholders, trap-naming clauses, or unrendered coordinate/index/schema vocabulary remain.",
        "- No scored field has a constant-answer baseline at or above 60%. Full distributions and baselines are stored in each domain's `open_validation_metrics.json` and consolidated in `open_question_suite_report.json`.",
        f"- Combined open files: {combined['combined_open_questions']:,} questions and {combined['combined_open_answers']:,} answers across {len(combined['datasets'])} datasets; all {combined['resolved_image_paths']:,} image paths resolve.",
        "- Protected images, renderers, and closed L1–L5 question/answer payloads are unchanged. Annotation changes are limited to `dataset_version`.",
    ]
    (ROOT/"open_question_rewrite_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("Wrote Dataset/open_question_rewrite_report.md")

if __name__=="__main__":main()
