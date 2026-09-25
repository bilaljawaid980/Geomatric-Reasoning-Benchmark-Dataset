"""Editable model, provider, and pricing configuration for GRIP evaluation."""

from __future__ import annotations

from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model IDs and standard pricing verified against OpenRouter on 2026-09-15.
# A model can be changed later by editing its single ``slug`` line below.
MODELS: dict[str, dict[str, Any]] = {
    "perplexity_sonar_pro": {
        "display_name": "Perplexity Sonar Pro",
        "slug": "perplexity/sonar-pro",
        "extra_body": {
            "provider": {
                "order": ["perplexity"],
                "allow_fallbacks": False,
            }
        },
        "estimated_reasoning_tokens": 0,
        "default_concurrency": 1,
        "max_tokens": 512,
    },
    "deepseek_v4_1_flash": {
        "display_name": "DeepSeek V4.1 Flash",
        "slug": "deepseek/deepseek-v4.1-flash",
        "extra_body": {"provider": {"sort": "latency"}},
        "reasoning": {"effort": "none"},
        "estimated_reasoning_tokens": 0,
        "default_concurrency": 1,
        "max_tokens": 512,
    },
    "gpt_5_6_sol": {
        "display_name": "GPT-5.6 Sol",
        "slug": "openai/gpt-5.6-sol",
        "extra_body": {
            "provider": {
                "order": ["openai"],
                "allow_fallbacks": False,
            }
        },
        "reasoning": {"effort": "none"},
        "estimated_reasoning_tokens": 0,
        "default_concurrency": 1,
        "max_tokens": 256,
    },
    "gpt_5_6_luna": {
        "display_name": "GPT-5.6 Luna",
        "slug": "openai/gpt-5.6-luna",
        "extra_body": {"provider": {"sort": "latency"}},
        "reasoning": {"effort": "none"},
        "estimated_reasoning_tokens": 0,
        "default_concurrency": 2,
        "max_tokens": 256,
    },
    "claude_opus_5": {
        "display_name": "Claude Opus 5",
        "slug": "anthropic/claude-opus-5",
        "extra_body": {"provider": {"sort": "latency"}},
        "reasoning": {"effort": "low"},
        "estimated_reasoning_tokens": 256,
        "default_concurrency": 2,
        "max_tokens": 2048,
    },
    "claude_sonnet_5": {
        "display_name": "Claude Sonnet 5",
        "slug": "anthropic/claude-sonnet-5",
        "extra_body": {"provider": {"sort": "latency"}},
        "reasoning": {"effort": "low"},
        "estimated_reasoning_tokens": 256,
        "default_concurrency": 2,
        "max_tokens": 2048,
    },
    "gemini_3_8_flash": {
        "display_name": "Gemini 3.8 Flash",
        "slug": "google/gemini-3.8-flash",
        "reasoning": {"effort": "low"},
        "estimated_reasoning_tokens": 256,
        "default_concurrency": 2,
        "max_tokens": 1024,
    },
    "grok_4_6": {
        "display_name": "Grok 4.6",
        "slug": "x-ai/grok-4.6",
        "extra_body": {
            "provider": {
                "order": ["xai"],
                "allow_fallbacks": False,
            }
        },
        "reasoning": {"effort": "low"},
        "estimated_reasoning_tokens": 256,
        "default_concurrency": 2,
        "max_tokens": 1024,
    },
    # Keep the historical CLI key ``inking`` for compatibility; the model is Inkling.
    "inking": {
        "display_name": "Inkling",
        "slug": "thinkingmachines/inkling",
        "extra_body": {"provider": {"sort": "latency"}},
        "reasoning": {"effort": "none"},
        "estimated_reasoning_tokens": 0,
        "default_concurrency": 2,
        "max_tokens": 256,
    },
    "muse_glimmer_30b": {
        "display_name": "Meta Muse Glimmer 30B",
        "slug": "meta/muse-glimmer-30b:nitro",
        "extra_body": {
            "provider": {
                "order": ["fireworks"],
                "allow_fallbacks": False,
            }
        },
        "reasoning": {"effort": "low"},
        "estimated_reasoning_tokens": 256,
        "default_concurrency": 1,
        "max_tokens": 512,
    },
}

# USD per one million tokens at the verification date above.
# Direct cost returned by OpenRouter always takes precedence over this fallback.
PRICE_TABLE_USD_PER_MILLION: dict[str, dict[str, float | None]] = {
    "perplexity_sonar_pro": {
        "input": 3.00,
        "output": 15.00,
        "reasoning": 15.00,
        "request": 0.005,
    },
    "deepseek_v4_1_flash": {"input": 0.15, "output": 0.60, "reasoning": 0.60},
    "gpt_5_6_sol": {"input": 2.00, "output": 10.00, "reasoning": 10.00},
    "gpt_5_6_luna": {"input": 0.20, "output": 1.20, "reasoning": 1.20},
    "claude_opus_5": {"input": 5.00, "output": 25.00, "reasoning": 25.00},
    "claude_sonnet_5": {"input": 2.00, "output": 10.00, "reasoning": 10.00},
    "gemini_3_8_flash": {"input": 0.75, "output": 3.75, "reasoning": 3.75},
    "grok_4_6": {"input": 2.00, "output": 6.00, "reasoning": 6.00},
    "inking": {"input": 0.95, "output": 4.05, "reasoning": 4.05},
    "muse_glimmer_30b": {"input": 0.35, "output": 1.50, "reasoning": 1.50},
}

# Used only for the pre-run estimate printed by sample_closed_loop.py.
ESTIMATED_TOKENS_PER_QUERY = {
    "input": 1_100,
    "output": 32,
    "reasoning": 0,
}


def validate_model_config(model_key: str) -> dict[str, Any]:
    """Return one configured model entry or raise for an unknown/placeholder slug."""

    if model_key not in MODELS:
        available = ", ".join(MODELS)
        raise KeyError(f"Unknown model key {model_key!r}. Available: {available}")
    config = MODELS[model_key]
    if not config["slug"] or str(config["slug"]).startswith("REPLACE_WITH_"):
        raise ValueError(
            f"Set MODELS[{model_key!r}]['slug'] in grip_eval/config.py from the "
            "OpenRouter models page before running queries."
        )
    return config


def fallback_cost_usd(
    model_key: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
) -> float | None:
    """Estimate response cost from the editable table when provider cost is absent."""

    prices = PRICE_TABLE_USD_PER_MILLION[model_key]
    if prices["input"] is None or prices["output"] is None:
        return None
    reasoning_price = prices["reasoning"]
    if reasoning_price is None:
        reasoning_price = prices["output"]
    token_cost = (
        input_tokens * prices["input"]
        + output_tokens * prices["output"]
        + reasoning_tokens * reasoning_price
    ) / 1_000_000
    return token_cost + float(prices.get("request") or 0.0)
