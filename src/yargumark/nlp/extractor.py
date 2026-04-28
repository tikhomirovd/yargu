from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

import anthropic

from yargumark.config import Settings, get_settings
from yargumark.db import DigestEntityRow
from yargumark.nlp.prompts import build_system_prompt, build_user_prompt
from yargumark.nlp.types import LlmSpan


@dataclass(frozen=True)
class ExtractionUsage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


@dataclass(frozen=True)
class ExtractionResult:
    spans: list[LlmSpan]
    raw_response_text: str
    usage: ExtractionUsage


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_spans_payload(text: str) -> list[LlmSpan]:
    cleaned = text.strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match is not None:
        cleaned = match.group(1).strip()
    payload = json.loads(cleaned)
    spans_value = payload.get("spans", [])
    if not isinstance(spans_value, list):
        raise ValueError("Invalid spans payload.")
    spans: list[LlmSpan] = []
    for item in cast(Sequence[object], spans_value):
        if not isinstance(item, dict):
            continue
        row = cast(dict[str, Any], item)
        candidate = row.get("registry_candidate")
        spans.append(
            LlmSpan(
                start=int(row["start"]),
                end=int(row["end"]),
                surface=str(row["surface"]),
                span_type=str(row["type"]),
                normalized=str(row.get("normalized", row["surface"])),
                registry_candidate=str(candidate) if candidate is not None else None,
                confidence=float(row.get("confidence", 0.0)),
                reasoning=str(row.get("reasoning", "")),
            )
        )
    return spans


def _extract_usage(response: object) -> ExtractionUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return ExtractionUsage(input_tokens=0, output_tokens=0, cached_input_tokens=0)
    input_tokens = int(getattr(usage, "input_tokens", 0))
    output_tokens = int(getattr(usage, "output_tokens", 0))
    cached = int(
        getattr(usage, "cache_read_input_tokens", 0)
        or getattr(usage, "cache_creation_input_tokens", 0)
    )
    return ExtractionUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
    )


def _extract_text_blocks(response: object) -> str:
    content = getattr(response, "content", [])
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def extract_spans_with_haiku(
    document_body: str,
    digest: list[DigestEntityRow],
    settings: Settings | None = None,
) -> ExtractionResult:
    resolved = settings or get_settings()
    if not resolved.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    system_prompt = build_system_prompt(digest)
    user_prompt = build_user_prompt(document_body)
    client = anthropic.Anthropic(api_key=resolved.anthropic_api_key)
    response = client.messages.create(
        model=resolved.anthropic_model,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = _extract_text_blocks(response)
    spans = _parse_spans_payload(text)
    usage = _extract_usage(response)
    return ExtractionResult(spans=spans, raw_response_text=text, usage=usage)


def _align_span_to_body(span: LlmSpan, body: str, window: int) -> LlmSpan | None:
    if not span.surface:
        return None
    length = len(body)
    if (
        0 <= span.start < span.end <= length
        and body[span.start : span.end] == span.surface
    ):
        return span
    anchor_lo = min(max(span.start, 0), length)
    anchor_hi = min(max(span.end, span.start, 0), length)
    lo = max(0, anchor_lo - window)
    hi = min(length, max(anchor_hi, anchor_lo + len(span.surface)) + window)
    segment = body[lo:hi]
    idx = segment.find(span.surface)
    if idx >= 0:
        start = lo + idx
        return replace(span, start=start, end=start + len(span.surface))
    parts = span.surface.split()
    if len(parts) >= 2:
        pattern = r"\s+".join(re.escape(part) for part in parts)
        match = re.search(pattern, segment)
        if match is not None:
            start = lo + match.start()
            end = lo + match.end()
            return replace(span, start=start, end=end)
    # Fallback: full-document scan when windowed search fails
    idx = body.find(span.surface)
    if idx >= 0:
        return replace(span, start=idx, end=idx + len(span.surface))
    if len(parts) >= 2:
        pattern = r"\s+".join(re.escape(part) for part in parts)
        match = re.search(pattern, body)
        if match is not None:
            return replace(span, start=match.start(), end=match.end())
    return None


def validate_span_offsets(
    spans: list[LlmSpan],
    body: str,
    align_window: int = 50,
) -> list[LlmSpan]:
    valid: list[LlmSpan] = []
    for span in spans:
        aligned = _align_span_to_body(span, body, align_window)
        if aligned is None:
            continue
        if aligned.start < 0 or aligned.end > len(body) or aligned.start >= aligned.end:
            continue
        if body[aligned.start : aligned.end] != aligned.surface:
            continue
        valid.append(aligned)
    return valid
