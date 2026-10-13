"""Categories page — sunburst, funnel, share over time."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.helpers import plotly_template
from dashboard.helpers.components import dataframe_with_download, filter_chips
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.charts import bar_by, donut, funnel, share_area, sunburst
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_category_monthly_revenue,
    get_revenue_by,
    get_status_funnel,
    get_sunburst_revenue,
)

st.set_page_config(page_title="Categories", page_icon="🏷️", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Categories")

filters, _ = sidebar_filters()
filter_chips(filters)
by_category = get_revenue_by(filters, "category")
by_status = get_revenue_by(filters, "order_status")

st.subheader("Category → Brand → Product")
sunburst_data = get_sunburst_revenue(filters)
if not sunburst_data.empty:
    st.plotly_chart(
        sunburst(sunburst_data),
        use_container_width=True,
        config={"displayModeBar": False},
    )

c1, c2 = st.columns(2)
with c1:
    st.subheader("Order status funnel")
    funnel_data = get_status_funnel(filters)
    if not funnel_data.empty:
        st.plotly_chart(
            funnel(funnel_data),
            use_container_width=True,
            config={"displayModeBar": False},
        )
with c2:
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

st.subheader("Category share over time")
share_data = get_category_monthly_revenue(filters)
if not share_data.empty:
    st.plotly_chart(
        share_area(share_data),
        use_container_width=True,
        config={"displayModeBar": False},
    )

if not by_status.empty:
    st.subheader("Revenue by Order Status")
    xcol = "status" if "status" in by_status.columns else by_status.columns[0]
    st.plotly_chart(
        bar_by(by_status, xcol),
        use_container_width=True,
        config={"displayModeBar": False},
    )
