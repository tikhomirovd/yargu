from __future__ import annotations

import sqlite3

import streamlit as st

from yargumark.config import Settings, get_settings
from yargumark.db import get_connection


def app_settings() -> Settings:
    return get_settings()


def db_connection() -> sqlite3.Connection:
    settings = app_settings()
    return get_connection(settings.db_path)


def current_ui_mode() -> str:
    if "ui_mode" not in st.session_state:
        st.session_state["ui_mode"] = app_settings().mode.strip().lower()
    return str(st.session_state["ui_mode"])
