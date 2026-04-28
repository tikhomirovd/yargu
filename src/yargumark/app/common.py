from __future__ import annotations

import sqlite3

import streamlit as st

from yargumark.config import Settings, get_settings
from yargumark.db import get_connection

_YM_STYLES_MARKDOWN = """
<style>
  .ym-article {
    font-size: 1rem;
    line-height: 1.55;
    color: inherit;
  }
  .ym-mark {
    background: rgba(255, 193, 7, 0.22);
    padding: 0 2px;
    border-radius: 2px;
  }
  .ym-badge {
    font-size: 0.82em;
    font-weight: 600;
    margin-left: 2px;
    white-space: nowrap;
  }
  .ym-foreign_agent { color: #b45309; }
  .ym-undesirable_org { color: #1d4ed8; }
  .ym-terrorist_extremist { color: #b91c1c; }
  .ym-banned_by_court { color: #6b21a8; }
  .ym-unknown { color: #4b5563; }
  .ym-footnotes {
    margin-top: 1.25rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(128, 128, 128, 0.35);
    font-size: 0.9rem;
    opacity: 0.95;
  }
</style>
"""


def inject_global_styles() -> None:
    st.markdown(_YM_STYLES_MARKDOWN, unsafe_allow_html=True)


def app_settings() -> Settings:
    return get_settings()


def db_connection() -> sqlite3.Connection:
    settings = app_settings()
    return get_connection(settings.db_path)


def current_ui_mode() -> str:
    if "ui_mode" not in st.session_state:
        st.session_state["ui_mode"] = app_settings().mode.strip().lower()
    return str(st.session_state["ui_mode"])
