"""Run a guarded 10-question Gemini closed-loop smoke test via OpenRouter."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grip_eval.config import (
    ESTIMATED_TOKENS_PER_QUERY,
    MODELS,
    PRICE_TABLE_USD_PER_MILLION,
    fallback_cost_usd,
    validate_model_config,
)
from grip_eval.openrouter import OpenRouterClient, closed_loop_user_content
from grip_eval.parsing import compare_answer, parse_answer

MODEL_KEY = "gemini_3_8_flash"
SAMPLE_SIZE = 10
PER_LEVEL = 2
FORMAT_INSTRUCTION = "Answer with only the following, and nothing else:\n\nANSWER: <your answer>"
REQUIRED_COLUMNS = {
    "row_id",
    "domain",
    "stem",
    "image_path",
    "question_id",
    "level",
    "prompt",
    "ground_truth",
    "answer_format",
    "tolerance",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_rows(path: Path) -> list[dict[str, str]]:
    """Read the local evaluation manifest without transmitting any private fields."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} contains no rows")
    return rows


def choose_rows(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    """Choose two rows per level, preferring ten distinct domains."""

    selected: list[dict[str, str]] = []
    used_domains: set[str] = set()
    used_stems: set[tuple[str, str]] = set()
    for level in range(1, 6):
        candidates = [row for row in rows if int(row["level"]) == level]
        random.Random(f"{seed}:{level}").shuffle(candidates)
        chosen: list[dict[str, str]] = []
        for prefer_new_domain in (True, False):
            for row in candidates:
                item = (row["domain"], row["stem"])
                if item in used_stems or row in chosen:
                    continue
                if prefer_new_domain and row["domain"] in used_domains:
                    continue
                chosen.append(row)
                used_domains.add(row["domain"])
                used_stems.add(item)
                if len(chosen) == PER_LEVEL:
                    break
            if len(chosen) == PER_LEVEL:
                break
        if len(chosen) != PER_LEVEL:
            raise ValueError(f"Could not select {PER_LEVEL} distinct items for level {level}")
        selected.extend(chosen)
    if len(selected) != SAMPLE_SIZE:
        raise AssertionError(f"Expected {SAMPLE_SIZE} selected rows, got {len(selected)}")
    return selected


def estimated_cost(query_count: int) -> float:
    prices = PRICE_TABLE_USD_PER_MILLION[MODEL_KEY]
    estimate = fallback_cost_usd(
        MODEL_KEY,
        ESTIMATED_TOKENS_PER_QUERY["input"] * query_count,
        ESTIMATED_TOKENS_PER_QUERY["output"] * query_count,
        int(
            MODELS[MODEL_KEY].get(
                "estimated_reasoning_tokens",
                ESTIMATED_TOKENS_PER_QUERY["reasoning"],
            )
        )
        * query_count,
    )
    if estimate is None or prices["input"] is None or prices["output"] is None:
        raise ValueError(f"Pricing is not configured for {MODEL_KEY}")
    return estimate


def direct_cost_present(payload: dict[str, Any]) -> bool:
    usage = payload.get("usage") or {}
    return usage.get("cost") is not None or payload.get("cost") is not None


def default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return TEST_ROOT / "results" / f"gemini_smoke_test_{stamp}.jsonl"


async def execute(
    rows: list[dict[str, str]],
    *,
    repository_root: Path,
    output_path: Path,
    max_cost: float,
    timeout: float,
) -> None:
    """Issue exactly the selected requests sequentially and report local scores/cost."""

    load_dotenv()
    import os

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set in the environment or .env")

    model = validate_model_config(MODEL_KEY)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output_path}")

    total_cost = 0.0
    total_input = 0
    total_output = 0
    total_reasoning = 0
    correct = 0
    completed = 0
    errors = 0
    client = OpenRouterClient(api_key=api_key, timeout_seconds=timeout)
    try:
        with output_path.open("x", encoding="utf-8", newline="") as handle:
            for index, row in enumerate(rows, start=1):
                if total_cost >= max_cost:
                    print(f"Stopped before row {index}: ${max_cost:.4f} soft cost ceiling reached.")
                    break

                image_path = repository_root / row["image_path"]
                if not image_path.is_file():
                    raise FileNotFoundError(f"Missing sampled image: {image_path}")
                prompt_sent = f"{row['prompt']}\n\n{FORMAT_INSTRUCTION}"
                try:
                    response = await client.chat(
                        model_key=MODEL_KEY,
                        model_slug=model["slug"],
                        messages=[
                            {
                                "role": "user",
                                "content": closed_loop_user_content(image_path, prompt_sent),
                            }
                        ],
                        max_tokens=int(model["max_tokens"]),
                        reasoning=model.get("reasoning"),
                    )
                    parsed = parse_answer(
                        response.text,
                        row["answer_format"],
                        row["ground_truth"],
                        row["tolerance"],
                        row["prompt"],
                    )
                    is_correct = compare_answer(
                        parsed,
                        row["ground_truth"],
                        row["answer_format"],
                        row["tolerance"],
                    )
                    cost = response.cost_usd
                    source = (
                        "openrouter_reported"
                        if direct_cost_present(response.provider_payload)
                        else "configured_fallback"
                    )
                    if cost is not None:
                        total_cost += cost
                    total_input += response.input_tokens
                    total_output += response.output_tokens
                    total_reasoning += response.reasoning_tokens
                    completed += 1
                    correct += int(is_correct)
                    record = {
                        "index": index,
                        "timestamp": utc_now(),
                        "row_id": row["row_id"],
                        "domain": row["domain"],
                        "level": int(row["level"]),
                        "question_id": row["question_id"],
                        "response_raw": response.text,
                        "parsed_answer": str(parsed.value) if parsed.parse_ok else None,
                        "parse_ok": parsed.parse_ok,
                        "parse_error": parsed.error,
                        "ground_truth": row["ground_truth"],
                        "correct": is_correct,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "reasoning_tokens": response.reasoning_tokens,
                        "cost_usd": cost,
                        "cost_source": source,
                        "latency_ms": response.latency_ms,
                    }
                    print(
                        f"{index:02d}/{SAMPLE_SIZE} {row['domain']} L{row['level']} "
                        f"correct={is_correct} cost=${(cost or 0.0):.6f} "
                        f"cumulative=${total_cost:.6f}"
                    )
                except Exception as error:
                    errors += 1
                    record = {
                        "index": index,
                        "timestamp": utc_now(),
                        "row_id": row["row_id"],
                        "domain": row["domain"],
                        "level": int(row["level"]),
                        "question_id": row["question_id"],
                        "error": f"{type(error).__name__}: {error}",
                    }
                    print(f"{index:02d}/{SAMPLE_SIZE} ERROR {record['error']}")
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
    finally:
        await client.close()

    print("\nGemini smoke-test summary")
    print(f"Successful responses: {completed}/{SAMPLE_SIZE}")
    print(f"Request errors: {errors}")
    print(f"Exact-match accuracy: {correct}/{completed}" if completed else "Exact-match accuracy: n/a")
    print(f"Input tokens: {total_input:,}")
    print(f"Output tokens: {total_output:,}")
    print(f"Reasoning tokens: {total_reasoning:,}")
    print(f"Reported/fallback cost: ${total_cost:.6f}")
    print(f"Results: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=TEST_ROOT / "plan" / "closed_loop_manifest.csv")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--seed", type=int, default=20260915)
    parser.add_argument("--max-cost", type=float, default=0.10, help="Soft USD ceiling")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually issue the 10 paid OpenRouter requests; otherwise dry-run only",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_cost <= 0:
        raise ValueError("--max-cost must be positive")
    model = validate_model_config(MODEL_KEY)
    rows = choose_rows(load_rows(args.manifest), args.seed)
    estimate = estimated_cost(len(rows))

    print(f"Model: {model['display_name']} ({model['slug']})")
    print(f"Samples: {len(rows)} ({PER_LEVEL} from each of L1-L5)")
    print(f"Estimated cost: ${estimate:.6f}")
    print(f"Soft cost ceiling: ${args.max_cost:.4f}")
    print("Selected rows:")
    for index, row in enumerate(rows, start=1):
        print(f"  {index:02d}. {row['domain']} L{row['level']} {row['question_id']}")

    if not args.execute:
        print("\nDRY RUN ONLY: no API requests were sent and no cost was incurred.")
        print("Run again with --execute to issue exactly these 10 requests.")
        return

    output_path = args.output or default_output_path()
    asyncio.run(
        execute(
            rows,
            repository_root=args.repository_root.resolve(),
            output_path=output_path,
            max_cost=args.max_cost,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    main()
