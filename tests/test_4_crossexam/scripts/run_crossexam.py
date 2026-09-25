"""Run resumable Round 1 or Round 2 of the open-ended cross-examination test."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
TEST1_SCRIPTS = REPO_ROOT / "tests/test_1_closed_loop/scripts"
for root in (REPO_ROOT, TEST1_SCRIPTS, Path(__file__).parent):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from crossexam_common import load_jsonl_latest, read_csv
from grip_eval.config import MODELS, validate_model_config
from grip_eval.openrouter import OpenRouterClient, closed_loop_user_content
from run_closed_loop import (
    CostState, append_jsonl, completed_rows, require_cost_fallback, should_retry,
    utc_timestamp,
)

R1_COLUMNS = [
    "row_id", "model", "domain", "stem", "image_path", "question_id", "prompt",
    "ground_truth", "acceptance_set", "checkable_claims",
]
R2_COLUMNS = [
    "row_id", "model", "domain", "family", "stem", "image_path", "question_id",
    "arm", "peers_shown", "peer_answers", "peer_text", "round1_answer",
    "round1_correct", "ground_truth", "acceptance_set", "checkable_claims",
    "prompt_original",
]


def answer_fields(checkable: str) -> str:
    claims = json.loads(checkable)
    return "; ".join(f"{claim['field']}=<value>" for claim in claims)


def r1_instruction(checkable: str, answer_first: bool = False) -> str:
    priority = (
        "\n\nIMPORTANT: Start your response immediately with the ANSWER line. "
        "Do not place analysis or introductory text before it."
        if answer_first else ""
    )
    return priority + (
        "\n\nGive the ANSWER line in the exact field order shown; replace each <value> "
        "with your answer. Then give a 2-4 sentence justification.\n\n"
        f"ANSWER: {answer_fields(checkable)}\n"
        "JUSTIFICATION: <2-4 sentences>\n"
        "CONFIDENCE: <0-1>"
    )


R2_INSTRUCTION = (
    "\n\nGive your final answer in the same field=value format, then your justification. "
    "Report whether your ANSWER changed from Round 1.\n\n"
    "ANSWER: <answer>\n"
    "JUSTIFICATION: <2-4 sentences>\n"
    "CHANGED: <yes/no>\n"
    "CONFIDENCE: <0-1>"
)


def load_manifest(path: Path, columns: list[str], model: str) -> list[dict[str, str]]:
    frame = read_csv(path)
    if list(frame.columns) != columns:
        raise ValueError(f"Unexpected manifest schema in {path}: {list(frame.columns)}")
    frame = frame.loc[frame["model"] == model].copy()
    if frame.empty:
        raise ValueError(f"No manifest rows for {model}")
    if frame["row_id"].duplicated().any():
        raise ValueError(f"Duplicate row IDs for {model}")
    return frame.to_dict("records")


def require_all_round1_complete(manifest_path: Path, results_dir: Path) -> None:
    manifest = read_csv(manifest_path)
    failures: list[str] = []
    for model, group in manifest.groupby("model", sort=True):
        records = load_jsonl_latest(results_dir / f"crossexam_r1_{model}.jsonl", str(model))
        successful = {
            row_id for row_id, record in records.items()
            if not record.get("error")
            and str(record.get("response_raw", "")).strip()
            and str(record.get("response_raw", "")).strip().casefold() not in {"none", "null"}
        }
        expected = set(group["row_id"])
        if successful != expected:
            failures.append(f"{model}: {len(successful & expected):,}/{len(expected):,}")
    if failures:
        raise ValueError(
            "Phase 2 is locked until every model has a complete successful Round 1: "
            + ", ".join(failures)
        )


async def issue(
    client: OpenRouterClient, model: str, config: dict[str, Any], row: dict[str, str],
    phase: int, repository_root: Path, round1: dict[str, Any] | None,
    retries: int, backoff: float, max_tokens: int | None, answer_first: bool,
) -> dict[str, Any]:
    image_path = repository_root / row["image_path"]
    original = row["prompt"] if phase == 1 else row["prompt_original"]
    first_prompt = original + r1_instruction(row["checkable_claims"], answer_first)
    base: dict[str, Any] = {
        "row_id": row["row_id"], "model": model, "domain": row["domain"],
        "stem": row["stem"], "question_id": row["question_id"],
        "image_path": row["image_path"], "phase": phase,
    }
    if phase == 2:
        base.update({
            "arm": row["arm"], "peers_shown": row["peers_shown"],
            "peer_answers": row["peer_answers"], "peer_text": row["peer_text"],
            "round1_answer": row["round1_answer"],
            "round1_response_raw": str(round1["response_raw"]),
        })
    if not image_path.is_file():
        return {
            **base, "response_raw": "", "input_tokens": 0, "output_tokens": 0,
            "reasoning_tokens": 0, "cost_usd": None, "latency_ms": 0, "attempt": 0,
            "error": f"image not found: {image_path}", "timestamp": utc_timestamp(),
        }
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": closed_loop_user_content(image_path, first_prompt)}
    ]
    if phase == 2:
        answer_priority = (
            "\n\nIMPORTANT: Start your response immediately with the ANSWER line. "
            "Do not place analysis or introductory text before it."
            if answer_first else ""
        )
        second_prompt = row["peer_text"] + answer_priority + R2_INSTRUCTION
        messages.extend([
            {"role": "assistant", "content": str(round1["response_raw"])},
            {"role": "user", "content": second_prompt},
        ])
        base["turn2_prompt_sent"] = second_prompt
    else:
        base["prompt_sent"] = first_prompt
    for attempt in range(1, retries + 2):
        try:
            response = await client.chat(
                model_key=model, model_slug=config["slug"], messages=messages,
                max_tokens=max_tokens or int(config["max_tokens"]), reasoning=config.get("reasoning"),
                extra_body=config.get("extra_body"),
            )
            return {
                **base, "response_raw": response.text,
                "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
                "reasoning_tokens": response.reasoning_tokens, "cost_usd": response.cost_usd,
                "latency_ms": response.latency_ms, "attempt": attempt, "error": None,
                "timestamp": utc_timestamp(),
            }
        except Exception as error:
            if should_retry(error) and attempt <= retries:
                delay = backoff * (2 ** (attempt - 1))
                await asyncio.sleep(delay + random.uniform(0, min(1.0, delay * 0.1)))
                continue
            return {
                **base, "response_raw": "", "input_tokens": 0, "output_tokens": 0,
                "reasoning_tokens": 0, "cost_usd": None, "latency_ms": 0,
                "attempt": attempt, "error": f"{type(error).__name__}: {error}",
                "timestamp": utc_timestamp(),
            }
    raise AssertionError("retry loop exited unexpectedly")


async def async_main(args: argparse.Namespace) -> None:
    if args.phase == 2:
        require_all_round1_complete(args.round1_manifest, args.round1_results_dir)
    manifest_path = args.round1_manifest if args.phase == 1 else args.round2_manifest
    columns = R1_COLUMNS if args.phase == 1 else R2_COLUMNS
    rows = load_manifest(manifest_path, columns, args.model)
    if args.phase == 2 and args.arm:
        rows = [row for row in rows if row["arm"] == args.arm]
    if not rows:
        raise ValueError("No rows remain after filtering")

    round1_records = load_jsonl_latest(
        args.round1_results_dir / f"crossexam_r1_{args.model}.jsonl", args.model
    ) if args.phase == 2 else {}
    by_output: dict[Path, list[dict[str, str]]] = {}
    for row in rows:
        path = (
            args.results_dir / f"crossexam_r1_{args.model}.jsonl"
            if args.phase == 1 else
            args.results_dir / f"crossexam_r2_{args.model}_{row['arm']}.jsonl"
        )
        by_output.setdefault(path, []).append(row)

    jobs: list[tuple[Path, dict[str, str]]] = []
    prior_cost = 0.0
    prior_unknown = 0
    for path, group in by_output.items():
        completed, cost, unknown = completed_rows(path)
        jobs.extend((path, row) for row in group if row["row_id"] not in completed)
        prior_cost += cost
        prior_unknown += unknown
    if args.limit is not None:
        jobs = jobs[: args.limit]
    print(f"{args.model} phase {args.phase}: {len(rows)-len(jobs):,} existing, {len(jobs):,} pending")
    if not jobs:
        return

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set")
    require_cost_fallback([args.model], args.max_cost)
    config = validate_model_config(args.model)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    state = CostState(total=prior_cost, unknown_responses=prior_unknown)
    queue: asyncio.Queue[tuple[Path, dict[str, str]]] = asyncio.Queue()
    for job in jobs:
        queue.put_nowait(job)
    locks = {path: asyncio.Lock() for path in by_output}
    client = OpenRouterClient(api_key=api_key, timeout_seconds=args.timeout)
    done = 0

    async def worker() -> None:
        nonlocal done
        while not queue.empty() and not state.stop.is_set():
            async with state.lock:
                if args.max_cost is not None and state.total >= args.max_cost:
                    state.stop.set()
                    return
            try:
                path, row = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            r1 = None
            if args.phase == 2:
                source_id = f"{args.model}:{row['domain']}:{row['stem']}"
                r1 = round1_records.get(source_id)
                if not r1 or r1.get("error"):
                    raise ValueError(f"Missing successful Round 1 row: {source_id}")
            record = await issue(
                client, args.model, config, row, args.phase, args.repository_root.resolve(),
                r1, args.retries, args.backoff, args.max_tokens, args.answer_first,
            )
            await append_jsonl(path, record, locks[path])
            done += 1
            async with state.lock:
                if record["cost_usd"] is None:
                    state.unknown_responses += 1
                else:
                    state.total += float(record["cost_usd"])
                print(
                    f"{args.model} phase {args.phase}: {done}/{len(jobs)} | "
                    f"cost=${state.total:,.4f} | unknown-cost={state.unknown_responses}",
                    flush=True,
                )
                if args.max_cost is not None and state.total >= args.max_cost:
                    state.stop.set()
            queue.task_done()

    try:
        concurrency = args.concurrency or int(MODELS[args.model]["default_concurrency"])
        await asyncio.gather(*(worker() for _ in range(concurrency)))
    finally:
        await client.close()
    print(f"Run complete. Known cumulative cost=${state.total:,.4f}; responses without cost={state.unknown_responses}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=(1, 2), required=True)
    parser.add_argument("--model", required=True, choices=list(MODELS))
    parser.add_argument("--round1-manifest", type=Path, default=TEST_ROOT / "plan/crossexam_manifest.csv")
    parser.add_argument("--round2-manifest", type=Path, default=TEST_ROOT / "plan/crossexam_round2_manifest.csv")
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument(
        "--round1-results-dir", type=Path, default=TEST_ROOT / "results",
        help="Canonical completed Round-1 results; used by Phase 2 even when its output is sharded",
    )
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--arm", choices=("natural", "constructed", "control_reask"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--max-cost", type=float)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--backoff", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--max-tokens", type=int,
        help="Override the model's configured output-token limit for this run",
    )
    parser.add_argument(
        "--answer-first", action="store_true",
        help="Require the ANSWER line before any analysis (useful for repair retries)",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.concurrency is not None and args.concurrency < 1:
        parser.error("--concurrency must be positive")
    if args.max_cost is not None and args.max_cost <= 0:
        parser.error("--max-cost must be positive")
    if args.max_tokens is not None and args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    if args.phase == 1 and args.arm:
        parser.error("--arm is only valid in phase 2")
    return args


if __name__ == "__main__":
    asyncio.run(async_main(parse_args()))
