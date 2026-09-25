"""Run fresh image-plus-question closed-loop queries through OpenRouter."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grip_eval.config import MODELS, PRICE_TABLE_USD_PER_MILLION, validate_model_config
from grip_eval.manifest import load_manifest
from grip_eval.openrouter import OpenRouterClient, closed_loop_user_content

FORMAT_INSTRUCTION = "Answer with only the following, and nothing else:\n\nANSWER: <your answer>"


@dataclass
class CostState:
    """Concurrency-safe accumulated cost and stop state."""

    total: float = 0.0
    unknown_responses: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    stop: asyncio.Event = field(default_factory=asyncio.Event)


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def completed_rows(path: Path) -> tuple[set[str], float, int]:
    """Read resumable row IDs and accumulated known cost from an existing JSONL."""

    completed: set[str] = set()
    cost = 0.0
    unknown = 0
    if not path.exists():
        return completed, cost, unknown
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path}:{line_number}: {error}") from error
            row_id = str(record.get("row_id", ""))
            if not row_id:
                raise ValueError(f"Missing row_id in {path}:{line_number}")
            # Failed requests remain pending so a corrected configuration can
            # retry them. A later successful record with the same row_id wins
            # during scoring.
            response_text = str(record.get("response_raw", "")).strip()
            if (
                record.get("error")
                or not response_text
                or response_text.casefold() in {"none", "null"}
            ):
                continue
            completed.add(row_id)
            if record.get("cost_usd") is None:
                unknown += 1
            else:
                cost += float(record["cost_usd"])
    return completed, cost, unknown


def should_retry(error: Exception) -> bool:
    """Return whether an OpenAI-compatible provider exception is transient."""

    if isinstance(error, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    return isinstance(error, APIStatusError) and error.status_code >= 500


async def append_jsonl(path: Path, record: dict[str, Any], lock: asyncio.Lock) -> None:
    """Append and flush one durable JSONL record."""

    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    async with lock:
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


async def issue_query(
    *,
    client: OpenRouterClient,
    model_key: str,
    model_config: dict[str, Any],
    row: dict[str, Any],
    repository_root: Path,
    retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    """Issue one fresh conversation with bounded transient-error retries."""

    prompt_sent = f"{row['prompt']}\n\n{FORMAT_INSTRUCTION}"
    image_path = repository_root / str(row["image_path"])
    base = {
        "row_id": row["row_id"],
        "model": model_key,
        "domain": row["domain"],
        "stem": row["stem"],
        "question_id": row["question_id"],
        "level": int(row["level"]),
        "image_path": row["image_path"],
        "prompt_sent": prompt_sent,
    }
    if not image_path.is_file():
        return {
            **base,
            "response_raw": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cost_usd": None,
            "latency_ms": 0,
            "attempt": 0,
            "error": f"image not found: {image_path}",
            "timestamp": utc_timestamp(),
        }

    messages = [
        {
            "role": "user",
            "content": closed_loop_user_content(image_path, prompt_sent),
        }
    ]
    for attempt in range(1, retries + 2):
        try:
            response = await client.chat(
                model_key=model_key,
                model_slug=model_config["slug"],
                messages=messages,
                max_tokens=int(model_config["max_tokens"]),
                reasoning=model_config.get("reasoning"),
                extra_body=model_config.get("extra_body"),
            )
            return {
                **base,
                "response_raw": response.text,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "reasoning_tokens": response.reasoning_tokens,
                "cost_usd": response.cost_usd,
                "latency_ms": response.latency_ms,
                "attempt": attempt,
                "error": None,
                "timestamp": utc_timestamp(),
            }
        except Exception as error:  # Provider exception classes vary by transport path.
            transient = should_retry(error)
            if transient and attempt <= retries:
                delay = backoff_seconds * (2 ** (attempt - 1))
                delay += random.uniform(0.0, min(1.0, delay * 0.1))
                await asyncio.sleep(delay)
                continue
            return {
                **base,
                "response_raw": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "cost_usd": None,
                "latency_ms": 0,
                "attempt": attempt,
                "error": f"{type(error).__name__}: {error}",
                "timestamp": utc_timestamp(),
            }
    raise AssertionError("retry loop exited unexpectedly")


async def run_model(
    *,
    client: OpenRouterClient,
    model_key: str,
    rows: list[dict[str, Any]],
    result_path: Path,
    repository_root: Path,
    concurrency: int,
    retries: int,
    backoff_seconds: float,
    max_cost: float | None,
    cost_state: CostState,
) -> int:
    """Run pending rows for one model with resumable append-only output."""

    model_config = validate_model_config(model_key)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    for row in rows:
        queue.put_nowait(row)
    file_lock = asyncio.Lock()
    completed_now = 0

    async def worker() -> None:
        nonlocal completed_now
        while not queue.empty() and not cost_state.stop.is_set():
            async with cost_state.lock:
                if max_cost is not None and cost_state.total >= max_cost:
                    cost_state.stop.set()
                    return
            try:
                row = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            record = await issue_query(
                client=client,
                model_key=model_key,
                model_config=model_config,
                row=row,
                repository_root=repository_root,
                retries=retries,
                backoff_seconds=backoff_seconds,
            )
            await append_jsonl(result_path, record, file_lock)
            completed_now += 1
            async with cost_state.lock:
                if record["cost_usd"] is None:
                    cost_state.unknown_responses += 1
                else:
                    cost_state.total += float(record["cost_usd"])
                print(
                    f"{model_key}: {completed_now}/{len(rows)} | "
                    f"cost=${cost_state.total:,.4f} | "
                    f"unknown-cost={cost_state.unknown_responses}",
                    flush=True,
                )
                if max_cost is not None and cost_state.total >= max_cost:
                    cost_state.stop.set()
            queue.task_done()

    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return completed_now


def require_cost_fallback(model_keys: list[str], max_cost: float | None) -> None:
    """Require editable fallback prices when a hard cost ceiling is requested."""

    if max_cost is None:
        return
    missing = [
        key
        for key in model_keys
        if PRICE_TABLE_USD_PER_MILLION[key]["input"] is None
        or PRICE_TABLE_USD_PER_MILLION[key]["output"] is None
    ]
    if missing:
        raise ValueError(
            "--max-cost requires fallback input/output prices for every selected model; "
            f"fill grip_eval/config.py for: {missing}"
        )


async def async_main(args: argparse.Namespace) -> None:
    """Load the manifest, resume selected models, and close the provider client."""

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set")
    # A paid run is intentionally restricted to one explicitly selected model.
    model_keys = [args.model]
    require_cost_fallback(model_keys, args.max_cost)
    for key in model_keys:
        validate_model_config(key)

    repository_root = args.repository_root.resolve()
    manifest = load_manifest(args.manifest)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    pending_by_model: dict[str, list[dict[str, Any]]] = {}
    accumulated_cost = 0.0
    accumulated_unknown = 0
    for model_key in model_keys:
        result_path = args.results_dir / f"closed_loop_{model_key}.jsonl"
        completed, prior_cost, prior_unknown = completed_rows(result_path)
        pending = manifest.loc[~manifest["row_id"].isin(completed)]
        if args.limit is not None:
            pending = pending.head(args.limit)
        pending_by_model[model_key] = pending.to_dict("records")
        accumulated_cost += prior_cost
        accumulated_unknown += prior_unknown
        print(
            f"{model_key}: {len(completed):,} existing, {len(pending):,} pending this run"
        )

    cost_state = CostState(total=accumulated_cost, unknown_responses=accumulated_unknown)
    client = OpenRouterClient(api_key=api_key, timeout_seconds=args.timeout)
    try:
        for model_key in model_keys:
            if cost_state.stop.is_set():
                break
            configured = int(MODELS[model_key]["default_concurrency"])
            concurrency = args.concurrency or configured
            await run_model(
                client=client,
                model_key=model_key,
                rows=pending_by_model[model_key],
                result_path=args.results_dir / f"closed_loop_{model_key}.jsonl",
                repository_root=repository_root,
                concurrency=concurrency,
                retries=args.retries,
                backoff_seconds=args.backoff,
                max_cost=args.max_cost,
                cost_state=cost_state,
            )
    finally:
        await client.close()
    print(
        f"Run complete. Known cumulative cost=${cost_state.total:,.4f}; "
        f"responses without cost={cost_state.unknown_responses}."
    )
    if cost_state.stop.is_set():
        print("Stopped at the configured cost ceiling; unissued rows remain resumable.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=TEST_ROOT / "plan" / "closed_loop_manifest.csv"
    )
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--model",
        required=True,
        choices=list(MODELS),
        help="Exactly one model key to run; there is deliberately no all-model default",
    )
    parser.add_argument("--limit", type=int, help="Maximum new rows per selected model")
    parser.add_argument("--concurrency", type=int, help="Override per-model concurrency")
    parser.add_argument("--max-cost", type=float, help="Cumulative USD ceiling")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--backoff", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be positive")
    if args.concurrency is not None and args.concurrency < 1:
        raise ValueError("--concurrency must be positive")
    if args.max_cost is not None and args.max_cost <= 0:
        raise ValueError("--max-cost must be positive")
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
