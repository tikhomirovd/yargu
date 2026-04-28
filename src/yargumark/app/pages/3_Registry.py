from __future__ import annotations

import streamlit as st

from yargumark.app.common import db_connection, inject_global_styles
from yargumark.db import count_entities_by_type, latest_registry_sync_finished_at

st.set_page_config(page_title="Registry", layout="wide")
inject_global_styles()
st.title("Статус реестров")

with db_connection() as conn:
    counts = count_entities_by_type(conn)
    last_sync = latest_registry_sync_finished_at(conn)

st.metric("Последняя успешная синхронизация", last_sync or "—")
st.subheader("Количество активных записей по типам")
st.table(
    [
        {"type": entity_type, "count": count}
        for entity_type, count in sorted(counts.items(), key=lambda item: item[0])
    ]
)
st.caption("Обновление: `uv run yargumark-registry-sync sync`")
