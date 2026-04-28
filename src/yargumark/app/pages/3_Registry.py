from __future__ import annotations

import streamlit as st

from yargumark.app.common import (
    app_settings,
    current_ui_mode,
    db_connection,
    inject_global_styles,
    render_cost_summary,
)
from yargumark.config import ui_threshold
from yargumark.db import (
    count_entities_by_type,
    count_mentions_by_entity_type,
    latest_registry_sync_finished_at,
)
from yargumark.registry.sync import sync_registry

st.set_page_config(page_title="Registry", layout="wide")
inject_global_styles()

if "registry_sync_status" in st.session_state:
    _st = st.session_state.pop("registry_sync_status")
    if _st is True:
        st.success("Синхронизация реестра завершена.")
    elif isinstance(_st, str):
        st.error(f"Ошибка синхронизации: {_st}")

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

st.title("Статус реестров")
st.markdown(
    "**Зачем эта страница:** здесь видно, какой **справочник обязательных сущностей** загружен в систему "
    "и **насколько он свежий**. Реестры на стороне государства обновляются регулярно — без даты синхронизации "
    "нельзя честно отвечать на вопрос про актуальность данных.\n\n"
    "**Три разных процесса (важно для демо):**\n"
    "- **Обновить реестры** ниже — это загрузка **официальных и файловых** данных в базу (ETL), **без вызова LLM** "
    "и без генерации «разговорных» синонимов.\n"
    "- **Обогащение алиасов через ИИ** (отдельный сценарий, скрипт enricher) — короткий вызов Haiku **на сущность**, "
    "если нужны народные формы вроде «инста».\n"
    "- **Алиасы вручную** при добавлении записи — без стоимости LLM."
)

with db_connection() as conn:
    counts = count_entities_by_type(conn)
    last_sync = latest_registry_sync_finished_at(conn)
    mention_by_type = count_mentions_by_entity_type(conn, threshold)

if st.button("Обновить реестры", type="primary"):
    with st.spinner("Загрузка и запись в базу (может занять до нескольких минут)..."):
        try:
            sync_registry()
            st.session_state["registry_sync_status"] = True
        except Exception as exc:
            st.session_state["registry_sync_status"] = str(exc)
    st.rerun()

st.metric("Последняя успешная синхронизация", last_sync or "—")

st.subheader("Записи в справочнике по типам")
rows_registry = [
    {"Тип": entity_type, "Активных записей": count}
    for entity_type, count in sorted(counts.items(), key=lambda item: item[0])
]
st.dataframe(rows_registry, use_container_width=True, hide_index=True)

st.subheader(f"Упоминания в текстах при текущем пороге UI ({mode}, ≥ {threshold:.2f})")
if not mention_by_type:
    st.caption(
        "Пока нет упоминаний выше порога — обработайте документы через NLP или смените режим."
    )
else:
    rows_m = [
        {"Тип": t, "Число упоминаний": n}
        for t, n in sorted(mention_by_type.items(), key=lambda item: item[0])
    ]
    st.dataframe(rows_m, use_container_width=True, hide_index=True)
    st.caption(
        "Показывает, сколько раз справочник «сработал» в уже размеченных текстах при выбранном пороге."
    )

with st.expander("Масштаб и оценка стоимости LLM"), db_connection() as conn:
    render_cost_summary(conn)

with st.expander("Команда для администратора (терминал)"):
    st.code("uv run yargumark-registry-sync sync", language="bash")
