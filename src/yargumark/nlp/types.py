from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmSpan:
    start: int
    end: int
    surface: str
    span_type: str
    normalized: str
    registry_candidate: str | None
    confidence: float
    reasoning: str


@dataclass(frozen=True)
class MatchResult:
    entity_id: int
    confidence: float
    match_method: str
    llm_candidate_matched: bool
