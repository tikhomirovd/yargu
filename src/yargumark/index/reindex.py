from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

from yargumark.config import Settings, get_settings
from yargumark.db import (
    ExtractedSpanRow,
    MentionRecord,
    clear_render_cache,
    delete_all_mentions,
    fetch_all_extracted_spans,
    fetch_entities_for_matching,
    get_connection,
    insert_mention,
)
from yargumark.nlp.confidence_rules import build_reasoning, finalize_confidence
from yargumark.nlp.matcher import match_span_to_entity
from yargumark.nlp.types import LlmSpan


@dataclass(frozen=True)
class ReindexStats:
    elapsed_ms: int
    spans_processed: int
    mentions_written: int
    documents_touched: int
    affected_doc_ids: tuple[int, ...]


def _row_to_llm_span(row: ExtractedSpanRow) -> LlmSpan:
    return LlmSpan(
        start=row.start_offset,
        end=row.end_offset,
        surface=row.surface_form,
        span_type=row.span_type,
        normalized=row.normalized,
        registry_candidate=None,
        confidence=0.99,
        reasoning="reindex_from_extracted_spans",
    )


def reindex_mentions_from_extracted_spans(
    connection: sqlite3.Connection,
    settings: Settings | None = None,
) -> ReindexStats:
    """
    Rebuild mentions from stored extracted_spans using deterministic matching only (no LLM).
    Invalidates render_cache for all documents.
    """
    resolved = settings or get_settings()
    started = time.perf_counter()
    delete_all_mentions(connection)
    clear_render_cache(connection)
    entities = fetch_entities_for_matching(connection)
    spans = fetch_all_extracted_spans(connection)
    documents_touched: set[int] = set()
    mentions_written = 0
    for row in spans:
        documents_touched.add(row.doc_id)
        span = _row_to_llm_span(row)
        match = match_span_to_entity(span, row.lemma_key, entities, resolved)
        if match is None:
            continue
        confidence = finalize_confidence(span, match)
        reasoning = build_reasoning(span, match, context_note=None)
        insert_mention(
            connection,
            MentionRecord(
                doc_id=row.doc_id,
                entity_id=match.entity_id,
                span_id=row.id,
                start_offset=row.start_offset,
                end_offset=row.end_offset,
                surface_form=row.surface_form,
                confidence=min(1.0, max(0.0, confidence)),
                match_method=match.match_method,
                reasoning=reasoning,
            ),
        )
        mentions_written += 1
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return ReindexStats(
        elapsed_ms=elapsed_ms,
        spans_processed=len(spans),
        mentions_written=mentions_written,
        documents_touched=len(documents_touched),
        affected_doc_ids=tuple(sorted(documents_touched)),
    )


def run_reindex_cli() -> None:
    settings = get_settings()
    with get_connection(settings.db_path) as connection:
        stats = reindex_mentions_from_extracted_spans(connection, settings)
        connection.commit()
    print(
        "Reindex done: "
        f"ms={stats.elapsed_ms}, spans={stats.spans_processed}, "
        f"mentions={stats.mentions_written}, docs_touched={stats.documents_touched}, "
        f"doc_ids={list(stats.affected_doc_ids)[:10]}"
    )
