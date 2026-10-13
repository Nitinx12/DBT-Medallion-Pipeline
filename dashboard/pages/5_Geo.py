"""Geo page — store map with click to filter plus region leaderboard."""

from __future__ import annotations

import sys
from dataclasses import replace
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
)
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.charts import bar_by, store_map
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.geo import store_coordinates
from dashboard.lib.queries import get_revenue_by, get_store_revenue

st.set_page_config(page_title="Geo", page_icon="🗺️", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Geo")

filters, _ = sidebar_filters()
filter_chips(filters)

current = get_store_revenue(filters)
previous = get_store_revenue(filters.previous_period())
merged = current.merge(store_coordinates(), on="store_id", how="left")
prev_rev = previous[["store_id", "revenue"]].rename(columns={"revenue": "prev_revenue"})
merged = merged.merge(prev_rev, on="store_id", how="left").fillna({"prev_revenue": 0.0})
merged["growth_pct"] = merged.apply(
    lambda r: (
        (r["revenue"] - r["prev_revenue"]) / r["prev_revenue"] * 100
        if r["prev_revenue"]
        else 0.0
    ),
    axis=1,
)

st.subheader("Store revenue map")
st.caption(
    "Click one or more bubbles to filter this page. "
    "Positions are province representative points: demo geography, not addresses."
)
if not merged.empty:
    map_key = st.session_state.get("map_key", 0)
    event = st.plotly_chart(
        store_map(merged),
        key=f"store_map_{map_key}",
        on_select="rerun",
        selection_mode="points",
        use_container_width=True,
        config={"displayModeBar": False},
    )
    names: set[str] = set()
    if event is not None:
        points = (getattr(event, "selection", None) or {}).get("points", []) or []
        names = {
            p.get("hovertext")
            for p in points
            if isinstance(p, dict) and p.get("hovertext")
        }
    valid = tuple(sorted(n for n in names if n in set(filters.stores)))
    col_clear, col_note = st.columns([1, 4])
    with col_clear:
        if st.button("Clear selection", key="geo_clear"):
            st.session_state["map_key"] = map_key + 1
            st.rerun()
    with col_note:
        if valid:
            st.caption(f"Map selection: {', '.join(valid)}.")
    shown = replace(filters, stores=valid) if valid else filters
else:
    empty_state("No stores in view.", "Widen the date range or clear a filter.")
    shown = filters

st.subheader("Region leaderboard")
by_province = get_revenue_by(shown, "province")
if not by_province.empty:
    st.plotly_chart(
        bar_by(by_province, "province"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.subheader("Stores")
store_table = get_store_revenue(shown)
if not store_table.empty:
    dataframe_with_download(store_table, "store_revenue.csv", key="dl_geo_stores")
