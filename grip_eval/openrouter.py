"""Generic asynchronous OpenRouter chat client used by all evaluation phases."""

from __future__ import annotations

import base64
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import OPENROUTER_BASE_URL, fallback_cost_usd


@dataclass(frozen=True)
class ProviderResponse:
    """Provider response text, accounting fields, and measured latency."""

    text: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: float | None
    latency_ms: int
    provider_payload: dict[str, Any]


def image_as_data_uri(path: str | Path) -> str:
    """Read an image unchanged and return an original-byte base64 data URI."""

    image_path = Path(path)
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def closed_loop_user_content(image_path: str | Path, prompt: str) -> list[dict[str, Any]]:
    """Build one image-plus-question user turn in OpenAI-compatible format."""

    return [
        {"type": "image_url", "image_url": {"url": image_as_data_uri(image_path)}},
        {"type": "text", "text": prompt},
    ]


def _response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    content = (choices[0].get("message") or {}).get("content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    return str(content)


def _usage_fields(payload: dict[str, Any]) -> tuple[int, int, int, float | None]:
    usage = payload.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    details = usage.get("completion_tokens_details") or {}
    reasoning_tokens = int(
        details.get("reasoning_tokens")
        or usage.get("reasoning_tokens")
        or payload.get("reasoning_tokens")
        or 0
    )
    direct_cost = usage.get("cost", payload.get("cost"))
    return input_tokens, output_tokens, reasoning_tokens, (
        float(direct_cost) if direct_cost is not None else None
    )


class OpenRouterClient:
    """Thin generic chat adapter that can support single or multi-turn requests."""

    def __init__(self, api_key: str, timeout_seconds: float = 120.0) -> None:
        """Create an asynchronous OpenRouter client without issuing a request."""

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=timeout_seconds,
        )

    async def chat(
        self,
        *,
        model_key: str,
        model_slug: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        reasoning: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Send arbitrary chat history and return normalized response metadata."""

        body = dict(extra_body or {})
        if reasoning is not None:
            body["reasoning"] = reasoning
        started = time.perf_counter()
        request: dict[str, Any] = {
            "model": model_slug,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if body:
            request["extra_body"] = body
        response = await self._client.chat.completions.create(**request)
        latency_ms = round((time.perf_counter() - started) * 1_000)
        payload = response.model_dump(mode="json")
        input_tokens, output_tokens, reasoning_tokens, direct_cost = _usage_fields(payload)
        cost = direct_cost
        if cost is None:
            cost = fallback_cost_usd(
                model_key, input_tokens, output_tokens, reasoning_tokens
            )
        return ProviderResponse(
            text=_response_text(payload),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            provider_payload=payload,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.close()
