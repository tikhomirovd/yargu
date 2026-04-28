from __future__ import annotations

from yargumark.nlp.types import LlmSpan, MatchResult


def finalize_confidence(span: LlmSpan, match: MatchResult) -> float:
    has_candidate = bool(span.registry_candidate and span.registry_candidate.strip())
    if not has_candidate:
        if match.match_method == "lemma":
            return 1.0
        return 0.85
    if match.llm_candidate_matched:
        return max(match.confidence, span.confidence)
    return min(span.confidence, 0.5)


def build_reasoning(span: LlmSpan, match: MatchResult, context_note: str | None) -> str:
    base = span.reasoning.strip()
    parts = [
        base,
        f"match_method={match.match_method}",
        f"llm_candidate_ok={match.llm_candidate_matched}",
    ]
    if context_note:
        parts.append(context_note)
    return " ".join(part for part in parts if part)
