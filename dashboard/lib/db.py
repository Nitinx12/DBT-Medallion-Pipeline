"""Shared Postgres connection for dashboard pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st


def apply_secrets() -> None:
    try:
        for key, value in st.secrets.items():
            os.environ.setdefault(key, str(value))
    except Exception:  # noqa: BLE001, S110
        pass


def get_engine():
    apply_secrets()
    from utils.connection import get_postgres_engine

    return get_postgres_engine()
