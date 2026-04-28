from __future__ import annotations

import html

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection
from yargumark.config import ui_threshold
from yargumark.db import DocumentRecord, upsert_document
from yargumark.marker.render import render_document_html
from yargumark.nlp.pipeline import process_document

st.set_page_config(page_title="Sandbox", layout="wide")
st.title("Песочница")

SANDBOX_URL = "sandbox://scratch"
settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

_default = "Студенты обсуждали Инста и модерацию контента."
_prev = st.session_state.get("sandbox_text", _default)
default_text = _prev if isinstance(_prev, str) else _default
body = st.text_area("Текст", value=default_text, height=200)
st.session_state["sandbox_text"] = body

if st.button("Запустить пайплайн (Haiku + матчинг)", type="primary"):
    if not settings.anthropic_api_key:
        st.error("Нужен ANTHROPIC_API_KEY в .env")
    else:
        with st.spinner("Обработка..."):
            with db_connection() as conn:
                doc_id = upsert_document(
                    conn,
                    DocumentRecord(
                        url=SANDBOX_URL,
                        title="Sandbox",
                        body=body,
                        html_raw=f"<pre>{html.escape(body)}</pre>",
                        published_at=None,
                        source="demo",
                    ),
                )
                conn.commit()
            process_document(doc_id)
            with db_connection() as conn:
                marked_html = render_document_html(conn, doc_id, mode, settings=settings)
        st.session_state["sandbox_doc_id"] = doc_id
        st.session_state["sandbox_html"] = marked_html
        st.success(f"Готово. doc_id={doc_id}")

if "sandbox_html" in st.session_state:
    st.subheader("Размеченный HTML")
    st.markdown(st.session_state["sandbox_html"], unsafe_allow_html=True)
    st.caption(f"Режим **{mode}**, порог **{threshold:.2f}**")
