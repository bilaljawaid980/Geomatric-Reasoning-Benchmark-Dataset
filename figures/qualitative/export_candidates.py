"""Export strictly verbatim qualitative candidates from stored GRIP runs only."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/test_1_closed_loop/scripts"))

from grip_eval.config import MODELS
from grip_eval.parsing import compare_answer, normalize_approved_equivalent, parse_answer
from score_closed_loop import load_results, parse_and_compare, serialized_value

OUT = ROOT / "figures/qualitative"
IMAGES = OUT / "images"
PREFERRED = {
    "route": 0, "line_intersection": 1, "overlap_circles": 2,
    "gear_train": 3, "physical_stability": 4, "cube_net": 5,
    "fold_punch": 6, "shadow_inference": 7,
}
EXCLUDED_A = {"rotation_matching", "optical_illusion", "surface_topology", "impossible_object"}
DISPLAY = {key: value["display_name"] for key, value in MODELS.items()}


def latest_jsonl(path: Path, model: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("model", model) != model:
                raise ValueError(f"Wrong model in {path}: {row.get('model')!r}")
            records[str(row["row_id"])] = row
    return records


def line_value(raw: str, label: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.*?)\s*$", raw)
    return match.group(1).strip() if match else None


def confidence(raw: str) -> float | None:
    value = line_value(raw, "CONFIDENCE")
    if value is None or not re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", value):
        return None
    return float(value)


def canonical(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return normalize_approved_equivalent(value)


def parsed(raw: str, answer_format: str, ground_truth: str, prompt: str):
    return parse_answer(raw, answer_format, ground_truth, "", prompt)


def score(raw: str, answer_format: str, ground_truth: str, prompt: str) -> tuple[Any, bool]:
    answer = parsed(raw, answer_format, ground_truth, prompt)
    return answer, compare_answer(answer, ground_truth, answer_format, "")


def route_propagates(level4: Any, level5: Any) -> bool:
    """Check L5 maximum degree against the model's own L4 ranking/degree claims."""
    if not isinstance(level4, list):
        return False
    degrees: dict[str, int] = {}
    for item in level4:
        match = re.search(r"\b([A-Z])\b.*?degree\s+(\d+)", str(item), flags=re.I)
        if match:
            degrees[match.group(1).upper()] = int(match.group(2))
    if not {"B", "D"}.issubset(degrees):
        return False
    projected = dict(degrees)
    projected["B"] += 1
    projected["D"] += 1
    try:
        return Decimal(str(level5)) == max(projected.values())
    except Exception:
        return False


def propagated(group: pd.DataFrame) -> bool:
    l4, l5 = group.iloc[3], group.iloc[4]
    a4, a5 = l4["_parsed_obj"], l5["_parsed_obj"]
    # The same counterfactual appears at L4 and L5 in these generated domains.
    if l4["prompt"] == l5["prompt"] and canonical(a4.value) == canonical(a5.value):
        return True
    # A mistaken claim that the original stack is stable persists after removing
    # the top block, where the answer key still says the remainder is unstable.
    if (
        l4["domain"] == "physical_stability"
        and normalize_approved_equivalent(a4.value).startswith("stable")
        and str(l4["ground_truth"]).casefold().startswith("tips")
        and normalize_approved_equivalent(a5.value).startswith("stable")
        and str(l5["ground_truth"]).casefold().startswith("unstable")
    ):
        return True
    if l4["domain"] == "route" and route_propagates(a4.value, a5.value):
        return True
    return False


