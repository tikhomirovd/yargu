from __future__ import annotations

import streamlit as st

from yargumark.app.common import (
    app_settings,
    db_connection,
    inject_global_styles,
    render_cost_summary,
)
from yargumark.config import ui_threshold

st.set_page_config(page_title="YarguMark", layout="wide")
inject_global_styles()

settings = app_settings()
if "ui_mode" not in st.session_state:
    st.session_state["ui_mode"] = settings.mode.strip().lower()

with st.sidebar:
    st.selectbox(
        "Режим (порог уверенности)",
        options=["demo", "production"],
        key="ui_mode",
        help=(
            "В режиме demo порог выше — меньше ложных срабатываний. "
            "В production порог ниже — выше полнота (recall)."
        ),
    )
    current_mode = str(st.session_state["ui_mode"])
    threshold = ui_threshold(settings, current_mode)
    st.caption(f"Текущий порог: **{threshold:.2f}**")

st.title("YarguMark")
st.markdown(
    "Система находит в текстах упоминания лиц и организаций из официальных реестров, "
    "расставляет **обязательные формулировки** и показывает **обоснование** по каждому срабатыванию."
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/1_Document.py", label="Документ", icon="📄")
with c2:
    st.page_link("pages/2_News_Library.py", label="Библиотека новостей", icon="📚")
with c3:
    st.page_link("pages/3_Registry.py", label="Статус реестров", icon="📋")
with c4:
    st.page_link("pages/5_Registry_Editor.py", label="Реестр и алиасы", icon="🧩")

st.page_link("pages/4_Sandbox.py", label="Песочница", icon="🧪")

with st.expander("Объём корпуса и кеш LLM", expanded=False):
    st.caption("Оценка в долларах по настройкам в `yargumark.pricing`; не счёт от Anthropic.")
    with db_connection() as conn:
        render_cost_summary(conn)
