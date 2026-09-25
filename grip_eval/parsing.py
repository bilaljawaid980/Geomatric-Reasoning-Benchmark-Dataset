"""Exact response parsing and comparison for closed-loop results."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class ParsedAnswer:
    """A normalized model answer or an explicit parse failure."""

    parse_ok: bool
    value: Any = None
    text: str = ""
    error: str | None = None


def parse_jsonish(value: Any) -> Any:
    """Decode JSON/Python-literal strings while leaving plain strings unchanged."""

    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    for loader in (json.loads, ast.literal_eval):
        try:
            return loader(stripped)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
    return value


def normalize_text(value: Any) -> str:
    """Normalize case/spacing and remove surrounding punctuation or Markdown."""

    text = str(value).strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"^[\W_]+|[\W_]+$", "", text, flags=re.UNICODE)


def normalize_approved_equivalent(value: Any) -> str:
    """Apply only the explicitly approved meaning-preserving wording aliases."""

    normalized = normalize_text(value)
    return {
        "smaller than": "smaller",
        "none": "neither",
    }.get(normalized, normalized)


def _answer_body(response_raw: str) -> str:
    """Remove a surrounding code fence and an optional ANSWER: prefix."""

    text = response_raw.strip()
    text = re.sub(r"^```(?:\w+)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\bANSWER\s*:\s*", text, flags=re.IGNORECASE)
    if match:
        text = text[match.end() :]
    return text.strip()


def _format_spec(answer_format: str) -> dict[str, Any]:
    parsed = parse_jsonish(answer_format)
    if isinstance(parsed, dict):
        return parsed
    return {"type": str(answer_format or "exact")}


def _as_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip().strip("{}"))
    except (InvalidOperation, ValueError):
        return None


def _number_from_text(text: str) -> Decimal | None:
    """Parse one unambiguous number, allowing a unit or degree symbol around it."""

    numbers = re.findall(
        r"(?<![\w.])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?![\w.])",
        text,
    )
    if len(numbers) != 1:
        return None
    return _as_decimal(numbers[0])


def _is_numeric_kind(kind: str) -> bool:
    return any(
        token in kind
        for token in ("numeric", "integer", "degree", "percentage", "number")
    )


def parse_answer(
    response_raw: str,
    answer_format: str,
    ground_truth: str,
    tolerance: str = "",
    prompt: str = "",
) -> ParsedAnswer:
    """Parse one answer for exact comparison; tolerance is intentionally unused."""

    if not response_raw or not response_raw.strip():
        return ParsedAnswer(False, error="empty response")
    body = _answer_body(response_raw)
    if not body:
        return ParsedAnswer(False, error="empty answer body")

    format_spec = _format_spec(answer_format)
    kind = normalize_text(format_spec.get("type", ""))
    expected = parse_jsonish(ground_truth)

    # Acceptance-set formats are categorical, even when their JSON looks structured.
    if format_spec.get("acceptance_set"):
        candidate = normalize_approved_equivalent(body)
        if not candidate:
            return ParsedAnswer(False, text=body, error="empty acceptance-set answer")
        return ParsedAnswer(True, candidate, body)

    if isinstance(expected, (dict, list)):
        parsed = parse_jsonish(body)
        if isinstance(parsed, type(expected)):
            return ParsedAnswer(True, parsed, body)
        return ParsedAnswer(False, text=body, error="structured answer was not parseable")

    if _is_numeric_kind(kind) and _as_decimal(expected) is not None:
        number = _number_from_text(body)
        if number is None:
            return ParsedAnswer(False, text=body, error="expected exactly one number")
        return ParsedAnswer(True, number, body)

    candidate = normalize_text(body)
    if candidate:
        return ParsedAnswer(True, candidate, body)
    return ParsedAnswer(False, text=body, error="could not isolate an exact answer")


def _structured_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON-like values recursively without numeric tolerance."""

    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            _structured_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _structured_equal(a, e) for a, e in zip(actual, expected)
        )
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        return Decimal(str(actual)) == Decimal(str(expected))
    return normalize_approved_equivalent(actual) == normalize_approved_equivalent(expected)


def compare_answer(
    parsed: ParsedAnswer,
    ground_truth: str,
    answer_format: str,
    tolerance: str = "",
) -> bool:
    """Compare exactly; the tolerance column is deliberately ignored."""

    if not parsed.parse_ok:
        return False

    format_spec = _format_spec(answer_format)
    acceptance = format_spec.get("acceptance_set")
    if acceptance:
        accepted = {normalize_approved_equivalent(item) for item in acceptance}
        return normalize_approved_equivalent(parsed.value) in accepted

    expected = parse_jsonish(ground_truth)
    if isinstance(expected, (dict, list)):
        return _structured_equal(parsed.value, expected)

    kind = normalize_text(format_spec.get("type", ""))
    expected_number = _as_decimal(expected)
    if _is_numeric_kind(kind) and expected_number is not None:
        return isinstance(parsed.value, Decimal) and parsed.value == expected_number

    return normalize_approved_equivalent(parsed.value) == normalize_approved_equivalent(expected)
