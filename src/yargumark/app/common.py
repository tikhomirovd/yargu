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
    """Блок «масштаб и оценка стоимости LLM» для главной и при необходимости других страниц."""
    counts = count_documents_by_source(connection)
    corpus = rollup_llm_cache_for_document_bodies(connection)
    all_cache = rollup_llm_cache_all(connection)
    other_rows = max(0, all_cache.row_count - corpus.row_count)
    other_in = max(0, all_cache.input_tokens - corpus.input_tokens)
    other_out = max(0, all_cache.output_tokens - corpus.output_tokens)

    parts = [f"**Всего страниц в базе:** {counts.total}"]
    for src, n in sorted(counts.by_source.items()):
        parts.append(f"- `{src}`: {n}")
    st.markdown("\n".join(parts))

    denom = corpus.row_count if corpus.row_count > 0 else 0
    avg_in = corpus.input_tokens / denom if denom else 0
    avg_out = corpus.output_tokens / denom if denom else 0
    avg_usd = estimate_llm_usd(int(avg_in), int(avg_out))
    total_corpus_usd = estimate_llm_usd(corpus.input_tokens, corpus.output_tokens)

    st.markdown(
        "**Разметка текстов страниц** "
        "(основной вызов Haiku по содержимому, данные из кеша запросов):"
    )
    if corpus.row_count == 0:
        st.caption(
            "Пока нет строк кеша, совпадающих с текстами документов — запустите NLP по страницам."
        )
    else:
        st.markdown(
            f"- Уникальных текстов с кешем: **{corpus.row_count}** · "
            f"сумма input+output токенов: **{corpus.input_tokens + corpus.output_tokens:,}** "
            f"(оценка **~${total_corpus_usd:.2f}**)\n"
            f"- В среднем на один такой текст: **~{avg_in + avg_out:,.0f}** токенов "
            f"(**~${avg_usd:.4f}** — ориентир; тарифы меняются)."
        )

    st.markdown(
        "**Прочие вызовы в кеше** (обогащение алиасов и др., ключ не совпадает с телом страницы):"
    )
    st.caption(
        f"Строк в кеше: **{other_rows}** · input+output токенов: **{other_in + other_out:,}** "
        f"(~**${estimate_llm_usd(other_in, other_out):.2f}**)."
    )
    st.caption(
        "Подтянуть официальный реестр в БД и переиндексировать архив без повторного чтения текстов "
        "моделью — **без стоимости LLM**. Отдельный вызов Haiku на обогащение синонимов для одной "
        "организации — обычно один короткий запрос (см. прочие строки кеша после запуска enricher)."
    )
    st.caption(
        "Дополнительные context-check вызовы для персон могут не входить в «одну строку» кеша на "
        "страницу — при необходимости уточняйте по логам API."
    )
