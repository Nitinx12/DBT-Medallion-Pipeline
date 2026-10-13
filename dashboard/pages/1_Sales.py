"""Sales page — revenue trend and store mix."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.helpers import plotly_template
from dashboard.helpers.components import dataframe_with_download
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.charts import bar_by, donut, revenue_trend_chart
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import get_revenue_by, get_revenue_trend

st.set_page_config(page_title="Sales", page_icon="📊", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Sales")

filters, meta = sidebar_filters(key_prefix="sales_")
granularity = st.radio(
    "Trend granularity", ["Day", "Week", "Month"], index=1, horizontal=True
).lower()

trend = get_revenue_trend(filters, granularity)
by_store = get_revenue_by(filters, "store")
by_payment = get_revenue_by(filters, "payment_method")

st.plotly_chart(
    revenue_trend_chart(trend, granularity),
    use_container_width=True,
    config={"displayModeBar": False},
)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Revenue by Store")
    if not by_store.empty:
        st.plotly_chart(
            bar_by(by_store, "store"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        dataframe_with_download(by_store, "revenue_by_store.csv", key="dl_sales_store")
with c2:
    st.subheader("Revenue by Payment")
    if not by_payment.empty:
        st.plotly_chart(
            donut(by_payment, "payment_method"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
