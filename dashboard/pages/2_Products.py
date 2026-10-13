"""Products page — top products, brands, category treemap."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from dashboard.helpers.components import dataframe_with_download
from dashboard.helpers.theme import WALMART_BLUE, inject_css, style
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_category_brand_treemap,
    get_revenue_by,
    get_top_products,
)

st.set_page_config(page_title="Products", page_icon="📦", layout="wide")
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Products")

filters, _ = sidebar_filters(key_prefix="prod_")
top_products = get_top_products(filters, limit=10)
by_brand = get_revenue_by(filters, "brand", limit=10)
treemap_data = get_category_brand_treemap(filters)

st.subheader("Top 10 Products")
dataframe_with_download(top_products, "top_products.csv", key="dl_prod_top")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Top 10 Brands")
    if not by_brand.empty:
        fig = px.bar(
            by_brand,
            x="revenue",
            y="brand",
            orientation="h",
            labels={"brand": "", "revenue": "Revenue"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        fig.update_traces(
            marker_color=WALMART_BLUE, hovertemplate="%{y}: $%{x:,.0f}<extra></extra>"
        )
        st.plotly_chart(
            style(fig, height=420),
            use_container_width=True,
            config={"displayModeBar": False},
        )
with c2:
    st.subheader("Category → Brand")
    if not treemap_data.empty:
        fig = px.treemap(
            treemap_data, path=["category_name", "brand_name"], values="revenue"
        )
        st.plotly_chart(
            style(fig, currency=False, legend=False, height=420),
            use_container_width=True,
            config={"displayModeBar": False},
        )
