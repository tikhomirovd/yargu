from __future__ import annotations

import sqlite3

import streamlit as st

from yargumark.config import Settings, get_settings
from yargumark.db import (
    count_documents_by_source,
    get_connection,
    rollup_llm_cache_all,
    rollup_llm_cache_for_document_bodies,
)
from yargumark.pricing import estimate_llm_usd

_YM_STYLES_MARKDOWN = """
<style>
  .ym-article {
    font-size: 1rem;
    line-height: 1.55;
    color: inherit;
  }
  .ym-mark {
    background: rgba(255, 193, 7, 0.22);
    padding: 0 2px;
    border-radius: 2px;
  }
  .ym-badge {
    font-size: 0.82em;
    font-weight: 600;
    margin-left: 2px;
    white-space: nowrap;
  }
  .ym-foreign_agent { color: #b45309; }
  .ym-undesirable_org { color: #1d4ed8; }
  .ym-terrorist_extremist { color: #b91c1c; }
  .ym-banned_by_court { color: #6b21a8; }
  .ym-unknown { color: #4b5563; }
  .ym-footnotes {
    margin-top: 1.25rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(128, 128, 128, 0.35);
    font-size: 0.9rem;
    opacity: 0.95;
  }
  [data-testid="stDataFrame"],
  [data-testid="stTable"] {
    background-color: color-mix(in srgb, var(--background-color, #fff) 100%, transparent) !important;
    color: inherit !important;
    opacity: 1 !important;
    border: 1px solid rgba(120, 120, 120, 0.35);
    border-radius: 0.35rem;
  }
  [data-testid="stDataFrame"] [role="grid"],
  [data-testid="stDataFrame"] .glide-data-grid {
    opacity: 1 !important;
  }
</style>
"""


def inject_global_styles() -> None:
    st.markdown(_YM_STYLES_MARKDOWN, unsafe_allow_html=True)


def app_settings() -> Settings:
    return get_settings()


def db_connection() -> sqlite3.Connection:
    settings = app_settings()
    return get_connection(settings.db_path)


def current_ui_mode() -> str:
    if "ui_mode" not in st.session_state:
        st.session_state["ui_mode"] = app_settings().mode.strip().lower()
    return str(st.session_state["ui_mode"])


def render_cost_summary(connection: sqlite3.Connection) -> None:
    """Сводка по объёму корпуса и строкам кеша LLM."""
    counts = count_documents_by_source(connection)
    corpus = rollup_llm_cache_for_document_bodies(connection)
    all_cache = rollup_llm_cache_all(connection)
    other_rows = max(0, all_cache.row_count - corpus.row_count)
    other_in = max(0, all_cache.input_tokens - corpus.input_tokens)
    other_out = max(0, all_cache.output_tokens - corpus.output_tokens)

    st.markdown(f"**Документов в базе:** {counts.total}")
    for src, n in sorted(counts.by_source.items()):
        st.markdown(f"- `{src}`: {n}")

    denom = corpus.row_count if corpus.row_count > 0 else 0
    avg_in = corpus.input_tokens / denom if denom else 0
    avg_out = corpus.output_tokens / denom if denom else 0
    avg_usd = estimate_llm_usd(int(avg_in), int(avg_out))
    total_corpus_usd = estimate_llm_usd(corpus.input_tokens, corpus.output_tokens)

    st.markdown("**Кеш разметки текстов** (основной вызов Haiku по телу страницы):")
    if corpus.row_count == 0:
        st.caption("Записей нет — обработайте документы через NLP.")
    else:
        st.markdown(
            f"- Записей: **{corpus.row_count}**, токены: "
            f"**{corpus.input_tokens + corpus.output_tokens:,}**, "
            f"оценка **~${total_corpus_usd:.2f}** · в среднем на документ **~${avg_usd:.4f}**"
        )

    st.markdown("**Прочий кеш** (обогащение алиасов и т.п.):")
    st.caption(
        f"Записей: **{other_rows}**, токены: **{other_in + other_out:,}**, "
        f"оценка **~${estimate_llm_usd(other_in, other_out):.2f}**."
    )
