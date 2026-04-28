from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import streamlit as st

st.set_page_config(page_title="Fixtures", layout="wide")
st.title("Демо-фикстуры")

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

st.caption(f"Загружено **{len(fixtures)}** фикстур, ожиданий: **{len(expected)}**.")

for item in fixtures:
    with st.expander(item.get("title", "Без названия")):
        st.write(item.get("body", ""))
