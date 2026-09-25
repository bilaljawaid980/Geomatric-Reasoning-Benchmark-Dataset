"""Run resumable grain-robustness queries after mandatory readability review."""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import random
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = Path(__file__).resolve().parents[1]
TEST1_SCRIPTS = REPO_ROOT / "tests" / "test_1_closed_loop" / "scripts"
for import_root in (REPO_ROOT, TEST1_SCRIPTS):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from grip_eval.config import MODELS, validate_model_config
from grip_eval.openrouter import OpenRouterClient, closed_loop_user_content
from run_closed_loop import (
    CostState,
    FORMAT_INSTRUCTION,
    append_jsonl,
    completed_rows,
    require_cost_fallback,
    should_retry,
    utc_timestamp,
)

MANIFEST_COLUMNS = [
    "row_id",
    "domain",
    "stem",
    "sigma",
    "image_path",
    "question_id",
    "level",
    "prompt",
    "ground_truth",
    "answer_format",
]


def parse_sigmas(value: str | None, available: set[int]) -> list[int]:
    """Select positive manifest sigmas in ascending order."""

    selected = sorted(available) if not value else sorted(
        {int(part.strip()) for part in value.split(",") if part.strip()}
    )
    if not selected or any(sigma <= 0 for sigma in selected):
        raise ValueError("run_grain.py only issues positive-sigma queries")
    unknown = sorted(set(selected) - available)
    if unknown:
        raise ValueError(f"Requested sigmas absent from manifest: {unknown}")
    return selected


def load_grain_manifest(path: Path) -> pd.DataFrame:
    """Load and validate the paid grain-query manifest."""

    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != MANIFEST_COLUMNS:
        raise ValueError(f"Unexpected grain manifest schema: {list(frame.columns)}")
    if frame["row_id"].duplicated().any():
        raise ValueError("Duplicate grain manifest row_id values")
    frame["sigma"] = pd.to_numeric(frame["sigma"], errors="raise").astype(int)
    frame["level"] = pd.to_numeric(frame["level"], errors="raise").astype(int)
    if (frame["sigma"] <= 0).any() or not frame["level"].between(1, 5).all():
        raise ValueError("Invalid sigma or level in grain manifest")
    return frame


def readability_decisions(path: Path) -> dict[tuple[str, int], bool]:
    """Load explicit manual yes/no decisions; blanks are a hard preflight failure."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"domain", "sigma", "readable"}.issubset(
            reader.fieldnames
        ):
            raise ValueError(f"Unexpected readability CSV schema in {path}")
        decisions: dict[tuple[str, int], bool] = {}
        for line_number, row in enumerate(reader, start=2):
            key = (row["domain"], int(row["sigma"]))
            if key in decisions:
                raise ValueError(f"Duplicate readability decision for {key}")
            value = row["readable"].strip().casefold()
            if value in {"yes", "y", "true", "readable", "1"}:
                decisions[key] = True
            elif value in {"no", "n", "false", "unreadable", "0"}:
                decisions[key] = False
            else:
                raise ValueError(
                    f"Set readable to yes or no in {path}:{line_number}; found {value!r}"
                )
    return decisions


def apply_readability_gate(
    manifest: pd.DataFrame, decisions: dict[tuple[str, int], bool]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return readable and explicitly unreadable rows after complete review."""

    required = sorted({(str(row.domain), int(row.sigma)) for row in manifest.itertuples()})
    missing = [key for key in required if key not in decisions]
    if missing:
        raise ValueError(f"Missing manual readability decisions: {missing[:10]}")
    allowed = manifest.apply(
        lambda row: decisions[(str(row["domain"]), int(row["sigma"]))], axis=1
    )
    return manifest.loc[allowed].copy(), manifest.loc[~allowed].copy()


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
    """Issue one grain query with the closed-loop prompt and retry policy."""

    prompt_sent = f"{row['prompt']}\n\n{FORMAT_INSTRUCTION}"
    image_path = repository_root / str(row["image_path"])
    base = {
        "row_id": row["row_id"],
        "model": model_key,
        "domain": row["domain"],
        "stem": row["stem"],
        "sigma": int(row["sigma"]),
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
        except Exception as error:
            if should_retry(error) and attempt <= retries:
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


async def run_rows(
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
    """Run one sigma's pending rows with durable append-only results."""

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
                    f"{model_key} sigma={record['sigma']}: {completed_now}/{len(rows)} | "
                    f"cost=${cost_state.total:,.4f} | "
                    f"unknown-cost={cost_state.unknown_responses}",
                    flush=True,
                )
                if max_cost is not None and cost_state.total >= max_cost:
                    cost_state.stop.set()
            queue.task_done()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return completed_now


async def async_main(args: argparse.Namespace) -> None:
    """Validate manual review, then run one explicitly selected model."""

    manifest = load_grain_manifest(args.manifest)
    sigmas = parse_sigmas(args.sigmas, set(manifest["sigma"]))
    manifest = manifest.loc[manifest["sigma"].isin(sigmas)].copy()
    decisions = readability_decisions(args.readability)
    readable, skipped = apply_readability_gate(manifest, decisions)
    print(f"Readable rows eligible: {len(readable):,}")
    print(f"Rows skipped as manually unreadable: {len(skipped):,}")
    if readable.empty:
        print("No readable rows are eligible; no API client was created.")
        return

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set")
    require_cost_fallback([args.model], args.max_cost)
    validate_model_config(args.model)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    pending_by_sigma: dict[int, list[dict[str, Any]]] = {}
    accumulated_cost = 0.0
    accumulated_unknown = 0
    for sigma in sigmas:
        result_path = args.results_dir / f"grain_{args.model}_sigma{sigma}.jsonl"
        completed, prior_cost, prior_unknown = completed_rows(result_path)
        pending = readable.loc[
            (readable["sigma"] == sigma) & ~readable["row_id"].isin(completed)
        ]
        if args.limit is not None:
            pending = pending.head(args.limit)
        pending_by_sigma[sigma] = pending.to_dict("records")
        accumulated_cost += prior_cost
        accumulated_unknown += prior_unknown
        print(f"{args.model} sigma={sigma}: {len(completed):,} existing, {len(pending):,} pending")

    cost_state = CostState(total=accumulated_cost, unknown_responses=accumulated_unknown)
    client = OpenRouterClient(api_key=api_key, timeout_seconds=args.timeout)
    try:
        for sigma in sigmas:
            if cost_state.stop.is_set():
                break
            rows = pending_by_sigma[sigma]
            if not rows:
                continue
            concurrency = args.concurrency or int(MODELS[args.model]["default_concurrency"])
            await run_rows(
                client=client,
                model_key=args.model,
                rows=rows,
                result_path=args.results_dir / f"grain_{args.model}_sigma{sigma}.jsonl",
                repository_root=args.repository_root.resolve(),
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=TEST_ROOT / "plan" / "grain_manifest.csv")
    parser.add_argument(
        "--readability", type=Path, default=TEST_ROOT / "plan" / "grain_readability.csv"
    )
    parser.add_argument("--results-dir", type=Path, default=TEST_ROOT / "results")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--model", required=True, choices=list(MODELS))
    parser.add_argument("--sigmas", help="Comma-separated positive sigmas; default is all")
    parser.add_argument("--limit", type=int, help="Maximum new rows per selected sigma")
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--max-cost", type=float, help="Cumulative USD ceiling")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--backoff", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> None:
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
