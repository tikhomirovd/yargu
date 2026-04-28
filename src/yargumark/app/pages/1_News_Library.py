from __future__ import annotations

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection
from yargumark.config import ui_threshold
from yargumark.db import list_documents_with_mentions

st.set_page_config(page_title="News Library", layout="wide")
st.title("Библиотека новостей")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

source = st.selectbox("Источник", options=["all", "uniyar", "demo"], index=0)
source_filter = None if source == "all" else source
only_marked = st.checkbox("Только помеченные документы", value=False)

with db_connection() as conn:
    rows = list_documents_with_mentions(conn, threshold, source=source_filter, limit=500)

if only_marked:
    rows = [row for row in rows if row.mention_count > 0]

data = [
    {
        "id": row.id,
        "title": row.title,
        "url": row.url,
        "published_at": row.published_at or "",
        "source": row.source,
        "mentions": row.mention_count,
    }
    for row in rows
]
st.dataframe(data, use_container_width=True, hide_index=True)
st.caption(f"Режим: **{mode}**, порог: **{threshold:.2f}**")
