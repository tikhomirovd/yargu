from __future__ import annotations

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.config import ui_threshold
from yargumark.db import list_documents_with_mentions

st.set_page_config(page_title="Библиотека новостей", layout="wide")
inject_global_styles()
st.title("Библиотека новостей")
st.caption("Список страниц в базе и число срабатываний реестра при текущем пороге.")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

_SOURCE_KEYS = ("all", "uniyar", "demo")


def _source_label(key: str) -> str:
    if key == "all":
        return "Все"
    if key == "uniyar":
        return "Университетский сайт (uniyar)"
    if key == "demo":
        return "Демо (demo)"
    return key


source = st.selectbox(
    "Источник",
    options=list(_SOURCE_KEYS),
    index=0,
    format_func=_source_label,
)
source_filter = None if source == "all" else source
only_marked = st.checkbox("Только помеченные документы", value=False)

with db_connection() as conn:
    rows = list_documents_with_mentions(
        conn,
        threshold,
        source=source_filter,
        limit=500,
        only_with_mentions=only_marked,
    )

data = [
    {
        "Заголовок": row.title,
        "Ссылка": row.url,
        "Опубликовано": row.published_at or "—",
        "Источник": row.source,
        "Упоминаний": row.mention_count,
    }
    for row in rows
]
st.dataframe(
    data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ссылка": st.column_config.LinkColumn("Ссылка", display_text="Открыть"),
        "Упоминаний": st.column_config.NumberColumn("Упоминаний", format="%d"),
    },
)
st.caption(f"Режим: **{mode}**, порог: **{threshold:.2f}**")
