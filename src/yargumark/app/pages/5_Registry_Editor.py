from __future__ import annotations

import html

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.config import ui_threshold
from yargumark.db import (
    EntityRecord,
    count_entities_for_overview,
    delete_entity_alias,
    ensure_entity_aliases_supports_manual,
    fetch_entity_aliases_with_kind,
    fetch_entity_brief,
    list_entities_overview,
    try_insert_enriched_alias,
    upsert_entity,
)
from yargumark.index.reindex import reindex_mentions_from_extracted_spans
from yargumark.registry.alias_enricher import classify_alias_kind, enrich_entity_aliases
from yargumark.registry.lemmatize import to_lemma_key
from yargumark.registry.normalize import normalize_name

st.set_page_config(page_title="Реестр и алиасы", layout="wide")
inject_global_styles()

st.title("Реестр и алиасы")
st.caption(
    "Поиск по справочнику, просмотр алиасов, ручное добавление и генерация вариантов через Haiku. "
    "После изменений выполняется переиндекс без повторного вызова LLM по архиву."
)

settings = app_settings()
mode = current_ui_mode()
threshold = ui_threshold(settings, mode)

_TYPE_ORDER = (
    "foreign_agent",
    "undesirable_org",
    "terrorist_extremist",
    "banned_by_court",
)

_TYPE_LABEL_RU: dict[str, str] = {
    "foreign_agent": "Иностранный агент",
    "undesirable_org": "Нежелательная организация",
    "terrorist_extremist": "Террорист / экстремист",
    "banned_by_court": "Запрещена по решению суда",
}


def _type_filter_label(t: str | None) -> str:
    if t is None:
        return "Все типы"
    return _TYPE_LABEL_RU.get(t, t)


with db_connection() as conn:
    ensure_entity_aliases_supports_manual(conn)
    conn.commit()

search = st.text_input("Поиск", placeholder="Имя, идентификатор или источник")
type_choice = st.selectbox(
    "Тип",
    options=(None, *_TYPE_ORDER),
    format_func=_type_filter_label,
)
page_size = st.selectbox("Строк на странице", options=(25, 50, 100), index=1)

with db_connection() as conn:
    total = count_entities_for_overview(conn, search=search or None, entity_type=type_choice)

total_pages = max(1, (total + page_size - 1) // page_size)
page = st.number_input("Страница", min_value=1, max_value=total_pages, value=1, step=1)
offset = (int(page) - 1) * int(page_size)

with db_connection() as conn:
    rows = list_entities_overview(
        conn,
        min_confidence=threshold,
        search=search or None,
        entity_type=type_choice,
        limit=int(page_size),
        offset=int(offset),
    )

st.caption(f"Всего записей: **{total}** · режим UI: **{mode}**, порог упоминаний: **{threshold:.2f}**")

overview_rows = [
    {
        "ID": r.id,
        "Каноническое имя": r.canonical_name,
        "Тип": _TYPE_LABEL_RU.get(r.entity_type, r.entity_type),
        "Источник": r.registry_source,
        "ID в источнике": r.registry_id,
        "Алиасов": r.alias_count,
        "Упоминаний": r.mention_count,
    }
    for r in rows
]
st.dataframe(
    overview_rows,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ID": st.column_config.NumberColumn("ID", format="%d"),
        "Алиасов": st.column_config.NumberColumn("Алиасов", format="%d"),
        "Упоминаний": st.column_config.NumberColumn("Упоминаний", format="%d"),
    },
)

entity_options = [r.id for r in rows]
selected_id: int | None
if entity_options:
    labels_map = {r.id: f"{r.canonical_name}  [{r.id}]" for r in rows}
    picked = st.selectbox(
        "Выберите сущность",
        options=entity_options,
        format_func=lambda eid: labels_map[int(eid)],
    )
    selected_id = int(picked)
else:
    selected_id = None
    st.info("Нет строк на этой странице — смените фильтр или страницу.")