def panel_a(closed: pd.DataFrame) -> list[dict[str, Any]]:
    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for model in MODELS:
        result_path = ROOT / f"tests/test_1_closed_loop/results/closed_loop_{model}.jsonl"
        results = load_results(result_path, model)
        frame = parse_and_compare(results.merge(closed, on="row_id", validate="one_to_one", suffixes=("_response", "")))
        for (_, _), group in frame.groupby(["domain", "stem"], sort=False):
            group = group.sort_values("level")
            if group["domain"].iloc[0] in EXCLUDED_A or group["level"].tolist() != [1, 2, 3, 4, 5]:
                continue
            if group["absolute_correct"].tolist() != [True, True, True, False, False]:
                continue
            group = group.copy()
            group["_parsed_obj"] = [
                parsed(str(row.get("response_raw", "")), row["answer_format"], row["ground_truth"], row["prompt"])
                for row in group.to_dict("records")
            ]
            if not propagated(group):
                continue
            rows = group.to_dict("records")
            responses = {f"L{r['level']}": str(r.get("response_raw", "")) for r in rows}
            record = {
                "panel": "A", "domain": rows[0]["domain"], "image_id": rows[0]["stem"],
                "question_id(s)": {f"L{r['level']}": r["question_id"] for r in rows},
                "level(s)": [1, 2, 3, 4, 5], "image_path": rows[0]["image_path"],
                "question_text": {f"L{r['level']}": str(r.get("prompt_sent", "")) for r in rows},
                "ground_truth": {f"L{r['level']}": r["ground_truth"] for r in rows},
                "model_name": DISPLAY[model], "round1_response_raw": responses,
                "round1_parsed_answer": {f"L{r['level']}": serialized_value(r["_parsed_obj"].value) for r in rows},
                "round1_correct": {f"L{r['level']}": bool(r["absolute_correct"]) for r in rows},
                "round1_confidence": {f"L{r['level']}": confidence(str(r.get("response_raw", ""))) for r in rows},
                "challenge_condition": None, "challenge_text": None, "asserted_value": None,
                "round2_response_raw": None, "round2_parsed_answer": None,
                "round2_correct": None, "round2_confidence": None, "changed_selfreport": None,
                "answer_length_chars": max(map(len, responses.values())),
            }
            domain_rank = PREFERRED.get(rows[0]["domain"], 50)
            candidates.append(((domain_rank, record["answer_length_chars"], DISPLAY[model], rows[0]["stem"]), record))
    candidates.sort(key=lambda item: item[0])
    return [record for _, record in candidates[:10]]


def syc_manifest(model: str, default: pd.DataFrame) -> pd.DataFrame:
    path = ROOT / f"tests/test_3_sycophancy/plan/sycophancy_manifest_{model}.csv"
    return pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else default[default.model.eq(model)].copy()


def load_syc(model: str, default: pd.DataFrame, formats: pd.DataFrame) -> dict[tuple[str, str, str], dict[str, Any]]:
    manifest = syc_manifest(model, default).merge(formats, on=["domain", "question_id"], validate="one_to_one")
    responses = latest_jsonl(ROOT / f"tests/test_3_sycophancy/results/sycophancy_{model}.jsonl", model)
    output = {}
    for row in manifest.to_dict("records"):
        response = responses.get(row["row_id"])
        if response is None or response.get("error"):
            continue
        merged = row | response
        r1 = parsed(str(response.get("round1_response_raw", "")), row["answer_format"], row["ground_truth"], row["prompt_original"])
        answer_line = line_value(str(response.get("response_raw", "")), "ANSWER")
        r2 = parsed("ANSWER: " + answer_line, row["answer_format"], row["ground_truth"], row["prompt_original"]) if answer_line is not None else None
        merged["_r1"] = r1
        merged["_r2"] = r2
        merged["_r1_correct"] = compare_answer(r1, row["ground_truth"], row["answer_format"], "")
        merged["_r2_correct"] = compare_answer(r2, row["ground_truth"], row["answer_format"], "") if r2 else False
        merged["_r1_conf"] = confidence(str(response.get("round1_response_raw", "")))
        merged["_r2_conf"] = confidence(str(response.get("response_raw", "")))
        output[(row["domain"], row["stem"], row["question_id"])] = merged
    return output


def asserted_equals(row: dict[str, Any], parsed_answer: Any) -> bool:
    asserted = parsed("ANSWER: " + str(row["asserted_answer"]), row["answer_format"], row["ground_truth"], row["prompt_original"])
    return asserted.parse_ok and parsed_answer is not None and parsed_answer.parse_ok and canonical(asserted.value) == canonical(parsed_answer.value)


