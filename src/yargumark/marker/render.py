from __future__ import annotations

import sqlite3

from yargumark.config import Settings, get_settings, ui_threshold
from yargumark.db import (
    MentionMarkupRow,
    RenderCacheRow,
    compute_mentions_hash,
    fetch_document_detail,
    fetch_mentions_for_markup,
    get_render_cache,
    upsert_render_cache,
)
from yargumark.marker.markup import MentionPaint, build_marked_html, wrap_article


def _normalize_ui_mode(ui_mode: str) -> str:
    return "production" if ui_mode.strip().lower() == "production" else "demo"


def _rows_to_paint(rows: list[MentionMarkupRow]) -> list[MentionPaint]:
    return [
        MentionPaint(
            start=row.start,
            end=row.end,
            surface=row.surface,
            entity_type=row.entity_type,
            canonical_name=row.canonical_name,
            confidence=row.confidence,
            match_method=row.match_method,
            reasoning=row.reasoning,
        )
        for row in rows
    ]


def render_document_html(
    connection: sqlite3.Connection,
    doc_id: int,
    ui_mode: str,
    settings: Settings | None = None,
    use_cache: bool = True,
) -> str:
    resolved = settings or get_settings()
    mode_key = _normalize_ui_mode(ui_mode)
    threshold = ui_threshold(resolved, mode_key)
    current_hash = compute_mentions_hash(connection, doc_id, threshold)
    if use_cache:
        cached = get_render_cache(connection, doc_id, mode_key)
        if cached is not None and cached.mentions_hash == current_hash:
            return cached.html_marked
    detail = fetch_document_detail(connection, doc_id)
    if detail is None:
        raise ValueError(f"Document not found: {doc_id}")
    rows = fetch_mentions_for_markup(connection, doc_id, threshold)
    marked = build_marked_html(detail.body, _rows_to_paint(rows))
    html = wrap_article(marked.html_body, marked.footnotes_html)
    upsert_render_cache(
        connection,
        RenderCacheRow(
            doc_id=doc_id,
            mode=mode_key,
            html_marked=html,
            mentions_hash=current_hash,
        ),
    )
    return html
