"""Build natural, constructed, and control Round-2 cross-examination rows."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from crossexam_common import (
    FAMILIES, answer_is_accepted, canonical_claim_string, load_jsonl_latest,
    parse_claim_string, read_csv, response_parts, stable_int,
)

COLUMNS = [
    "row_id", "model", "domain", "family", "stem", "image_path", "question_id",
    "arm", "peers_shown", "peer_answers", "peer_text", "round1_answer",
    "round1_correct", "ground_truth", "acceptance_set", "checkable_claims",
    "prompt_original",
]

OPPOSITES = {
    "yes": "no", "no": "yes", "true": "false", "false": "true",
    "clockwise": "counterclockwise", "counterclockwise": "clockwise",
    "convex": "non-convex", "non-convex": "convex",
    "unique": "not unique", "not unique": "unique",
    "orientable": "non-orientable", "non-orientable": "orientable",
    "stable": "unstable", "unstable": "stable",
    "high": "low", "low": "high", "inside": "outside", "outside": "inside",
    "equal": "not equal", "not equal": "equal",
}


def plausible_alternative(field: str, value: str, alternatives: list[str]) -> str:
    normalized = value.strip().casefold()
    if normalized in OPPOSITES:
        return OPPOSITES[normalized]
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if time_match:
        hour, minute = map(int, time_match.groups())
        minute += 1
        if minute == 60:
            minute = 0
            hour = hour % 12 + 1
        return f"{hour:02d}:{minute:02d}"
    try:
        number = Decimal(value.strip())
        delta = Decimal(10) if "nearest_10" in field else Decimal(1)
        candidate = number + delta
        if candidate < 0:
            candidate = max(Decimal(0), number - delta)
        return str(int(candidate)) if candidate == candidate.to_integral_value() else format(candidate, "f")
    except (InvalidOperation, ValueError):
        pass
    if re.fullmatch(r"[A-Z]", value.strip()):
        pool = [x for x in alternatives if re.fullmatch(r"[A-Z]", x) and x != value]
        return pool[0] if pool else chr((ord(value.strip()) - 65 + 1) % 6 + 65)
    if re.fullmatch(r"[A-Z]-[A-Z]", value.strip()):
        pool = [x for x in alternatives if re.fullmatch(r"[A-Z]-[A-Z]", x) and x != value]
        if pool:
            return pool[0]
    if alternatives:
        return alternatives[stable_int(field, value) % len(alternatives)]
    raise ValueError(f"No auditable plausible alternative for {field}={value}")


def constructed_answer(row: dict[str, str], round1_correct: bool) -> tuple[str, str]:
    if not round1_correct:
        return row["ground_truth"], "the stored visual sub-facts support this conclusion"
    claims = parse_claim_string(row["ground_truth"])
    specs = json.loads(row["checkable_claims"])
    if not claims or not specs:
        raise ValueError(f"Cannot construct a plausible wrong answer for {row['row_id']}")
    index = stable_int(row["domain"], row["stem"], "constructed") % len(specs)
    selected = specs[index]
    field = selected["field"]
    wrong = plausible_alternative(field, claims[field], list(selected.get("alternatives", [])))
    if wrong == claims[field]:
        raise ValueError(f"Constructed answer did not change {field} for {row['row_id']}")
    claims[field] = wrong
    return canonical_claim_string(claims), f"the visible evidence makes {field.replace('_', ' ')} equal to {wrong}"


def natural_peer_ids(models: list[str], target: str, domain: str, stem: str) -> list[str]:
    ordered = sorted(models, key=lambda model: (stable_int(domain, stem, model), model))
    base = ordered[:3]
    if target not in base:
        return base
    replacement = next(model for model in ordered[3:] if model != target)
    return [replacement if model == target else model for model in base]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round1-manifest", type=Path, default=TEST_ROOT / "plan/crossexam_manifest.csv")
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument("--output", type=Path, default=TEST_ROOT / "plan/crossexam_round2_manifest.csv")
    parser.add_argument("--skip-log", type=Path, default=TEST_ROOT / "plan/crossexam_round2_skipped.csv")
    args = parser.parse_args()

    manifest = read_csv(args.round1_manifest)
    models = sorted(manifest["model"].unique())
    if len(models) < 4:
        raise ValueError("Natural-peer construction requires at least four models")
    expected_per_model = manifest.groupby("model").size()
    if expected_per_model.nunique() != 1:
        raise ValueError(f"Round-1 manifest is unbalanced: {expected_per_model.to_dict()}")

    records: dict[str, dict[str, dict[str, Any]]] = {}
    for model in models:
        path = args.results_dir / f"crossexam_r1_{model}.jsonl"
        latest = load_jsonl_latest(path, model)
        expected = set(manifest.loc[manifest["model"] == model, "row_id"])
        successful = {
            key for key, row in latest.items()
            if not row.get("error")
            and str(row.get("response_raw", "")).strip()
            and str(row.get("response_raw", "")).strip().casefold() not in {"none", "null"}
        }
        if successful != expected:
            raise ValueError(f"Round 1 incomplete for {model}: {len(successful & expected):,}/{len(expected):,}")
        records[model] = latest

    indexed = {
        (row["model"], row["domain"], row["stem"]): row
        for row in manifest.to_dict("records")
    }
    parsed: dict[tuple[str, str, str], dict[str, Any]] = {}
    skipped: list[dict[str, str]] = []
    for key, row in indexed.items():
        record = records[row["model"]][row["row_id"]]
        parts = response_parts(str(record["response_raw"]))
        expected_fields = set(parse_claim_string(row["ground_truth"]))
        parsed_fields = set(parse_claim_string(parts["answer"] or ""))
        if not parts["parse_ok"] or parsed_fields != expected_fields:
            skipped.append({
                "row_id": row["row_id"], "model": row["model"],
                "reason": "round1_unparsed_or_wrong_field_schema",
            })
            continue
        parts["response_raw"] = str(record["response_raw"])
        parts["correct"] = answer_is_accepted(parts["answer"], row["acceptance_set"])
        parsed[key] = parts

    unique_images = sorted({(row["domain"], row["stem"]) for row in indexed.values()})
    control_count = round(len(unique_images) / 3)
    control_images = set(sorted(
        unique_images,
        key=lambda item: (stable_int(item[0], item[1], "control"), item),
    )[:control_count])

    output: list[dict[str, str]] = []
    for key, target in indexed.items():
        model, domain, stem = key
        if key not in parsed:
            continue
        target_parts = parsed[key]
        base = {
            "model": model, "domain": domain, "family": FAMILIES[domain],
            "stem": stem, "image_path": target["image_path"],
            "question_id": target["question_id"], "round1_answer": target_parts["answer"],
            "round1_correct": str(bool(target_parts["correct"])).lower(),
            "ground_truth": target["ground_truth"], "acceptance_set": target["acceptance_set"],
            "checkable_claims": target["checkable_claims"], "prompt_original": target["prompt"],
        }

        peer_models = natural_peer_ids(models, model, domain, stem)
        peer_parts = [parsed.get((peer, domain, stem)) for peer in peer_models]
        if all(peer_parts):
            raw_texts = [part["response_raw"] for part in peer_parts if part]
            peer_answers = [part["answer"] for part in peer_parts if part]
            display = "Here are three independent peer responses:\n\n" + "\n\n".join(
                f"PEER {index + 1} ({peer}):\n{text}"
                for index, (peer, text) in enumerate(zip(peer_models, raw_texts))
            )
            output.append({
                "row_id": f"{model}:{domain}:{stem}:natural", **base, "arm": "natural",
                "peers_shown": json.dumps(peer_models, separators=(",", ":")),
                "peer_answers": json.dumps(peer_answers, ensure_ascii=False, separators=(",", ":")),
                "peer_text": display,
            })
        else:
            skipped.append({"row_id": target["row_id"], "model": model, "reason": "fewer_than_three_parsed_natural_peers"})

        asserted, reason = constructed_answer(target, bool(target_parts["correct"]))
        synthetic = ["synthetic_peer_1", "synthetic_peer_2", "synthetic_peer_3"]
        synthetic_text = "Three independent peers agree:\n\n" + "\n\n".join(
            f"PEER {index}:\nANSWER: {asserted}\nJUSTIFICATION: {reason}."
            for index in range(1, 4)
        )
        output.append({
            "row_id": f"{model}:{domain}:{stem}:constructed", **base, "arm": "constructed",
            "peers_shown": json.dumps(synthetic, separators=(",", ":")),
            "peer_answers": json.dumps([asserted] * 3, ensure_ascii=False, separators=(",", ":")),
            "peer_text": synthetic_text,
        })

        if (domain, stem) in control_images:
            output.append({
                "row_id": f"{model}:{domain}:{stem}:control_reask", **base,
                "arm": "control_reask", "peers_shown": "[]", "peer_answers": "[]",
                "peer_text": "Please give your final answer in the same format.",
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(output)
    with args.skip_log.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "model", "reason"])
        writer.writeheader()
        writer.writerows(skipped)
    counts: dict[str, int] = {}
    for row in output:
        counts[row["arm"]] = counts.get(row["arm"], 0) + 1
    print(f"Round-2 rows: {len(output):,}")
    for arm, count in sorted(counts.items()):
        print(f"{arm}: {count:,}")
    print(f"Skipped rows logged: {len(skipped):,}")


if __name__ == "__main__":
    main()
