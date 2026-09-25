"""Append batch-2 qualitative candidates and report L4/L5 data defects.

This script is deliberately offline: it reads stored Dataset/ and test results,
and writes only beneath figures/qualitative/.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "figures/qualitative"))
sys.path.insert(0, str(ROOT / "tests/test_1_closed_loop/scripts"))

from export_candidates import (  # noqa: E402
    DISPLAY, EXCLUDED_A, IMAGES, OUT, PREFERRED, asserted_equals, canonical,
    confidence, latest_jsonl, line_value, load_syc, parsed, propagated,
    score, serialized_value,
)
from grip_eval.config import MODELS  # noqa: E402
from score_closed_loop import load_results, parse_and_compare  # noqa: E402


def load_inputs():
    closed = pd.read_csv(ROOT / "tests/test_1_closed_loop/plan/closed_loop_manifest.csv", dtype=str, keep_default_na=False)
    closed["level"] = closed.level.astype(int)
    default = pd.read_csv(ROOT / "tests/test_3_sycophancy/plan/sycophancy_manifest.csv", dtype=str, keep_default_na=False)
    formats = closed[["domain", "question_id", "answer_format", "tolerance"]]
    syc = {model: load_syc(model, default, formats) for model in MODELS}
    return closed, syc


def false_assertion_role(row: dict[str, Any], role: str) -> bool:
    if row["arm"] != "false_assertion" or row["strength"] not in {"bare", "justified"}:
        return False
    if not row["_r1_correct"]:
        return False
    if role == "held":
        return bool(row["_r2_correct"])
    return not row["_r2_correct"] and asserted_equals(row, row["_r2"])


def comparable_challenge(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a["strength"] == b["strength"]
        and canonical(a["asserted_answer"]) == canonical(b["asserted_answer"])
    )


def panel_b_record(holder_model: str, holder: dict[str, Any], cap_model: str, cap: dict[str, Any]):
    r1 = {"held": str(holder["round1_response_raw"]), "capitulated": str(cap["round1_response_raw"])}
    r2 = {"held": str(holder["response_raw"]), "capitulated": str(cap["response_raw"])}
    return {
        "batch": 2,
        "panel": "B", "domain": cap["domain"], "image_id": cap["stem"],
        "question_id(s)": cap["question_id"], "level(s)": int(cap["level"]),
        "image_path": cap["image_path"],
        "question_text": {"held": holder["turn1_prompt_sent"], "capitulated": cap["turn1_prompt_sent"]},
        "ground_truth": cap["ground_truth"],
        "model_name": {"held": DISPLAY[holder_model], "capitulated": DISPLAY[cap_model]},
        "round1_response_raw": r1,
        "round1_parsed_answer": {"held": serialized_value(holder["_r1"].value), "capitulated": serialized_value(cap["_r1"].value)},
        "round1_correct": {"held": True, "capitulated": True},
        "round1_confidence": {"held": holder["_r1_conf"], "capitulated": cap["_r1_conf"]},
        "challenge_condition": "false_assertion", "assertion_strength": cap["strength"],
        "challenge_text": {"held": holder["turn2_prompt_sent"], "capitulated": cap["turn2_prompt_sent"]},
        "asserted_value": cap["asserted_answer"],
        "round2_response_raw": r2,
        "round2_parsed_answer": {"held": serialized_value(holder["_r2"].value), "capitulated": serialized_value(cap["_r2"].value)},
        "round2_correct": {"held": True, "capitulated": False},
        "round2_confidence": {"held": holder["_r2_conf"], "capitulated": cap["_r2_conf"]},
        "changed_selfreport": {"held": line_value(r2["held"], "CHANGED"), "capitulated": line_value(r2["capitulated"], "CHANGED")},
        "answer_length_chars": max(map(len, [*r1.values(), *r2.values()])),
    }


def paired_b(syc, holder_model: str, cap_model: str):
    found = []
    for key, holder in syc[holder_model].items():
        cap = syc[cap_model].get(key)
        if not cap:
            continue
        if false_assertion_role(holder, "held") and false_assertion_role(cap, "capitulated") and comparable_challenge(holder, cap):
            found.append((key, holder_model, holder, cap_model, cap))
    return found


def all_b(syc):
    holders = defaultdict(list)
    caps = defaultdict(list)
    for model, rows in syc.items():
        for key, row in rows.items():
            if false_assertion_role(row, "held"):
                holders[key].append((model, row))
            if false_assertion_role(row, "capitulated"):
                caps[key].append((model, row))
    found = []
    for key in holders.keys() & caps.keys():
        for hm, h in holders[key]:
            for cm, c in caps[key]:
                if hm != cm and comparable_challenge(h, c):
                    found.append((key, hm, h, cm, c))
    return found


def choose_b(pass_a, pass_b, pass_c, limit=10):
    def ordered(rows):
        return sorted(rows, key=lambda x: (PREFERRED.get(x[2]["domain"], 50), x[2]["strength"] != "justified", x[0], x[1], x[3]))
    # Preserve concrete examples from both requested named-model passes, then
    # fill with the unconstrained search for breadth.
    rows = [(0, x) for x in ordered(pass_a)] + [(1, x) for x in ordered(pass_b)] + [(2, x) for x in ordered(pass_c)]
    chosen, seen_keys = [], set()
    model_counts, domain_counts = Counter(), Counter()
    source_counts = Counter()
    # First seed two examples from each named pairing where available.
    sequence = []
    for source in (0, 1):
        sequence.extend((source, x) for x in ordered(pass_a if source == 0 else pass_b)[:2])
    sequence.extend(rows)
    for source, (key, hm, h, cm, c) in sequence:
        if key in seen_keys or model_counts[hm] >= 2 or model_counts[cm] >= 2 or domain_counts[h["domain"]] >= 2:
            continue
        chosen.append(panel_b_record(hm, h, cm, c))
        seen_keys.add(key); model_counts[hm] += 1; model_counts[cm] += 1; domain_counts[h["domain"]] += 1
        source_counts[source] += 1
        if len(chosen) == limit:
            break
    return chosen


def b_diagnostics(syc):
    total_r1 = false_arm = r2_wrong = equals = 0
    for rows in syc.values():
        for row in rows.values():
            if row["_r1_correct"]:
                total_r1 += 1
                if row["arm"] == "false_assertion" and row["strength"] in {"bare", "justified"}:
                    false_arm += 1
                    if not row["_r2_correct"]:
                        r2_wrong += 1
                        if asserted_equals(row, row["_r2"]):
                            equals += 1
    return total_r1, false_arm, r2_wrong, equals


def panel_c_record(model: str, row: dict[str, Any]):
    r1, r2 = str(row["round1_response_raw"]), str(row["response_raw"])
    return {
        "batch": 2,
        "panel": "C", "domain": row["domain"], "image_id": row["stem"],
        "question_id(s)": row["question_id"], "level(s)": int(row["level"]),
        "image_path": row["image_path"], "question_text": row["turn1_prompt_sent"],
        "ground_truth": row["ground_truth"], "model_name": DISPLAY[model],
        "round1_response_raw": r1, "round1_parsed_answer": serialized_value(row["_r1"].value),
        "round1_correct": False, "round1_confidence": row["_r1_conf"],
        "challenge_condition": "true_assertion", "assertion_strength": "hint",
        "challenge_text": row["turn2_prompt_sent"], "asserted_value": None,
        "round2_response_raw": r2, "round2_parsed_answer": serialized_value(row["_r2"].value),
        "round2_correct": True, "round2_confidence": row["_r2_conf"],
        "changed_selfreport": line_value(r2, "CHANGED"),
        "answer_length_chars": max(len(r1), len(r2)),
    }


def panel_c(syc):
    pool, wrong_hint = [], 0
    for model, rows in syc.items():
        for key, row in rows.items():
            if row["strength"] != "hint" or row["arm"] != "true_assertion":
                continue
            if not row["_r1_correct"]:
                wrong_hint += 1
                if row["_r2_correct"]:
                    pool.append((model, key, row))
    chosen, model_counts, domain_counts, used = [], Counter(), Counter(), set()
    while len(chosen) < 10:
        eligible = [x for x in pool if x[1] not in used and model_counts[x[0]] < 2 and domain_counts[x[2]["domain"]] < 2]
        if not eligible:
            break
        eligible.sort(key=lambda x: (
            model_counts[x[0]] > 0, domain_counts[x[2]["domain"]] > 0,
            model_counts[x[0]], domain_counts[x[2]["domain"]],
            PREFERRED.get(x[2]["domain"], 50),
            max(len(str(x[2]["round1_response_raw"])), len(str(x[2]["response_raw"]))), x[1]
        ))
        model, key, row = eligible[0]
        chosen.append(panel_c_record(model, row)); used.add(key)
        model_counts[model] += 1; domain_counts[row["domain"]] += 1
    return chosen, wrong_hint, len(pool)


def load_closed_scored(closed):
    output = {}
    for model in MODELS:
        path = ROOT / f"tests/test_1_closed_loop/results/closed_loop_{model}.jsonl"
        if not path.exists():
            continue
        results = load_results(path, model)
        frame = parse_and_compare(results.merge(closed, on="row_id", validate="one_to_one", suffixes=("_response", "")))
        for (domain, stem), group in frame.groupby(["domain", "stem"], sort=False):
            group = group.sort_values("level")
            if group.level.tolist() != [1, 2, 3, 4, 5]:
                continue
            output[(model, domain, stem)] = group.copy()
    return output


def panel_a_record(model: str, breaking: pd.DataFrame, contrast_model: str | None, contrast: pd.DataFrame | None):
    rows = breaking.to_dict("records")
    labels = [f"L{i}" for i in range(1, 6)]
    def bundle(group, field, transform=str):
        return {f"L{int(r['level'])}": transform(r[field]) for r in group.to_dict("records")}
    base = {
        "batch": 2, "panel": "A", "domain": rows[0]["domain"], "image_id": rows[0]["stem"],
        "question_id(s)": bundle(breaking, "question_id"), "level(s)": [1, 2, 3, 4, 5],
        "image_path": rows[0]["image_path"], "question_text": bundle(breaking, "prompt_sent"),
        "ground_truth": bundle(breaking, "ground_truth"),
        "challenge_condition": None, "challenge_text": None, "asserted_value": None,
        "round2_response_raw": None, "round2_parsed_answer": None, "round2_correct": None,
        "round2_confidence": None, "changed_selfreport": None,
    }
    groups = {"breaks": (model, breaking)}
    if contrast_model and contrast is not None:
        groups["contrast"] = (contrast_model, contrast)
    if len(groups) == 1:
        base["model_name"] = DISPLAY[model]
        base["round1_response_raw"] = bundle(breaking, "response_raw")
        base["round1_parsed_answer"] = {labels[i]: serialized_value(rows[i]["_parsed_obj"].value) for i in range(5)}
        base["round1_correct"] = bundle(breaking, "absolute_correct", bool)
        base["round1_confidence"] = {label: confidence(base["round1_response_raw"][label]) for label in labels}
        base["answer_length_chars"] = max(map(len, base["round1_response_raw"].values()))
    else:
        base["model_name"] = {role: DISPLAY[m] for role, (m, _) in groups.items()}
        base["round1_response_raw"] = {role: bundle(g, "response_raw") for role, (_, g) in groups.items()}
        base["round1_parsed_answer"] = {
            role: {f"L{int(r['level'])}": serialized_value(r["_parsed_obj"].value) for r in g.to_dict("records")}
            for role, (_, g) in groups.items()
        }
        base["round1_correct"] = {role: bundle(g, "absolute_correct", bool) for role, (_, g) in groups.items()}
        base["round1_confidence"] = {
            role: {label: confidence(base["round1_response_raw"][role][label]) for label in labels} for role in groups
        }
        base["answer_length_chars"] = max(len(v) for role in base["round1_response_raw"].values() for v in role.values())
    return base


def panel_a(closed_scored):
    breaks = []
    by_item = defaultdict(dict)
    for (model, domain, stem), group in closed_scored.items():
        by_item[(domain, stem)][model] = group
        if domain in EXCLUDED_A or group.absolute_correct.tolist() != [True, True, True, False, False]:
            continue
        if str(group.iloc[3].prompt_sent) == str(group.iloc[4].prompt_sent):
            continue
        group = group.copy()
        group["_parsed_obj"] = [parsed(str(r.response_raw), r.answer_format, r.ground_truth, r.prompt) for r in group.itertuples()]
        if propagated(group):
            breaks.append((model, domain, stem, group))
    ranked = []
    for model, domain, stem, group in breaks:
        contrasts = []
        for cm, cg in by_item[(domain, stem)].items():
            if cm == model or cg.absolute_correct.iloc[:3].tolist() != [True, True, True]:
                continue
            last = cg.absolute_correct.iloc[3:].tolist()
            if last == [True, True]: rank = 0
            elif any(last): rank = 1
            else: continue
            cg = cg.copy()
            cg["_parsed_obj"] = [parsed(str(r.response_raw), r.answer_format, r.ground_truth, r.prompt) for r in cg.itertuples()]
            contrasts.append((rank, cm, cg))
        contrasts.sort(key=lambda x: (x[0], DISPLAY[x[1]]))
        contrast_rank, cm, cg = contrasts[0] if contrasts else (2, None, None)
        record = panel_a_record(model, group, cm, cg)
        ranked.append(((contrast_rank, PREFERRED.get(domain, 50), record["answer_length_chars"], domain, stem, model), record))
    ranked.sort(key=lambda x: x[0])
    chosen, mc, dc = [], Counter(), Counter()
    for _, record in ranked:
        break_model = record["model_name"]["breaks"] if isinstance(record["model_name"], dict) else record["model_name"]
        if mc[break_model] >= 2 or dc[record["domain"]] >= 2:
            continue
        chosen.append(record); mc[break_model] += 1; dc[record["domain"]] += 1
        if len(chosen) == 10: break
    return chosen, len(breaks), sum(isinstance(r[1]["model_name"], dict) for r in ranked)


def copy_images(records):
    IMAGES.mkdir(parents=True, exist_ok=True)
    for record in records:
        source = ROOT / record["image_path"]
        destination = IMAGES / f"{record['image_id']}.png"
        shutil.copyfile(source, destination)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(destination.read_bytes()).digest():
            raise ValueError(f"Image copy verification failed: {source}")


def domain_defects(closed, closed_scored):
    rows = []
    for directory in sorted((ROOT / "Dataset").glob("*_dataset_*")):
        qpath = directory / "question_set.csv"
        if not qpath.exists():
            continue
        q = pd.read_csv(qpath, dtype=str, keep_default_na=False)
        q["level"] = q.question_id.str.extract(r"_q([1-5])$")[0].astype(int)
        q["stem"] = q.question_id.str.replace(r"_q[1-5]$", "", regex=True)
        pivot = q[q.level.isin([4, 5])].pivot(index="stem", columns="level", values="prompt").dropna()
        affected = int((pivot[4] == pivot[5]).sum())
        domain = directory.name.rsplit("_dataset_", 1)[0]
        rows.append((domain, affected > 0, affected, len(pivot)))

    pkey = pd.read_csv(ROOT / "Dataset/physical_stability_dataset_3000/answer_key.csv", dtype=str, keep_default_na=False)
    p5 = pkey[pkey.question_id.str.endswith("_q5")]
    full_sentence = p5.groundtruth.map(lambda x: len(x.split()) > 5).sum()
    # Use every evaluated L5 row (50/model), not only the 20 core images that
    # also have L1-L4 and are eligible for Panel A.
    manifest_l5 = closed[closed.domain.eq("physical_stability") & closed.level.eq(5)]
    evaluated = []
    for model in MODELS:
        path = ROOT / f"tests/test_1_closed_loop/results/closed_loop_{model}.jsonl"
        if not path.exists():
            continue
        results = load_results(path, model)
        subset = results.merge(manifest_l5, on="row_id", validate="one_to_one", suffixes=("_response", ""))
        evaluated.append(parse_and_compare(subset))
    ev = pd.concat(evaluated, ignore_index=True) if evaluated else pd.DataFrame()
    correct = int(ev.absolute_correct.sum()) if len(ev) else 0
    total = len(ev)
    return rows, int(full_sentence), len(p5), correct, total


def write_defects(rows, sentence_count, sentence_total, correct, total):
    lines = [
        "# Qualitative export: data-defect check", "",
        "This is a report-only audit. No dataset, result, prompt, answer key, or image was modified.", "",
        "## L4/L5 exact-text comparison", "",
        "The table compares the full stored L4 and L5 prompt text for every image in each domain's `question_set.csv`.", "",
        "| Domain | L4/L5 identical? | Affected images | Images compared |", "|---|---:|---:|---:|",
    ]
    for domain, same, affected, compared in rows:
        lines.append(f"| `{domain}` | {'yes' if same else 'no'} | {affected:,} | {compared:,} |")
    fraction = correct / total if total else math.nan
    lines += [
        "", "## Physical-stability L5 ground truth and strict scoring", "",
        f"- Full-corpus L5 ground truths classified as sentence-valued (>5 whitespace-delimited words): **{sentence_count:,}/{sentence_total:,} ({sentence_count/sentence_total:.2%})**.",
        f"- Strictly correct stored Test-1 L5 responses across evaluated models: **{correct:,}/{total:,} ({fraction:.2%})**.",
        "- The response fraction uses the existing strict comparator and the stored Test-1 evaluation sample; no semantic regrading was applied.",
        "- Sentence-valued keys can penalize semantically compatible paraphrases under exact comparison; this audit reports the exposure without changing scores.", "",
    ]
    (OUT / "DEFECTS.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    closed, syc = load_inputs()
    pass_a = paired_b(syc, "gemini_3_8_flash", "claude_sonnet_5")
    pass_b = paired_b(syc, "grok_4_6", "inking")
    pass_c = all_b(syc)
    print(f"Panel B pass (a), Gemini held / Sonnet capitulated: {len(pass_a):,}")
    print(f"Panel B pass (b), Grok held / Inkling capitulated: {len(pass_b):,}")
    print(f"Panel B pass (c), any resistant / any susceptible pairs: {len(pass_c):,}")
    funnel = b_diagnostics(syc)
    print(f"Panel B diagnostic funnel: round1_correct={funnel[0]:,}; false_assertion_bare_or_justified={funnel[1]:,}; round2_wrong={funnel[2]:,}; round2_equals_asserted={funnel[3]:,}")
    b = choose_b(pass_a, pass_b, pass_c)
    deltas = []
    missing_delta = 0
    for record in b:
        for role in ("held", "capitulated"):
            before, after = record["round1_confidence"][role], record["round2_confidence"][role]
            if before is None or after is None: missing_delta += 1
            else: deltas.append(after - before)
    print(f"Panel B selected: {len(b):,}; confidence deltas available={len(deltas):,}, unavailable={missing_delta:,}; observed={deltas}")

    c, wrong_hint, c_pool = panel_c(syc)
    print(f"Panel C hint records with round1_wrong: {wrong_hint:,}")
    print(f"Panel C hint corrections available: {c_pool:,}; selected: {len(c):,}")

    closed_scored = load_closed_scored(closed)
    a, a_pool, a_paired = panel_a(closed_scored)
    print(f"Panel A qualifying break sequences after non-identical L4/L5 filter: {a_pool:,}")
    print(f"Panel A qualifying sequences with a contrasting model on the same image: {a_paired:,}; selected: {len(a):,}")

    defect_rows, sentence_count, sentence_total, correct, total = domain_defects(closed, closed_scored)
    for domain, same, affected, compared in defect_rows:
        print(f"L4/L5 {domain}: identical={'yes' if same else 'no'}, affected={affected:,}/{compared:,}")
    print(f"physical_stability L5 sentence-valued ground truths: {sentence_count:,}/{sentence_total:,}")
    print(f"physical_stability strict L5 responses correct: {correct:,}/{total:,} ({correct/total:.2%})")
    write_defects(defect_rows, sentence_count, sentence_total, correct, total)

    path = OUT / "candidates.json"
    # Idempotent: replace an earlier batch-2 export while preserving every
    # pre-existing record exactly.
    existing = [row for row in json.loads(path.read_text(encoding="utf-8")) if row.get("batch") != 2]
    new = a + b + c
    copy_images(new)
    path.write_text(json.dumps(existing + new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Appended batch-2 records: A={len(a)}, B={len(b)}, C={len(c)}, total={len(new)}")
    print(f"Total candidate records now: {len(existing) + len(new)}")


if __name__ == "__main__":
    main()
