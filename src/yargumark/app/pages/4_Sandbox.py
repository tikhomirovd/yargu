from __future__ import annotations

import html

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.config import ui_threshold
from yargumark.db import (
    DocumentRecord,
    fetch_document_detail,
    fetch_mentions_for_markup,
    upsert_document,
)
from yargumark.marker.render import render_document_html
from yargumark.nlp.pipeline import process_document

st.set_page_config(page_title="Sandbox", layout="wide")
inject_global_styles()
st.title("Песочница")

st.markdown(
    "**Зачем эта страница:** проверить произвольный абзац **без краулера**: система прогоняет тот же пайплайн, "
    "что и для сохранённых страниц (Haiku + матчинг), и показывает результат.\n\n"
    "**Когда показывать в демо:** когда нужно быстро показать пример на своём тексте.\n\n"
    "**Режим в боковой панели** (demo / production) задаёт **порог уверенности**: в demo часть кандидатов "
    "скрывается — если плашек мало, переключите production или уточните текст."
)

SANDBOX_URL = "sandbox://scratch"
settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

_default = (
    "На семинаре обсудили роль мессенджеров: часть студентов предпочитает телегу для объявлений, "
    "в отдельных сообщениях фигурировали отсылки к деятельности ФБК и к площадкам Meta в контексте регистрации СМИ."
)
_prev = st.session_state.get("sandbox_text", _default)
default_text = _prev if isinstance(_prev, str) else _default
body = st.text_area("Вставьте текст для проверки", value=default_text, height=220)
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
            st.session_state["sandbox_doc_id"] = doc_id
        st.success(f"Готово. Внутренний id документа: {doc_id}")

if "sandbox_doc_id" in st.session_state:
    _sid = int(st.session_state["sandbox_doc_id"])
    with db_connection() as conn:
        detail = fetch_document_detail(conn, _sid)
        marked_html = render_document_html(conn, _sid, mode, settings=settings)
        mentions = fetch_mentions_for_markup(conn, _sid, threshold)

    st.subheader("Как увидит читатель (с плашками)")
    st.caption(
        f"Режим **{mode}**, порог **{threshold:.2f}** — при другом режиме число подсветок может измениться."
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Исходный текст")
        if detail is not None:
            st.text(detail.body)
    with right:
        st.subheader("Версия с маркировкой")
        st.markdown(marked_html, unsafe_allow_html=True)

    st.subheader("Почему так")
    if not mentions:
        st.caption(
            "Нет упоминаний выше порога. Попробуйте режим production в боковой панели или более явные формулировки."
        )
    for mention in mentions:
        st.markdown(
            "- "
            f"**{html.escape(mention.surface)}** → `{html.escape(mention.canonical_name)}` "
            f"({html.escape(mention.entity_type)}), метод `{html.escape(mention.match_method)}`, "
            f"уверенность `{mention.confidence:.2f}`. "
            f"{html.escape(mention.reasoning)}"
        )