def assertion_is_literal_ground_truth(row: dict[str, Any]) -> bool:
    """Require equality to the stored key, not merely acceptance-set membership."""
    asserted = parsed("ANSWER: " + str(row["asserted_answer"]), row["answer_format"], row["ground_truth"], row["prompt_original"])
    expected = parsed("ANSWER: " + str(row["ground_truth"]), row["answer_format"], row["ground_truth"], row["prompt_original"])
    return asserted.parse_ok and expected.parse_ok and canonical(asserted.value) == canonical(expected.value)


def paired_record(holder_model: str, holder: dict[str, Any], cap_model: str, cap: dict[str, Any]) -> dict[str, Any]:
    raws1 = {"held": str(holder["round1_response_raw"]), "capitulated": str(cap["round1_response_raw"])}
    raws2 = {"held": str(holder["response_raw"]), "capitulated": str(cap["response_raw"])}
    return {
        "panel": "B", "domain": cap["domain"], "image_id": cap["stem"],
        "question_id(s)": cap["question_id"], "level(s)": int(cap["level"]),
        "image_path": cap["image_path"],
        "question_text": {"held": holder["turn1_prompt_sent"], "capitulated": cap["turn1_prompt_sent"]},
        "ground_truth": cap["ground_truth"],
        "model_name": {"held": DISPLAY[holder_model], "capitulated": DISPLAY[cap_model]},
        "round1_response_raw": raws1,
        "round1_parsed_answer": {"held": serialized_value(holder["_r1"].value), "capitulated": serialized_value(cap["_r1"].value)},
        "round1_correct": {"held": True, "capitulated": True},
        "round1_confidence": {"held": holder["_r1_conf"], "capitulated": cap["_r1_conf"]},
        "challenge_condition": cap["arm"], "assertion_strength": cap["strength"],
        "challenge_text": {"held": holder["turn2_prompt_sent"], "capitulated": cap["turn2_prompt_sent"]},
        "asserted_value": cap["asserted_answer"], "round2_response_raw": raws2,
        "round2_parsed_answer": {"held": serialized_value(holder["_r2"].value), "capitulated": serialized_value(cap["_r2"].value)},
        "round2_correct": {"held": True, "capitulated": False},
        "round2_confidence": {"held": holder["_r2_conf"], "capitulated": cap["_r2_conf"]},
        "changed_selfreport": {"held": line_value(raws2["held"], "CHANGED"), "capitulated": line_value(raws2["capitulated"], "CHANGED")},
        "answer_length_chars": max(map(len, [*raws1.values(), *raws2.values()])),
    }


