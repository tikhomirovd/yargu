from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from yargumark.config import Settings, get_settings
from yargumark.db import EntityForMatch
from yargumark.nlp.types import LlmSpan, MatchResult
from yargumark.registry.lemmatize import to_lemma_key
from yargumark.registry.normalize import normalize_name


@dataclass(frozen=True)
class ResolvedCandidate:
    entity_id: int | None
    registry_source: str | None
    registry_id: str | None


def resolve_registry_candidate(
    candidate: str | None,
    entities: list[EntityForMatch],
) -> ResolvedCandidate:
    if candidate is None or candidate.strip() == "":
        return ResolvedCandidate(entity_id=None, registry_source=None, registry_id=None)
    trimmed = candidate.strip()
    if trimmed.isdigit():
        entity_id = int(trimmed)
        return ResolvedCandidate(entity_id=entity_id, registry_source=None, registry_id=None)
    if ":" in trimmed:
        source, registry_id = trimmed.split(":", 1)
        return ResolvedCandidate(
            entity_id=None,
            registry_source=source.strip(),
            registry_id=registry_id.strip(),
        )
    lowered = trimmed.lower()
    for entity in entities:
        if entity.canonical_name.lower() == lowered:
            return ResolvedCandidate(entity_id=entity.id, registry_source=None, registry_id=None)
    return ResolvedCandidate(entity_id=None, registry_source=None, registry_id=None)


def _candidate_matches_entity(
    resolved: ResolvedCandidate,
    entity: EntityForMatch,
) -> bool:
    if resolved.entity_id is not None:
        return resolved.entity_id == entity.id
    if resolved.registry_source is not None and resolved.registry_id is not None:
        return (
            entity.registry_source == resolved.registry_source
            and entity.registry_id == resolved.registry_id
        )
    return False


def _fuzzy_best_score(surface: str, entity: EntityForMatch) -> float:
    candidates = [entity.canonical_name, *entity.aliases]
    best = 0.0
    for label in candidates:
        score = float(fuzz.token_sort_ratio(surface, label))
        if score > best:
            best = score
    return best


def match_span_to_entity(
    span: LlmSpan,
    lemma_key: str,
    entities: list[EntityForMatch],
    settings: Settings | None = None,
) -> MatchResult | None:
    resolved_settings = settings or get_settings()
    fuzzy_min = int(resolved_settings.fuzzy_min_score)
    resolved_candidate = resolve_registry_candidate(span.registry_candidate, entities)

    lemma_hits = [entity for entity in entities if lemma_key in entity.lemma_keys]
    if len(lemma_hits) == 1:
        entity = lemma_hits[0]
        candidate_ok = (
            resolved_candidate.entity_id is None and resolved_candidate.registry_id is None
        ) or _candidate_matches_entity(resolved_candidate, entity)
        return MatchResult(
            entity_id=entity.id,
            confidence=1.0,
            match_method="lemma",
            llm_candidate_matched=candidate_ok,
        )

    surface_norm = normalize_name(span.surface).lower()
    for entity in entities:
        for alias in entity.aliases:
            if surface_norm == alias.lower():
                candidate_ok = (
                    resolved_candidate.entity_id is None and resolved_candidate.registry_id is None
                ) or _candidate_matches_entity(resolved_candidate, entity)
                return MatchResult(
                    entity_id=entity.id,
                    confidence=0.95,
                    match_method="alias",
                    llm_candidate_matched=candidate_ok,
                )

    best_entity: EntityForMatch | None = None
    best_score = 0.0
    for entity in entities:
        score = _fuzzy_best_score(span.surface, entity)
        if score > best_score:
            best_score = score
            best_entity = entity
    if best_entity is not None and best_score >= fuzzy_min:
        candidate_ok = (
            resolved_candidate.entity_id is None and resolved_candidate.registry_id is None
        ) or _candidate_matches_entity(resolved_candidate, best_entity)
        return MatchResult(
            entity_id=best_entity.id,
            confidence=best_score / 100.0,
            match_method="fuzzy",
            llm_candidate_matched=candidate_ok,
        )
    return None


def span_lemma_key(span: LlmSpan) -> str:
    base = normalize_name(span.normalized) if span.normalized else normalize_name(span.surface)
    return to_lemma_key(base)
