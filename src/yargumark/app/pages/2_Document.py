from __future__ import annotations

import html

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection
from yargumark.config import ui_threshold
from yargumark.db import (
    fetch_document_detail,
    fetch_mentions_for_markup,
    list_documents_with_mentions,
)
from yargumark.marker.render import render_document_html

st.set_page_config(page_title="Document", layout="wide")
st.title("Просмотр документа")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

with db_connection() as conn:
    catalog = list_documents_with_mentions(conn, threshold, limit=500)

if not catalog:
    st.warning("Нет документов в базе. Запустите краулер или scripts/seed_demo.py.")
    st.stop()

options = {f"{row.id} — {row.title[:80]}": row.id for row in catalog}
choice = st.selectbox("Документ", options=list(options.keys()))
doc_id = options[choice]

with db_connection() as conn:
    detail = fetch_document_detail(conn, doc_id)
    mentions = fetch_mentions_for_markup(conn, doc_id, threshold)
    marked_html = render_document_html(conn, doc_id, mode, settings=settings)

if detail is None:
    st.error("Документ не найден.")
    st.stop()

left, right = st.columns(2)
with left:
    st.subheader("Оригинал")
    st.text(detail.body)
with right:
    st.subheader("Размеченный текст")
    st.markdown(marked_html, unsafe_allow_html=True)

st.subheader("Почему так")
if not mentions:
    st.caption("Нет упоминаний выше порога для текущего режима.")
for mention in mentions:
    st.markdown(
        "- "
        f"**{html.escape(mention.surface)}** → `{html.escape(mention.canonical_name)}` "
        f"({html.escape(mention.entity_type)}), метод `{html.escape(mention.match_method)}`, "
        f"уверенность `{mention.confidence:.2f}`. "
        f"{html.escape(mention.reasoning)}"
    )