if selected_id is not None:
    st.subheader("Сущность и алиасы")
    with db_connection() as conn:
        brief = fetch_entity_brief(conn, int(selected_id))
        pairs = fetch_entity_aliases_with_kind(conn, int(selected_id))

    if brief is None:
        st.error("Запись не найдена.")
    else:
        canonical_name, etype = brief
        st.markdown(
            f"**{html.escape(canonical_name)}** · {_TYPE_LABEL_RU.get(etype, etype)} "
            f"· порог упоминаний в таблице: **{threshold:.2f}**"
        )

        alias_lines = [
            f"`{html.escape(alias)}` — _{html.escape(kind)}_"
            for alias, kind in pairs
        ]
        if alias_lines:
            st.markdown("Алиасы:\n\n" + "\n\n".join(f"- {line}" for line in alias_lines))
        else:
            st.caption("Алиасов пока нет.")

        new_alias = st.text_input("Новый алиас", key=f"na_{selected_id}")
        if st.button("Добавить алиас вручную", key=f"add_{selected_id}"):
            normalized = normalize_name(new_alias)
            if not normalized:
                st.warning("Введите непустой алиас.")
            else:
                with db_connection() as conn:
                    ensure_entity_aliases_supports_manual(conn)
                    inserted = try_insert_enriched_alias(
                        conn, int(selected_id), normalized, "manual"
                    )
                    if inserted:
                        stats = reindex_mentions_from_extracted_spans(conn, settings)
                        conn.commit()
                        st.success(
                            f"Добавлено. Переиндекс: {stats.elapsed_ms} ms, "
                            f"mentions={stats.mentions_written}."
                        )
                    else:
                        conn.commit()
                        st.info("Такой алиас уже есть.")

        if pairs:
            del_alias = st.selectbox(
                "Удалить алиас",
                options=[p[0] for p in pairs],
                key=f"del_sel_{selected_id}",
            )
            if st.button("Удалить выбранный алиас", key=f"del_btn_{selected_id}"):
                with db_connection() as conn:
                    deleted = delete_entity_alias(conn, int(selected_id), del_alias)
                    if deleted:
                        stats = reindex_mentions_from_extracted_spans(conn, settings)
                        conn.commit()
                        st.success(
                            f"Удалено. Переиндекс: {stats.elapsed_ms} ms, "
                            f"mentions={stats.mentions_written}."
                        )
                    else:
                        conn.commit()
                        st.warning("Не удалось удалить.")

        st.markdown("---")
        st.markdown("**Генерация алиасов (Haiku)**")
        if not settings.anthropic_api_key:
            st.warning("Для генерации нужен `ANTHROPIC_API_KEY` в окружении.")
        else:
            if st.button("Сгенерировать варианты", key=f"gen_{selected_id}"):
                with st.spinner("Запрос к модели…"):
                    try:
                        with db_connection() as conn:
                            ensure_entity_aliases_supports_manual(conn)
                            candidates = enrich_entity_aliases(
                                conn,
                                int(selected_id),
                                canonical_name,
                                etype,
                                settings=settings,
                            )
                            conn.commit()
                        st.session_state[f"candidates_{selected_id}"] = candidates
                    except Exception as exc:
                        st.error(str(exc))

            cand_key = f"candidates_{selected_id}"
            raw_candidates = st.session_state.get(cand_key)
            if isinstance(raw_candidates, list) and raw_candidates:
                opts = [str(x) for x in raw_candidates]
                chosen: list[str] = st.multiselect(
                    "Кандидаты для добавления",
                    options=opts,
                    default=opts,
                    key=f"multi_{selected_id}",
                )
                if st.button("Добавить выбранные кандидаты", key=f"acc_{selected_id}"):
                    added = 0
                    with db_connection() as conn:
                        ensure_entity_aliases_supports_manual(conn)
                        for line in chosen:
                            kind = classify_alias_kind(line)
                            if try_insert_enriched_alias(conn, int(selected_id), line, kind):
                                added += 1
                        stats = reindex_mentions_from_extracted_spans(conn, settings)
                        conn.commit()
                    st.success(
                        f"Добавлено новых: **{added}**. Переиндекс: {stats.elapsed_ms} ms, "
                        f"mentions={stats.mentions_written}."
                    )
                    st.session_state[cand_key] = []

with st.expander("Добавить новую запись в справочник"):
    with st.form("registry_add"):
        entity_type = st.selectbox(
            "Тип",
            options=list(_TYPE_ORDER),
            format_func=lambda t: _TYPE_LABEL_RU.get(t, t),
        )
        canonical_name = st.text_input("Каноническое имя")
        registry_source = st.text_input("Источник реестра")
        registry_id = st.text_input("ID в реестре")
        aliases_text = st.text_input("Алиасы через запятую")
        submitted = st.form_submit_button("Добавить и переиндексировать")

    if submitted:
        aliases = [normalize_name(part) for part in aliases_text.split(",") if normalize_name(part)]
        canonical = normalize_name(canonical_name)
        if not canonical:
            st.error("Укажите каноническое имя.")
            st.stop()
        lemma_key = to_lemma_key(canonical)
        record = EntityRecord(
            entity_type=entity_type,
            canonical_name=canonical,
            registry_source=registry_source.strip(),
            registry_id=registry_id.strip(),
            included_at=None,
            aliases=aliases or [canonical],
            lemma_key=lemma_key,
        )
        with db_connection() as conn:
            ensure_entity_aliases_supports_manual(conn)
            created = upsert_entity(conn, record)
            stats = reindex_mentions_from_extracted_spans(conn, settings)
            conn.commit()
        st.success(
            f"Запись {'создана' if created else 'обновлена'}. "
            f"Переиндекс за **{stats.elapsed_ms} ms**: spans={stats.spans_processed}, "
            f"mentions={stats.mentions_written}, документов (по spans): {stats.documents_touched}."
        )
