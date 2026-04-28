from __future__ import annotations

import json
import re
from dataclasses import dataclass
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
    raw_spans = payload.get("spans", [])
    if not isinstance(raw_spans, list):
        raise ValueError("Invalid spans payload.")
    spans: list[LlmSpan] = []
    for item in cast(list[Any], raw_spans):
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


def validate_span_offsets(spans: list[LlmSpan], body: str) -> list[LlmSpan]:
    length = len(body)
    valid: list[LlmSpan] = []
    for span in spans:
        if span.start < 0 or span.end > length or span.start >= span.end:
            continue
        if body[span.start : span.end] != span.surface:
            continue
        valid.append(span)
    return valid
