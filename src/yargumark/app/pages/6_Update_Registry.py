from __future__ import annotations

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.config import ui_threshold
from yargumark.db import EntityRecord, fetch_document_detail, upsert_entity
from yargumark.index.reindex import reindex_mentions_from_extracted_spans
from yargumark.marker.render import render_document_html
from yargumark.registry.lemmatize import to_lemma_key
from yargumark.registry.normalize import normalize_name

st.set_page_config(page_title="Update Registry Demo", layout="wide")
inject_global_styles()
st.title("Демо: обновление реестра без LLM")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

st.markdown(
    "Добавьте тестовую запись в реестр и пересоберите упоминания **только из сохранённых "
    "`extracted_spans`** — без вызова Haiku. Кеш разметки сбрасывается."
)

with st.form("registry_add"):
    entity_type = st.selectbox(
        "Тип",
        options=[
            "foreign_agent",
            "undesirable_org",
            "terrorist_extremist",
            "banned_by_court",
        ],
    )
    canonical_name = st.text_input("Каноническое имя", value="Demo Org")
    registry_source = st.text_input("Источник реестра", value="demo_ui")
    registry_id = st.text_input("ID в реестре", value="demo-001")
    aliases_text = st.text_input("Алиасы через запятую", value="Alias RU, DemoOrg")
    submitted = st.form_submit_button("Добавить и переиндексировать")

if submitted:
    aliases = [normalize_name(part) for part in aliases_text.split(",") if normalize_name(part)]
    canonical = normalize_name(canonical_name)
    if not canonical:
        st.error("Укажите каноническое имя.")
        st.stop()
    lemma_key = to_lemma_key(canonical)
    record = EntityRecord(
        entity_type=entity_type,
        canonical_name=canonical,
        registry_source=registry_source.strip(),
        registry_id=registry_id.strip(),
        included_at=None,
        aliases=aliases or [canonical],
        lemma_key=lemma_key,
    )
    with db_connection() as conn:
        created = upsert_entity(conn, record)
        stats = reindex_mentions_from_extracted_spans(conn, settings)
        conn.commit()
    st.success(
        f"Запись {'создана' if created else 'обновлена'}. "
        f"Переиндекс за **{stats.elapsed_ms} ms**: spans={stats.spans_processed}, "
        f"mentions={stats.mentions_written}, документов по extracted_spans: "
        f"{stats.documents_touched}. LLM не вызывалась."
    )
    st.caption("Стоимость LLM для этого шага: **$0** (только SQLite + fuzzy/lemma).")

    preview_id: int | None = None
    with db_connection() as conn:
        for doc_id in stats.affected_doc_ids:
            detail_row = fetch_document_detail(conn, doc_id)
            if detail_row is not None and detail_row.body.strip():
                preview_id = doc_id
                break
    if preview_id is not None:
        st.subheader("Пример документа до / после")
        with db_connection() as conn:
            detail = fetch_document_detail(conn, preview_id)
            marked = render_document_html(conn, preview_id, mode, settings=settings)
        if detail is not None:
            left, right = st.columns(2)
            with left:
                st.caption(f"doc_id={preview_id}, порог **{threshold:.2f}**")
                st.text(detail.body)
            with right:
                st.markdown(marked, unsafe_allow_html=True)
