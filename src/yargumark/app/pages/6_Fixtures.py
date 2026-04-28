from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import streamlit as st

from yargumark.app.common import app_settings, current_ui_mode, db_connection, inject_global_styles
from yargumark.benchmark.fixtures_metrics import precision_recall_surfaces
from yargumark.config import ui_threshold
from yargumark.db import fetch_mention_surfaces, get_document_id_by_url
from yargumark.marker.render import render_document_html

st.set_page_config(page_title="Fixtures", layout="wide")
inject_global_styles()
st.title("Качество (тестовые кейсы)")
st.markdown(
    "**Зачем эта страница:** заранее подготовленные тексты с **эталоном** (ground truth) — чтобы считать "
    "precision/recall и показать на слайде, как система ведёт себя на **намеренно сложных** формулировках.\n\n"
    "**Когда показывать:** после основного сценария, если аудитория спрашивает про метрики или нужен контролируемый "
    "набор примеров.\n\n"
    "Реальные страницы с найденными упоминаниями удобнее смотреть в **Просмотр документа**."
)

root = Path(__file__).resolve().parents[4]
fixtures_path = root / "demo" / "fixtures.json"
expected_path = root / "demo" / "fixtures_expected.json"

if not fixtures_path.exists():
    st.warning("Файл demo/fixtures.json не найден.")
    st.stop()

fixtures_raw = json.loads(fixtures_path.read_text(encoding="utf-8"))
if not isinstance(fixtures_raw, list):
    st.error("Некорректный формат fixtures.json")
    st.stop()
fixtures: list[dict[str, Any]] = []
for row in cast(Sequence[object], fixtures_raw):
    if isinstance(row, dict):
        fixtures.append(cast(dict[str, Any], row))
expected: list[dict[str, Any]] = []
if expected_path.exists():
    loaded = json.loads(expected_path.read_text(encoding="utf-8"))
    if isinstance(loaded, list):
        for row in cast(Sequence[object], loaded):
            if isinstance(row, dict):
                expected.append(cast(dict[str, Any], row))

settings = app_settings()
mode = current_ui_mode()
threshold_demo = ui_threshold(settings, "demo")
threshold_prod = ui_threshold(settings, "production")

expected_by_url: dict[str, list[str]] = {}
for row in expected:
    url_key = str(row["url"])
    raw = row.get("expected_mention_surfaces", [])
    if isinstance(raw, list):
        surfaces = [str(el) for el in cast(list[object], raw)]
        expected_by_url[url_key] = surfaces

st.caption(f"Загружено **{len(fixtures)}** фикстур, ожиданий: **{len(expected)}**.")
st.info(
    "Чтобы появилась колонка «Разметка» и метрики: `uv run python scripts/seed_demo.py`, "
    "затем для каждого `doc_id` вызовите `uv run yargumark-process-doc --doc-id …` "
    "(или прогоните свой батч-скрипт)."
)

for item in fixtures:
    url = str(item["url"])
    title = str(item.get("title", "Без названия"))
    body = str(item.get("body", ""))
    exp_surfaces = expected_by_url.get(url, [])
    with st.expander(title):
        left, right = st.columns(2)
        with left:
            st.subheader("Исходный текст")
            st.text(body)
        with right:
            st.subheader("Результат в базе (плашки)")
            with db_connection() as conn:
                doc_id = get_document_id_by_url(conn, url)
                if doc_id is None:
                    st.caption("Нет строки в `documents` для этого url.")
                    demo_actual: list[str] = []
                    prod_actual: list[str] = []
                else:
                    st.caption(f"doc_id={doc_id}, режим UI: **{mode}**")
                    marked_html = render_document_html(
                        conn,
                        doc_id,
                        mode,
                        settings=settings,
                    )
                    st.markdown(marked_html, unsafe_allow_html=True)
                    demo_actual = fetch_mention_surfaces(conn, doc_id, threshold_demo)
                    prod_actual = fetch_mention_surfaces(conn, doc_id, threshold_prod)
        pr_demo = precision_recall_surfaces(exp_surfaces, demo_actual)
        pr_prod = precision_recall_surfaces(exp_surfaces, prod_actual)
        st.markdown(
            "**Сводка (поверхности):** "
            f"ожидаемые `{exp_surfaces}` · demo actual `{demo_actual}` "
            f"(P={pr_demo.precision:.2f}, R={pr_demo.recall:.2f}) · "
            f"production actual `{prod_actual}` "
            f"(P={pr_prod.precision:.2f}, R={pr_prod.recall:.2f})"
        )
