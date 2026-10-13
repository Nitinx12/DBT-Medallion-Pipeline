"""Sales page — revenue trend and store mix."""

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
from dashboard.helpers.components import dataframe_with_download, filter_chips
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.charts import (
    bar_by,
    donut,
    dow_hour_heatmap,
    revenue_trend_chart,
    waterfall,
)
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_category_monthly_revenue,
    get_dow_hour_revenue,
    get_revenue_by,
    get_revenue_trend,
)

st.set_page_config(page_title="Sales", page_icon="📊", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Sales")

filters, meta = sidebar_filters()
filter_chips(filters)
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

st.subheader("When do shoppers buy")
dow_hour = get_dow_hour_revenue(filters)
if not dow_hour.empty:
    st.plotly_chart(
        dow_hour_heatmap(dow_hour),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.subheader("What moved month over month")
cat_monthly = get_category_monthly_revenue(filters)
months = sorted(cat_monthly["month"].unique()) if not cat_monthly.empty else []
if len(months) >= 2:
    last, prev = months[-1], months[-2]
    cur = cat_monthly[cat_monthly["month"] == last].set_index("category_name")[
        "revenue"
    ]
    old = cat_monthly[cat_monthly["month"] == prev].set_index("category_name")[
        "revenue"
    ]
    delta = cur.sub(old, fill_value=0.0).reset_index()
    delta.columns = ["category_name", "delta"]
    delta = delta.sort_values("delta", ascending=False)
    st.plotly_chart(
        waterfall(delta), use_container_width=True, config={"displayModeBar": False}
    )
    st.caption(f"Category change from {prev:%b %Y} to {last:%b %Y}.")
else:
    st.caption("Pick a window spanning two months to see movement.")
