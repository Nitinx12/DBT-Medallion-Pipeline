"""Data Health page — freshness, row counts, pipeline runs."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.lib.db import apply_secrets

# Secrets first: pages after this read config at import time.
apply_secrets()

from dashboard.helpers import plotly_template
from dashboard.helpers.components import (
    dataframe_with_download,
    empty_state,
    filter_chips,
    freshness_badge,
)
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_freshness,
    get_pipeline_status,
    get_table_counts,
)

st.set_page_config(page_title="Data Health", page_icon="💚", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Data Health")

filters, _ = sidebar_filters()
filter_chips(filters)

st.subheader("Freshness")
freshness_badge(get_freshness()["last_order_ts"])
st.caption("Green under 15 minutes, amber under 2 hours, red beyond that.")

st.subheader("Gold tables")
counts = get_table_counts()
if not counts.empty:
    st.metric("Total gold rows", f"{int(counts['row_count'].sum()):,}")
    dataframe_with_download(counts, "gold_row_counts.csv", key="dl_health_counts")
else:
    empty_state("No gold tables found.", "Check POSTGRES_SCHEMA_GOLD in .env.")

st.subheader("Pipeline runs")
runs = get_pipeline_status()
if not runs.empty:
    dataframe_with_download(runs, "pipeline_runs.csv", key="dl_health_runs")
else:
    empty_state(
        "No extract history found.",
        "etl_logs/etl_watermarks only exist after extract.py runs.",
    )
