"""Customers page — top customers and recent orders."""

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
from dashboard.helpers.components import dataframe_with_download
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import get_recent_order_lines, get_top_customers

st.set_page_config(page_title="Customers", page_icon="🧑‍🤝‍🧑", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Customers")

filters, _ = sidebar_filters(key_prefix="cust_")
top_customers = get_top_customers(filters, limit=10)
recent = get_recent_order_lines(filters, limit=200)

st.subheader("Top 10 Customers")
dataframe_with_download(top_customers, "top_customers.csv", key="dl_cust_top")

st.subheader("Recent order lines (200)")
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