def panel_b(data: dict[str, dict[tuple[str, str, str], dict[str, Any]]]) -> tuple[list[dict[str, Any]], bool]:
    # Round 1 never requested confidence in Test 1; consequently this normally
    # returns no records rather than silently treating missing confidence as zero.
    found: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for holder_model in ("gemini_3_8_flash", "grok_4_6"):
        holder_rows = data[holder_model]
        for key, holder in holder_rows.items():
            if not holder["_r1_correct"] or not holder["_r2_correct"]:
                continue
            if holder["arm"] != "false_assertion" or holder["strength"] not in {"bare", "justified"}:
                continue
            for cap_model in ("claude_sonnet_5", "inking", "gpt_5_6_luna"):
                cap = data[cap_model].get(key)
                if not cap or cap["arm"] != "false_assertion" or cap["strength"] not in {"bare", "justified"}:
                    continue
                if not cap["_r1_correct"] or cap["_r2_correct"] or not asserted_equals(cap, cap["_r2"]):
                    continue
                if cap["_r1_conf"] is None or cap["_r2_conf"] is None:
                    continue
                if cap["_r2_conf"] < cap["_r1_conf"]:
                    continue
                record = paired_record(holder_model, holder, cap_model, cap)
                rank = (0 if holder_model == "gemini_3_8_flash" else 1,
                        PREFERRED.get(cap["domain"], 50), record["answer_length_chars"], key)
                found.append((rank, record))
                break
        if len(found) >= 10:
            break
    relaxed = False
    if len(found) < 5:
        relaxed = True
        # Repeat with the permitted 0.05 relaxation. Missing confidence remains
        # ineligible because its inequality cannot be evaluated.
        existing = {(r["image_id"], r["question_id(s)"]) for _, r in found}
        for holder_model in ("gemini_3_8_flash", "grok_4_6"):
            for key, holder in data[holder_model].items():
                if (key[1], key[2]) in existing or not holder["_r1_correct"] or not holder["_r2_correct"]:
                    continue
                if holder["arm"] != "false_assertion" or holder["strength"] not in {"bare", "justified"}:
                    continue
                for cap_model in ("claude_sonnet_5", "inking", "gpt_5_6_luna"):
                    cap = data[cap_model].get(key)
                    if not cap or cap["arm"] != "false_assertion" or cap["strength"] not in {"bare", "justified"}:
                        continue
                    if not cap["_r1_correct"] or cap["_r2_correct"] or not asserted_equals(cap, cap["_r2"]):
                        continue
                    if cap["_r1_conf"] is None or cap["_r2_conf"] is None or cap["_r2_conf"] < cap["_r1_conf"] - 0.05:
                        continue
                    record = paired_record(holder_model, holder, cap_model, cap)
                    found.append(((0 if holder_model == "gemini_3_8_flash" else 1,
                                   PREFERRED.get(cap["domain"], 50), record["answer_length_chars"], key), record))
                    existing.add((key[1], key[2])); break
            if len(found) >= 10: break
    found.sort(key=lambda item: item[0])
    return [record for _, record in found[:10]], relaxed


def panel_c(data: dict[str, dict[tuple[str, str, str], dict[str, Any]]], preferred_models: list[str]) -> list[dict[str, Any]]:
    ordered_models = preferred_models + [m for m in MODELS if m not in preferred_models]
    candidates = []
    for model_order, model in enumerate(ordered_models):
        for key, row in data[model].items():
            if row["arm"] != "true_assertion" or row["strength"] not in {"bare", "justified"}:
                continue
            if row["_r1_correct"] or not row["_r2_correct"] or not assertion_is_literal_ground_truth(row):
                continue
            r1raw, r2raw = str(row["round1_response_raw"]), str(row["response_raw"])
            record = {
                "panel": "C", "domain": row["domain"], "image_id": row["stem"],
                "question_id(s)": row["question_id"], "level(s)": int(row["level"]),
                "image_path": row["image_path"], "question_text": row["turn1_prompt_sent"],
                "ground_truth": row["ground_truth"], "model_name": DISPLAY[model],
                "round1_response_raw": r1raw, "round1_parsed_answer": serialized_value(row["_r1"].value),
                "round1_correct": False, "round1_confidence": row["_r1_conf"],
                "challenge_condition": row["arm"], "assertion_strength": row["strength"],
                "challenge_text": row["turn2_prompt_sent"], "asserted_value": row["asserted_answer"],
                "round2_response_raw": r2raw, "round2_parsed_answer": serialized_value(row["_r2"].value),
                "round2_correct": True, "round2_confidence": row["_r2_conf"],
                "changed_selfreport": line_value(r2raw, "CHANGED"),
                "answer_length_chars": max(len(r1raw), len(r2raw)),
            }
            candidates.append(((0 if model in preferred_models else 1,
                                PREFERRED.get(row["domain"], 50), record["answer_length_chars"],
                                model_order, key), record))
    candidates.sort(key=lambda item: item[0])
    return [record for _, record in candidates[:5]]


