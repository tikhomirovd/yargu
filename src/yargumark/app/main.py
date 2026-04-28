from __future__ import annotations

import streamlit as st

from yargumark.app.common import app_settings
from yargumark.config import ui_threshold

st.set_page_config(page_title="YarguMark", layout="wide")

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
    "Локальный MVP: краулинг, реестры, извлечение упоминаний (Haiku), "
    "детерминированный матчинг и юридические плашки."
)
st.info("Откройте разделы в боковом меню **Streamlit Pages**.")
