"""Build an offline prompt/response manifest for the final figure images.

The script reads existing plans, analyses, and stored responses. It makes no API
calls and writes only ``manifest.json`` beside this file.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).with_name("manifest.json")
MODELS = [
    "claude_opus_5",
    "claude_sonnet_5",
    "deepseek_v4_1_flash",
    "gemini_3_8_flash",
    "gpt_5_6_luna",
    "gpt_5_6_sol",
    "grok_4_6",
    "inking",
    "muse_glimmer_30b",
    "perplexity_sonar_pro",
]
IMAGES = {
    "cube_structure_0168": ("Solid", "cube_structure"),
    "hex_pathfinding_2132": ("Topological", "hex_pathfinding"),
    "nested_squares_1571": ("Plane", "nested_squares"),
    "occluded_pattern_0134": ("Projective", "occluded_pattern"),
    "optical_illusion_0046": ("Optical", "optical_illusion"),
    "physical_stability_0060": ("Physical", "physical_stability"),
    "route_puzzle_2166": ("Topological", "route"),
    "rpm_1901": ("Inductive", "rpm"),
    "symmetry_pattern_2333": ("Transformational", "symmetry_pattern"),
}


def scalar(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def records(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                output.append(json.loads(line))
    return output


def answer_line(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.replace("**", "").replace("__", "")
    match = re.search(r"(?im)^\s*ANSWER\s*:\s*(.*?)\s*$", cleaned)
    return match.group(1).strip() if match else None


def transition(before: bool | None, after: bool | None) -> str | None:
    if before is None or after is None:
        return None
    if before and after:
        return "held"
    if before and not after:
        return "capitulation"
    if not before and after:
        return "correction"
    return "unchanged_wrong"


def load_test1() -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = [
        ROOT / "tests/test_1_closed_loop/analysis/per_question.csv",
        ROOT / "tests/test_1_closed_loop/analysis/gpt_5_6_sol/per_question.csv",
        ROOT / "tests/test_1_closed_loop/analysis/deepseek_v4_1_flash/per_question.csv",
        ROOT / "tests/test_1_closed_loop/analysis/perplexity_sonar_pro/per_question.csv",
    ]
    raw = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    raw = raw[raw["stem"].isin(IMAGES)].drop_duplicates(["model", "row_id"], keep="last")
    typed = pd.read_csv(ROOT / "analysis/typed_comparator/test1_row_scores.csv")
    typed = typed[typed["stem"].isin(IMAGES)][
        ["model", "row_id", "typed_correct", "typed_parsed", "typed_parse_ok"]
    ]
    return raw, typed


def load_test2() -> pd.DataFrame:
    paths = [
        ROOT / "tests/test_2_grain_robustness/analysis/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/gpt_5_6_sol/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/deepseek_v4_1_flash/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/perplexity_sonar_pro/per_question.csv",
    ]
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    return frame[frame["stem"].isin(IMAGES)].drop_duplicates(
        ["model", "row_id", "sigma"], keep="last"
    )


def load_test3() -> tuple[list[dict[str, Any]], pd.DataFrame]:
    result_dir = ROOT / "tests/test_3_sycophancy/results"
    rows: list[dict[str, Any]] = []
    for path in sorted(result_dir.glob("sycophancy_*.jsonl")):
        rows.extend(record for record in records(path) if record.get("stem") in IMAGES)
    typed = pd.read_csv(ROOT / "analysis/typed_comparator/test3_row_scores.csv")
    typed = typed[typed["stem"].isin(IMAGES)]
    return rows, typed


def load_test4() -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], pd.DataFrame]:
    plan = ROOT / "tests/test_4_crossexam/plan"
    r1_manifest_paths = [
        plan / "crossexam_manifest.csv",
        plan / "gpt_5_6_sol/crossexam_manifest_with_gpt_5_6_sol.csv",
        plan / "deepseek_v4_1_flash/crossexam_manifest.csv",
        plan / "perplexity_sonar_pro/crossexam_manifest.csv",
    ]
    r2_manifest_paths = [
        plan / "crossexam_round2_manifest.csv",
        plan / "gpt_5_6_sol/crossexam_round2_manifest_with_gpt_5_6_sol.csv",
        plan / "deepseek_v4_1_flash/crossexam_round2_manifest.csv",
        plan / "perplexity_sonar_pro/crossexam_round2_manifest.csv",
    ]
    r1_manifest = pd.concat([pd.read_csv(path) for path in r1_manifest_paths], ignore_index=True)
    r2_manifest = pd.concat([pd.read_csv(path) for path in r2_manifest_paths], ignore_index=True)
    r1_manifest = r1_manifest[r1_manifest["stem"].isin(IMAGES)].drop_duplicates("row_id")
    r2_manifest = r2_manifest[r2_manifest["stem"].isin(IMAGES)].drop_duplicates("row_id")

    result_dir = ROOT / "tests/test_4_crossexam/results"
    r1_results: list[dict[str, Any]] = []
    r2_results: list[dict[str, Any]] = []
    for model in MODELS:
        r1_path = result_dir / f"crossexam_r1_{model}.jsonl"
        r1_results.extend(row for row in records(r1_path) if row.get("stem") in IMAGES)
        for arm in ("natural", "constructed", "control_reask"):
            path = result_dir / f"crossexam_r2_{model}_{arm}.jsonl"
            r2_results.extend(row for row in records(path) if row.get("stem") in IMAGES)

    scored_parts = []
    for model in MODELS:
        path = ROOT / f"tests/test_4_crossexam/analysis/phase1/{model}/round1_scored.csv"
        scored_parts.append(pd.read_csv(path))
    r1_scored = pd.concat(scored_parts, ignore_index=True)
    r1_scored = r1_scored[r1_scored["stem"].isin(IMAGES)]
    return r1_manifest, r2_manifest, r1_results, r2_results, r1_scored


def prior_question_sets() -> dict[str, dict[str, Any]]:
    path = ROOT / "figures/samples/manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    found: dict[str, dict[str, Any]] = {}
    for family_rows in data["families"].values():
        for row in family_rows:
            found[row["image_id"]] = {
                "closed_loop": row.get("closed_loop"),
                "open_loop": row.get("open_loop"),
            }
    return found


def main() -> None:
    t1, t1_typed = load_test1()
    t2 = load_test2()
    t3, t3_typed = load_test3()
    t4_r1m, t4_r2m, t4_r1, t4_r2, t4_score = load_test4()
    old_questions = prior_question_sets()

    typed1 = {
        (row.model, row.row_id): row
        for row in t1_typed.itertuples(index=False)
    }
    typed3 = {
        (row.model, row.stem, int(row.level), row.arm, row.strength): row
        for row in t3_typed.itertuples(index=False)
    }
    r1_manifest = {row["row_id"]: row for row in t4_r1m.to_dict("records")}
    r2_manifest = {row["row_id"]: row for row in t4_r2m.to_dict("records")}
    r1_result = {row["row_id"]: row for row in t4_r1}
    r2_result = {row["row_id"]: row for row in t4_r2}
    r1_score = {row.row_id: row for row in t4_score.itertuples(index=False)}

    sys.path.insert(0, str(ROOT / "tests/test_4_crossexam/scripts"))
    from crossexam_common import answer_is_accepted, response_parts

    output: dict[str, Any] = {
        "description": "Exact stored prompts and responses for the final figure-image selection. Null means that image was not evaluated in that test.",
        "models": MODELS,
        "images": {},
        "coverage": {},
        "scoring_notes": {
            "test1": "Both archived strict and current typed-comparator fields are retained.",
            "test2": "Correctness is the archived Test-2 absolute_correct field.",
            "test3": "Correctness uses analysis/typed_comparator/test3_row_scores.csv.",
            "test4": "Round-1 archived score fields are retained; Round-2 correctness is parsed with the current answer_is_accepted comparator and labelled accordingly.",
        },
        "network_calls": 0,
        "warnings": [],
    }

    for stem, (family, domain) in IMAGES.items():
        image: dict[str, Any] = {
            "family": family,
            "domain": domain,
            "image_id": stem,
            "file": f"figures/samples/all_four_tests/final/{stem}.png",
            "dataset_question_set": old_questions.get(stem),
        }

        # Test 1
        subset1 = t1[t1["stem"] == stem].sort_values(["model", "level"])
        test1: dict[str, Any] = {}
        for row in subset1.to_dict("records"):
            typed = typed1.get((row["model"], row["row_id"]))
            test1.setdefault(row["model"], {"levels": []})["levels"].append({
                "level": int(row["level"]),
                "question_id": row["question_id"],
                "prompt_sent": scalar(row["prompt_sent"]),
                "question": scalar(row["prompt"]),
                "ground_truth": scalar(row["ground_truth"]),
                "answer_format": scalar(row["answer_format"]),
                "raw_response": scalar(row["response_raw"]),
                "parsed_answer_archived": scalar(row["parsed_answer"]),
                "strict_correct_archived": bool(row["absolute_correct"]),
                "typed_parsed_current": scalar(typed.typed_parsed) if typed is not None else None,
                "typed_parse_ok_current": bool(typed.typed_parse_ok) if typed is not None else None,
                "typed_correct_current": bool(typed.typed_correct) if typed is not None else None,
            })
        image["test1"] = test1 or None

        # Test 2
        subset2 = t2[t2["stem"] == stem].sort_values(["model", "sigma", "level"])
        test2: dict[str, Any] = {}
        for row in subset2.to_dict("records"):
            sigma = f"sigma_{int(row['sigma'])}"
            model = test2.setdefault(row["model"], {})
            model.setdefault(sigma, []).append({
                "level": int(row["level"]),
                "question_id": row["question_id"],
                "prompt_sent": scalar(row["prompt_sent"]),
                "ground_truth": scalar(row["ground_truth"]),
                "raw_response": scalar(row["response_raw"]),
                "parsed_answer": scalar(row["parsed_answer"]),
                "correct_archived": bool(row["absolute_correct"]),
            })
        image["test2"] = test2 or None

        # Test 3
        test3: dict[str, Any] = {}
        for row in sorted(
            (r for r in t3 if r.get("stem") == stem),
            key=lambda r: (r.get("model", ""), int(r.get("level", 0))),
        ):
            key = (row["model"], stem, int(row["level"]), row["arm"], row["strength"])
            typed = typed3.get(key)
            before = bool(typed.typed_r1) if typed is not None else None
            after = bool(typed.typed_r2) if typed is not None else None
            test3.setdefault(row["model"], {})[f"level_{int(row['level'])}"] = {
                "condition": row.get("arm"),
                "strength": row.get("strength"),
                "question_id": row.get("question_id"),
                "prompt_original": row.get("prompt_original"),
                "turn1_prompt_sent": row.get("turn1_prompt_sent"),
                "asserted_answer": row.get("asserted_answer"),
                "assertion_text": row.get("assertion_text"),
                "turn2_prompt_sent": row.get("turn2_prompt_sent"),
                "round1_raw": row.get("round1_response_raw"),
                "round1_final_answer": scalar(row.get("round1_answer")),
                "round2_raw": row.get("response_raw"),
                "round2_final_answer": answer_line(row.get("response_raw")),
                "round1_correct_typed": before,
                "round2_correct_typed": after,
                "transition_typed": transition(before, after),
            }
        image["test3"] = test3 or None

        # Test 4
        test4: dict[str, Any] = {}
        for row_id, plan_row in sorted(r1_manifest.items()):
            if plan_row["stem"] != stem:
                continue
            raw = r1_result.get(row_id)
            scored = r1_score.get(row_id)
            model = plan_row["model"]
            test4[model] = {
                "question_id": plan_row["question_id"],
                "prompt_original": plan_row["prompt"],
                "prompt_sent": raw.get("prompt_sent") if raw else None,
                "ground_truth": plan_row["ground_truth"],
                "acceptance_set": json.loads(plan_row["acceptance_set"]),
                "phase1_raw": raw.get("response_raw") if raw else None,
                "phase1_final_answer_archived": scalar(scored.answer) if scored is not None else None,
                "phase1_correct_archived": bool(scored.correct) if scored is not None else None,
                "phase1_confidence": scalar(scored.confidence) if scored is not None else None,
                "phase2": {},
            }
        for row_id, plan_row in sorted(r2_manifest.items()):
            if plan_row["stem"] != stem:
                continue
            raw = r2_result.get(row_id)
            parts = response_parts(raw.get("response_raw", ""), round2=True) if raw else {}
            after = answer_is_accepted(parts.get("answer"), plan_row["acceptance_set"]) if raw else None
            before = str(plan_row["round1_correct"]).casefold() == "true"
            test4.setdefault(plan_row["model"], {"phase2": {}})["phase2"][plan_row["arm"]] = {
                "peer_models": json.loads(plan_row["peers_shown"]),
                "peer_answers": json.loads(plan_row["peer_answers"]),
                "peer_block": plan_row["peer_text"],
                "turn2_prompt_sent": raw.get("turn2_prompt_sent") if raw else None,
                "phase2_raw": raw.get("response_raw") if raw else None,
                "phase2_final_answer": parts.get("answer"),
                "phase2_justification": parts.get("justification"),
                "phase2_changed": parts.get("changed"),
                "phase2_confidence": parts.get("confidence"),
                "round1_correct_archived_manifest": before,
                "round2_correct_current_comparator": after,
                "transition_mixed_label": transition(before, after),
            }
        image["test4"] = test4 or None

        coverage = {
            "test1_models": len(test1),
            "test2_models": len(test2),
            "test3_models": len(test3),
            "test4_models": len(test4),
        }
        image["in_test"] = {name.replace("_models", ""): count > 0 for name, count in coverage.items()}
        output["coverage"][stem] = coverage
        output["images"][stem] = image

    missing = [
        f"{stem}: absent from {test}"
        for stem, counts in output["coverage"].items()
        for test, count in counts.items()
        if count == 0
    ]
    output["warnings"].extend(missing)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Coverage (number of models with stored responses)")
    print("image_id,test1,test2,test3,test4")
    for stem, counts in output["coverage"].items():
        print(
            f"{stem},{counts['test1_models']},{counts['test2_models']},"
            f"{counts['test3_models']},{counts['test4_models']}"
        )
    print(f"Wrote: {OUTPUT.relative_to(ROOT)}")
    print("Network calls: 0")


if __name__ == "__main__":
    main()
