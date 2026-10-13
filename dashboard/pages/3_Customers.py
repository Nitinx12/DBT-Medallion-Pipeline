"""Customers page — RFM segments, cohorts, top customers, recent orders."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from dashboard.helpers import plotly_template
from dashboard.helpers.components import dataframe_with_download, filter_chips
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.charts import cohort_heatmap, rfm_scatter
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_cohort_activity,
    get_recent_order_lines,
    get_rfm_segments,
    get_top_customers,
)

st.set_page_config(page_title="Customers", page_icon="🧑‍🤝‍🧑", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Customers")

filters, _ = sidebar_filters()
filter_chips(filters)

st.subheader("RFM segments")
rfm = get_rfm_segments(filters)
if not rfm.empty:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(
            rfm_scatter(rfm), use_container_width=True, config={"displayModeBar": False}
        )
    with c2:
        summary = (
            rfm.groupby("segment")
            .agg(customers=("customer_id", "nunique"), revenue=("monetary", "sum"))
            .reset_index()
            .sort_values("revenue", ascending=False)
        )
        dataframe_with_download(summary, "rfm_segments.csv", key="dl_cust_rfm")
    st.caption("Recency, frequency, and spend each split into quintiles.")

st.subheader("Cohort retention")
cohort = get_cohort_activity(filters)
if not cohort.empty:
    act = cohort.copy()
    act["cohort_month"] = pd.to_datetime(act["cohort_month"])
    act["activity_month"] = pd.to_datetime(act["activity_month"])
    act["cohort"] = act["cohort_month"].dt.strftime("%Y-%m")
    act["offset"] = (
        (act["activity_month"].dt.year - act["cohort_month"].dt.year) * 12
        + act["activity_month"].dt.month
        - act["cohort_month"].dt.month
    )
    size = act[act["offset"] == 0].set_index("cohort")["customers"]
    pivot = (
        act.pivot(index="cohort", columns="offset", values="customers")
        .div(size, axis=0)
        .fillna(0.0)
    )
    st.plotly_chart(
        cohort_heatmap(pivot),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.caption(
        "Share of each cohort still ordering N months after its first order in view."
    )

st.subheader("Top 10 Customers")
top_customers = get_top_customers(filters, limit=10)
dataframe_with_download(top_customers, "top_customers.csv", key="dl_cust_top")

st.subheader("Recent order lines (200)")
recent = get_recent_order_lines(filters, limit=200)
search = st.text_input(
    "Search", placeholder="Filter by product, customer, store, brand…"
)
view = recent
if search and not recent.empty:
    mask = False
    q = search.lower()
    for col in recent.columns:
        mask = mask | recent[col].astype(str).str.lower().str.contains(q, na=False)
    view = recent[mask]
dataframe_with_download(view, "recent_orders.csv", key="dl_cust_recent")