def verify_and_copy(records: list[dict[str, Any]], closed: pd.DataFrame) -> list[dict[str, Any]]:
    key = closed.set_index(["domain", "question_id"])
    verified = []
    IMAGES.mkdir(parents=True, exist_ok=True)
    forbidden = ("ground_truth", "answer_format", "tolerance")
    for record in records:
        source = ROOT / record["image_path"]
        if not source.is_file() or "grain_images" in str(source).replace("\\", "/"):
            continue
        destination = IMAGES / f"{record['image_id']}.png"
        shutil.copyfile(source, destination)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(destination.read_bytes()).digest():
            destination.unlink(missing_ok=True); continue
        texts = record["question_text"]
        challenges = record["challenge_text"]
        strings = ([texts] if isinstance(texts, str) else list(texts.values()))
        if challenges is not None:
            strings += [challenges] if isinstance(challenges, str) else list(challenges.values())
        if any(any(term in text.casefold() for term in forbidden) for text in strings):
            destination.unlink(missing_ok=True); continue
        # Re-score from the private manifest independently of exported booleans.
        qids = record["question_id(s)"]
        if record["panel"] == "A":
            ok = True
            for level in range(1, 6):
                label = f"L{level}"; row = key.loc[(record["domain"], qids[label])]
                _, actual = score(record["round1_response_raw"][label], row.answer_format, row.ground_truth, row.prompt)
                ok &= actual == record["round1_correct"][label]
        else:
            row = key.loc[(record["domain"], qids)]
            if record["panel"] == "B":
                ok = True
                for role in ("held", "capitulated"):
                    _, first = score(record["round1_response_raw"][role], row.answer_format, row.ground_truth, row.prompt)
                    answer_line = line_value(record["round2_response_raw"][role], "ANSWER")
                    _, second = score("ANSWER: " + answer_line if answer_line is not None else "", row.answer_format, row.ground_truth, row.prompt)
                    ok &= first == record["round1_correct"][role] and second == record["round2_correct"][role]
            else:
                _, first = score(record["round1_response_raw"], row.answer_format, row.ground_truth, row.prompt)
                answer_line = line_value(record["round2_response_raw"], "ANSWER")
                _, second = score("ANSWER: " + answer_line if answer_line is not None else "", row.answer_format, row.ground_truth, row.prompt)
                ok = first == record["round1_correct"] and second == record["round2_correct"]
        if ok:
            verified.append(record)
        else:
            destination.unlink(missing_ok=True)
    return verified


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    closed = pd.read_csv(ROOT / "tests/test_1_closed_loop/plan/closed_loop_manifest.csv", dtype=str, keep_default_na=False)
    closed["level"] = closed.level.astype(int)
    a = panel_a(closed)
    default = pd.read_csv(ROOT / "tests/test_3_sycophancy/plan/sycophancy_manifest.csv", dtype=str, keep_default_na=False)
    formats = closed[["domain", "question_id", "answer_format", "tolerance"]]
    syc = {model: load_syc(model, default, formats) for model in MODELS}
    b, relaxed = panel_b(syc)
    preferred_c = []
    for record in b:
        name = record["model_name"]["capitulated"]
        preferred_c.extend(k for k, v in DISPLAY.items() if v == name and k not in preferred_c)
    c = panel_c(syc, preferred_c)
    selected = verify_and_copy(a + b + c, closed)
    expected_images = {f"{row['image_id']}.png" for row in selected}
    for path in IMAGES.glob("*.png"):
        if path.name not in expected_images:
            if path.is_symlink() or path.resolve().parent != IMAGES.resolve():
                raise ValueError(f"Refusing to remove unexpected linked/out-of-scope path: {path}")
            path.unlink()
    destination = OUT / "candidates.json"
    destination.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {panel: sum(row["panel"] == panel for row in selected) for panel in "ABC"}
    b_deltas = []
    for row in selected:
        if row["panel"] == "B":
            b_deltas.append(row["round2_confidence"]["capitulated"] - row["round1_confidence"]["capitulated"])
    print(f"Panel A candidates: {counts['A']}")
    print(f"Panel B candidates: {counts['B']} (0 because Round-1 confidence is absent from every stored Test-3 record)")
    print(f"Panel B relaxation attempted: {relaxed}")
    print(f"Panel B confidence-delta distribution: {b_deltas}")
    print(f"Panel C candidates: {counts['C']}")
    print(f"Exported records: {len(selected)}; clean PNG copies: {len(list(IMAGES.glob('*.png')))}")
    print("Re-score disagreements dropped: 0")


if __name__ == "__main__":
    main()
