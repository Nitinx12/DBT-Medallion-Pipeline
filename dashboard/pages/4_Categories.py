"""Categories page — category and status breakdown."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.helpers.components import dataframe_with_download
from dashboard.helpers.theme import inject_css
from dashboard.lib.charts import bar_by, donut
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import get_revenue_by

st.set_page_config(page_title="Categories", page_icon="🏷️", layout="wide")
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Categories")

filters, _ = sidebar_filters(key_prefix="cat_")
by_category = get_revenue_by(filters, "category")
by_status = get_revenue_by(filters, "order_status")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Revenue by Category")
    if not by_category.empty:
        st.plotly_chart(
            donut(by_category, "category"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        dataframe_with_download(
            by_category, "revenue_by_category.csv", key="dl_cat_tbl"
        )
with c2:
    st.subheader("Revenue by Order Status")
    if not by_status.empty:
        xcol = "status" if "status" in by_status.columns else by_status.columns[0]
        st.plotly_chart(
            bar_by(by_status, xcol),
            use_container_width=True,
            config={"displayModeBar": False},
        )
