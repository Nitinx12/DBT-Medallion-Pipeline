"""Walmart Gold Dashboard — home."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.lib.db import apply_secrets

# Secrets first: pages after this read config at import time.
apply_secrets()

from dashboard.helpers import plotly_template
from dashboard.helpers.components import filter_chips, footer, kpi_cards
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import get_gold_meta, get_kpis

st.set_page_config(page_title="Walmart — Home", page_icon="🛒", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)

st.title("Walmart Gold Dashboard")
st.caption("Use the sidebar pages: Sales, Products, Customers, Categories.")

try:
    filters, meta = sidebar_filters()
    filter_chips(filters)
    gold = get_gold_meta()
    current = get_kpis(filters)
    previous = get_kpis(filters.previous_period())

    def _pct(curr: float, prev: float) -> float | None:
        return (curr - prev) / prev * 100 if prev else None

    kpi_cards(
        current["revenue"],
        current["orders"],
        current["customers"],
        current["aov"],
        {
            "revenue": _pct(current["revenue"], previous["revenue"]),
            "orders": _pct(float(current["orders"]), float(previous["orders"])),
            "customers": _pct(
                float(current["customers"]), float(previous["customers"])
            ),
            "aov": _pct(current["aov"], previous["aov"]),
        },
    )
    st.info(
        f"Gold fact rows: {gold.get('fact_rows', 0):,} · Last order: {gold.get('last_order_ts') or '—'}"
    )
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not connect to Postgres: {exc}")
    st.stop()

footer()
