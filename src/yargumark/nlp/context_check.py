from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from yargumark.config import Settings, get_settings
from yargumark.db import EntityForMatch


@dataclass(frozen=True)
class ContextCheckResult:
    is_match: bool
    confidence: float
    reasoning: str


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_context_payload(text: str) -> ContextCheckResult:
    cleaned = text.strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match is not None:
        cleaned = match.group(1).strip()
    payload = json.loads(cleaned)
    return ContextCheckResult(
        is_match=bool(payload.get("is_match", False)),
        confidence=float(payload.get("confidence", 0.0)),
        reasoning=str(payload.get("reasoning", "")),
    )


def _snippet(body: str, start: int, end: int, radius: int) -> str:
    left = max(0, start - radius)
    right = min(len(body), end + radius)
    return body[left:right]


def run_context_check(
    body: str,
    start: int,
    end: int,
    entity: EntityForMatch,
    settings: Settings | None = None,
) -> ContextCheckResult:
    resolved = settings or get_settings()
    if not resolved.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    snippet = _snippet(body, start, end, radius=300)
    system_prompt = (
        "You verify whether a person mention refers to a specific registry entity. "
        "Answer JSON only: "
        '{"is_match":true|false,"confidence":0.0-1.0,"reasoning":"one sentence"}.'
    )
    user_prompt = (
        f"Snippet:\n{snippet}\n\n"
        f"Candidate entity: {entity.canonical_name} "
        f"({entity.registry_source}:{entity.registry_id}).\n"
        "Is this snippet about that specific person?"
    )
    client = anthropic.Anthropic(api_key=resolved.anthropic_api_key)
    response = client.messages.create(
        model=resolved.anthropic_model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text_parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            text_parts.append(text)
    return _parse_context_payload("".join(text_parts))
