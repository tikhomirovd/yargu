from __future__ import annotations

import json
from typing import Any

from yargumark.config import get_settings
from yargumark.db import (
    EntityForMatch,
    ExtractedSpanRecord,
    LlmCacheRow,
    MentionRecord,
    clear_nlp_for_document,
    fetch_digest_entities,
    fetch_document,
    fetch_entities_for_matching,
    get_connection,
    get_llm_cache,
    insert_extracted_span,
    insert_mention,
    upsert_llm_cache,
)
from yargumark.nlp.confidence_rules import build_reasoning, finalize_confidence
from yargumark.nlp.context_check import run_context_check
from yargumark.nlp.extractor import (
    ExtractionResult,
    extract_spans_with_haiku,
    validate_span_offsets,
)
from yargumark.nlp.llm_cache import text_sha256
from yargumark.nlp.matcher import match_span_to_entity, span_lemma_key
from yargumark.nlp.types import LlmSpan


def _entity_by_id(entities: list[EntityForMatch], entity_id: int) -> EntityForMatch | None:
    for entity in entities:
        if entity.id == entity_id:
            return entity
    return None


def _span_from_dict(payload: dict[str, Any]) -> LlmSpan:
    candidate = payload.get("registry_candidate")
    return LlmSpan(
        start=int(payload["start"]),
        end=int(payload["end"]),
        surface=str(payload["surface"]),
        span_type=str(payload["type"]),
        normalized=str(payload.get("normalized", payload["surface"])),
        registry_candidate=str(candidate) if candidate is not None else None,
        confidence=float(payload.get("confidence", 0.0)),
        reasoning=str(payload.get("reasoning", "")),
    )


def _span_to_dict(span: LlmSpan) -> dict[str, Any]:
    return {
        "start": span.start,
        "end": span.end,
        "surface": span.surface,
        "type": span.span_type,
        "normalized": span.normalized,
        "registry_candidate": span.registry_candidate,
        "confidence": span.confidence,
        "reasoning": span.reasoning,
    }


def process_document(doc_id: int) -> None:
    settings = get_settings()
    with get_connection(settings.db_path) as connection:
        document = fetch_document(connection, doc_id)
        if document is None:
            raise ValueError(f"Document not found: {doc_id}")
        body = document.body
        digest = fetch_digest_entities(connection, limit=200)
        entities = fetch_entities_for_matching(connection)
        cache_key = text_sha256(body)
        cached = get_llm_cache(connection, cache_key)
        if cached is not None:
            payload = json.loads(cached.response_json)
            spans = [_span_from_dict(item) for item in payload.get("spans", [])]
            spans = validate_span_offsets(spans, body, settings.span_align_window)
        else:
            extraction: ExtractionResult = extract_spans_with_haiku(body, digest, settings)
            spans = validate_span_offsets(
                extraction.spans,
                body,
                settings.span_align_window,
            )
            payload = {
                "spans": [_span_to_dict(span) for span in spans],
                "raw": extraction.raw_response_text,
            }
            upsert_llm_cache(
                connection,
                LlmCacheRow(
                    text_sha256=cache_key,
                    response_json=json.dumps(payload, ensure_ascii=False),
                    model=settings.anthropic_model,
                    input_tokens=extraction.usage.input_tokens,
                    output_tokens=extraction.usage.output_tokens,
                    cached_input_tokens=extraction.usage.cached_input_tokens,
                ),
            )

        clear_nlp_for_document(connection, doc_id)
        for span in spans:
            lemma_key = span_lemma_key(span)
            normalized = span.normalized.strip() if span.normalized else span.surface
            span_id = insert_extracted_span(
                connection,
                ExtractedSpanRecord(
                    doc_id=doc_id,
                    start_offset=span.start,
                    end_offset=span.end,
                    surface_form=span.surface,
                    normalized=normalized,
                    lemma_key=lemma_key,
                    span_type=span.span_type,
                    extractor="haiku",
                ),
            )
            match = match_span_to_entity(span, lemma_key, entities, settings)
            if match is None:
                continue
            confidence = finalize_confidence(span, match)
            reasoning = build_reasoning(span, match, context_note=None)
            if (
                span.span_type == "PER"
                and settings.context_check_low <= confidence <= settings.context_check_high
            ):
                entity = _entity_by_id(entities, match.entity_id)
                if entity is None:
                    continue
                context = run_context_check(body, span.start, span.end, entity, settings)
                if not context.is_match:
                    continue
                confidence = context.confidence
                reasoning = build_reasoning(
                    span,
                    match,
                    context_note=f"context_check={context.reasoning}",
                )
            insert_mention(
                connection,
                MentionRecord(
                    doc_id=doc_id,
                    entity_id=match.entity_id,
                    span_id=span_id,
                    start_offset=span.start,
                    end_offset=span.end,
                    surface_form=span.surface,
                    confidence=min(1.0, max(0.0, confidence)),
                    match_method=match.match_method,
                    reasoning=reasoning,
                ),
            )
        connection.commit()
