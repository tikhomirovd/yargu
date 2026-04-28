from __future__ import annotations

import html

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.config import ui_threshold
from yargumark.db import (
    fetch_document_detail,
    fetch_mentions_for_markup,
    list_documents_with_mentions,
)
from yargumark.marker.render import render_document_html

st.set_page_config(page_title="Документ", layout="wide")
inject_global_styles()
st.title("Документ")
st.caption("Слева — оригинал, справа — текст с правовыми плашками.")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

show_all_docs = st.checkbox(
    "Показать все документы",
    value=False,
    help=(
        "Без галки видны только страницы, где найдена хотя бы одна сущность из реестра "
        "при текущем пороге уверенности."
    ),
)

with db_connection() as conn:
    catalog = list_documents_with_mentions(
        conn,
        threshold,
        limit=500,
        only_with_mentions=not show_all_docs,
    )

if not catalog:
    if not show_all_docs:
        st.warning(
            "Нет документов, в которых сработал реестр при текущем пороге. "
            "Включите «Показать все документы» или смените режим в боковой панели."
        )
    else:
        st.warning("В базе нет документов. Запустите краулер или сидер.")
    st.stop()


def _label(title: str, published_at: str | None) -> str:
    base = (title or "").strip() or "Без названия"
    if published_at:
        return f"{base}  ·  {published_at}"
    return base


options: dict[str, int] = {}
for row in catalog:
    label = _label(row.title, row.published_at)
    if label in options:
        label = f"{label}  ({row.id})"
    options[label] = row.id

choice = st.selectbox("Документ", options=list(options.keys()))
doc_id = options[choice]

with db_connection() as conn:
    detail = fetch_document_detail(conn, doc_id)
    mentions = fetch_mentions_for_markup(conn, doc_id, threshold)
    marked_html = render_document_html(conn, doc_id, mode, settings=settings)

if detail is None:
    st.error("Документ не найден.")
    st.stop()

article_title = (detail.title or "").strip() or "Без названия"
st.markdown(f"### [{article_title}]({detail.url})")
meta_parts: list[str] = []
if detail.published_at:
    meta_parts.append(f"Опубликовано: {detail.published_at}")
meta_parts.append(f"Источник: {detail.source}")
st.caption(" · ".join(meta_parts))

left, right = st.columns(2)
with left:
    st.subheader("Оригинал")
    st.text(detail.body)
with right:
    st.subheader("Размеченный текст")
    st.markdown(marked_html, unsafe_allow_html=True)

st.subheader("Почему так")
if not mentions:
    st.caption("При текущем пороге сработавших упоминаний нет.")
for mention in mentions:
    st.markdown(
        "- "
        f"**{html.escape(mention.surface)}** → `{html.escape(mention.canonical_name)}` "
        f"({html.escape(mention.entity_type)}), метод `{html.escape(mention.match_method)}`, "
        f"уверенность `{mention.confidence:.2f}`. "
        f"{html.escape(mention.reasoning)}"
    )
