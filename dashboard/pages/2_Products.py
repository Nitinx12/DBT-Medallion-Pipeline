"""Products page — top products, brands, category treemap."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from dashboard.helpers import plotly_template
from dashboard.helpers.components import dataframe_with_download, filter_chips
from dashboard.helpers.theme import WALMART_BLUE, get_theme, inject_css, style
from dashboard.lib.charts import bubble, pareto, treemap
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_category_brand_treemap,
    get_product_revenue,
    get_revenue_by,
    get_top_products,
)

st.set_page_config(page_title="Products", page_icon="📦", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)
st.title("Products")

filters, _ = sidebar_filters()
filter_chips(filters)
top_products = get_top_products(filters, limit=10)
by_brand = get_revenue_by(filters, "brand", limit=10)
treemap_data = get_category_brand_treemap(filters)

st.subheader("Top 10 Products")
bars = None
if not top_products.empty:
    bars = {
        "revenue": st.column_config.ProgressColumn(
            "Revenue",
            format="$%d",
            min_value=0,
            max_value=int(top_products["revenue"].max()),
        ),
        "units_sold": st.column_config.ProgressColumn(
            "Units",
            format="%d",
            min_value=0,
            max_value=int(top_products["units_sold"].max()),
        ),
    }
dataframe_with_download(
    top_products, "top_products.csv", key="dl_prod_top", column_config=bars
)

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
        st.plotly_chart(
            treemap(treemap_data),
            use_container_width=True,
            config={"displayModeBar": False},
        )

st.subheader("Pareto: revenue concentration")
product_revenue = get_product_revenue(filters)
if not product_revenue.empty:
    pareto_fig, n80 = pareto(product_revenue)
    st.plotly_chart(
        pareto_fig, use_container_width=True, config={"displayModeBar": False}
    )
    st.caption(f"{n80} of {len(product_revenue)} products drive 80% of revenue.")

st.subheader("Portfolio: volume vs value")
portfolio = get_top_products(filters, limit=30)
if not portfolio.empty:
    st.plotly_chart(
        bubble(portfolio), use_container_width=True, config={"displayModeBar": False}
    )
