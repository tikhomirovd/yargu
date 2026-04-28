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
        "Режим UI (порог уверенности)",
        options=["demo", "production"],
        key="ui_mode",
        help=(
            "Demo: выше порог — меньше ложных срабатываний. "
            "Production: ниже порог — выше полнота (recall)."
        ),
    )
    current_mode = str(st.session_state["ui_mode"])
    threshold = ui_threshold(settings, current_mode)
    st.caption(f"Текущий порог: **{threshold:.2f}**")

st.title("YarguMark")
st.markdown(
    "Прототип для демонстрации: система находит в текстах страниц упоминания лиц и организаций "
    "из официальных реестров, расставляет **юридически корректные формулировки** (плашки) и "
    "показывает **объяснение** по каждому срабатыванию."
)
st.markdown(
    "**Рекомендуемый порядок демо:**\n"
    "1. Просмотр документа — разметка и «почему так».\n"
    "2. Библиотека новостей — масштаб корпуса.\n"
    "3. Статус реестров — свежесть справочника и охват.\n"
    "4. При необходимости: песочница, обновление реестра без повторного ИИ по архиву, тестовые кейсы."
)

c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/1_Document.py", label="Просмотр документа", icon="📄")
with c2:
    st.page_link("pages/2_News_Library.py", label="Библиотека новостей", icon="📚")
with c3:
    st.page_link("pages/3_Registry.py", label="Статус реестров", icon="📋")

with st.expander("Масштаб и оценка стоимости LLM (ориентир для бизнеса)", expanded=False):
    st.caption(
        "Оценка в долларах по умолч. тарифам Haiku в `yargumark.pricing`; не официальный счёт Anthropic."
    )
    with db_connection() as conn:
        render_cost_summary(conn)
