"""
Walmart Sales Dashboard — Streamlit + Plotly, backed by the Postgres
`gold` star schema.

Run:
    uv run streamlit run dashboard/app.py

Design:
- All SQL lives in queries.py (parameterized, aggregated in Postgres).
- Styling lives in theme.py (one design system).
- Reusable cards/chips in components.py.
- This file only orchestrates layout, state, and rendering.
"""

from __future__ import annotations

import html
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:  # noqa: BLE001, S110
    pass

from dashboard.components import (
    dataframe_with_download,
    empty_state,
    filter_chips,
    footer,
    kpi_cards,
)
from dashboard.queries import (
    Filters,
    get_category_brand_treemap,
    get_filter_options,
    get_gold_meta,
    get_kpis,
    get_recent_order_lines,
    get_revenue_by,
    get_revenue_trend,
    get_top_customers,
    get_top_products,
)
from dashboard.theme import (
    PALETTE,
    SEMANTIC,
    WALMART_BLUE,
    inject_css,
    style,
)
from utils.logger import get_logger

log = get_logger("dashboard", console_level="WARNING")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Walmart Sales — Gold Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/anomalyco/walmart",
        "Report a bug": "https://github.com/anomalyco/walmart/issues",
        "About": "Walmart Medallion Pipeline — gold star schema dashboard (Streamlit + Plotly).",
    },
)
st.markdown(inject_css(), unsafe_allow_html=True)

WALMART_BLUE_E = html.escape(WALMART_BLUE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_currency(v: float) -> str:
    return f"${v:,.0f}"


def _delta_pct(curr: float, prev: float) -> float | None:
    if not prev:
        return None
    return (curr - prev) / prev * 100


def _hover_currency(fig: go.Figure) -> go.Figure:
    fig.update_traces(
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>"
        if any(hasattr(t, "labels") for t in fig.data)
        else "Revenue: $%{y:,.0f}<br>%{x}<extra></extra>"
    )  # type: ignore[arg-type]
    return fig


# ---------------------------------------------------------------------------
# Load filter options + meta (cached)
# ---------------------------------------------------------------------------
try:
    with st.spinner("Connecting to gold schema…"):
        options = get_filter_options()
        try:
            meta = get_gold_meta()
        except Exception:  # noqa: BLE001 — meta is optional; dashboard still usable without it
            meta = {"fact_rows": 0, "last_order_ts": None}
except Exception as exc:
    log.exception("Failed to load filter options from gold schema")
    st.markdown(
        f"""
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:14px;padding:18px 20px;">
            <div style="font-weight:700;color:#991B1B;margin-bottom:6px;">Could not connect to Postgres</div>
            <div style="font-size:0.86rem;color:#7F1D1D;word-break:break-all;">{html.escape(str(exc))}</div>
            <div style="font-size:0.78rem;color:#991B1B;margin-top:10px;">Check <code>.env</code> (POSTGRES_*) and that the pipeline has created the <code>gold</code> schema.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

if not options["stores"]:
    st.markdown(
        """
        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:14px;padding:18px 20px;">
            <div style="font-weight:700;color:#92400E;">No active stores in gold yet</div>
            <div style="font-size:0.86rem;color:#78350F;margin-top:6px;">Run the pipeline once to populate <code>gold.dim_stores</code> and <code>gold.fact_order_items</code>.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

min_date: date = options["min_date"]
max_date: date = options["max_date"]

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
with st.sidebar:
    # Brand lockup
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin:4px 0 14px 0;">
            <div style="width:38px;height:38px;border-radius:10px;background:{WALMART_BLUE};display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:1.15rem;box-shadow:0 4px 10px rgba(0,113,206,0.35);">W</div>
            <div>
                <div style="font-weight:800;letter-spacing:-0.02em;line-height:1;color:{SEMANTIC["text"]}">Walmart</div>
                <div style="font-size:0.70rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{SEMANTIC["text_faint"]}">Gold Dashboard</div>
            </div>
            <div style="margin-left:auto;font-size:0.68rem;font-weight:700;color:{SEMANTIC["text_faint"]};background:{SEMANTIC["surface_alt"]};border:1px solid {SEMANTIC["border"]};padding:3px 7px;border-radius:999px;">LIVE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick presets — set session_state for the date_input on next rerun
    st.markdown("**Date presets**")
    c1, c2, c3 = st.columns(3)
    if c1.button("7D", use_container_width=True, key="preset_7d"):
        st.session_state["_date_range"] = (max_date - timedelta(days=6), max_date)
    if c2.button("30D", use_container_width=True, key="preset_30d"):
        st.session_state["_date_range"] = (max_date - timedelta(days=29), max_date)
    if c3.button("90D", use_container_width=True, key="preset_90d"):
        st.session_state["_date_range"] = (max_date - timedelta(days=89), max_date)
    c4, c5 = st.columns(2)
    if c4.button("YTD", use_container_width=True, key="preset_ytd"):
        st.session_state["_date_range"] = (date(max_date.year, 1, 1), max_date)
    if c5.button("All time", use_container_width=True, key="preset_all"):
        st.session_state["_date_range"] = (min_date, max_date)

    default_range: tuple[date, date] = st.session_state.get(
        "_date_range", (min_date, max_date)
    )
    # clamp preset if data changed
    default_range = (max(min_date, default_range[0]), min(max_date, default_range[1]))

    selected_range = st.date_input(
        "Order date range",
        value=default_range,
        min_value=min_date,
        max_value=max_date,
        key="date_range_input",
        help="Inclusive on both ends in the UI; converted to [start, end) for SQL.",
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date_inclusive = selected_range
    else:
        start_date, end_date_inclusive = default_range

    # Guard: if user picks reversed range (can happen with presets), normalize
    if start_date > end_date_inclusive:
        start_date, end_date_inclusive = end_date_inclusive, start_date

    st.markdown("---")
    st.markdown("**Scope**")

    # Store search-friendly multiselects with Select-all affordance
    selected_stores = st.multiselect(
        "Store(s)",
        options["stores"],
        default=options["stores"],
        placeholder="Choose stores…",
        key="stores_ms",
    )
    s_col1, s_col2 = st.columns(2)
    if s_col1.button("All stores", use_container_width=True, key="all_stores"):
        st.session_state["stores_ms"] = options["stores"]
        st.rerun()
    if s_col2.button("Clear", use_container_width=True, key="clear_stores"):
        st.session_state["stores_ms"] = []
        st.rerun()

    selected_categories = st.multiselect(
        "Categor(y/ies)",
        options["categories"],
        default=options["categories"],
        placeholder="Choose categories…",
        key="cats_ms",
    )
    selected_statuses = st.multiselect(
        "Order status",
        options["statuses"],
        default=options["statuses"],
        placeholder="Choose statuses…",
        key="status_ms",
    )

    st.markdown("---")
    granularity_label = st.radio(
        "Trend granularity",
        ["Day", "Week", "Month"],
        index=1,
        horizontal=True,
        key="granularity",
    )
    granularity = granularity_label.lower()

    st.markdown("---")
    if st.button("↺ Clear all filters", use_container_width=True, key="clear_all"):
        for k in ("_date_range", "stores_ms", "cats_ms", "status_ms", "granularity"):
            st.session_state.pop(k, None)
        st.rerun()

    with st.expander("About this data", expanded=False):
        st.caption(
            f"Gold schema: `{getattr(__import__('utils.engine', fromlist=['POSTGRES_SCHEMA_GOLD']), 'POSTGRES_SCHEMA_GOLD', 'gold')}`  \n"
            f"Fact rows (active): **{meta.get('fact_rows', 0):,}**  \n"
            f"Last order: **{meta.get('last_order_ts') or '—'}**  \n\n"
            "Filters use `is_active = true` on both fact and order dims. "
            "All aggregations run in Postgres."
        )

# Build immutable filter key (hashable for cache)
filters = Filters(
    start_date=start_date,
    end_date=end_date_inclusive + timedelta(days=1),  # inclusive UI -> exclusive SQL
    stores=tuple(selected_stores),
    categories=tuple(selected_categories),
    statuses=tuple(selected_statuses),
)

# ---------------------------------------------------------------------------
# Top header
# ---------------------------------------------------------------------------
last_ts = meta.get("last_order_ts")
last_ts_str = (
    pd.Timestamp(last_ts).strftime("%b %d, %Y %H:%M")
    if last_ts is not None and str(last_ts) != "NaT"
    else "—"
)

hdr_left, hdr_right = st.columns([3, 1.35])
with hdr_left:
    st.markdown(
        f"""
        <div style="margin:2px 0 4px 0;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <h1 style="margin:0;font-size:1.85rem;font-weight:800;letter-spacing:-0.03em;color:{SEMANTIC["text"]};line-height:1;">Sales Overview</h1>
                <span style="font-size:0.70rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;background:{WALMART_BLUE};color:white;padding:4px 9px;border-radius:999px;">GOLD</span>
                <span style="font-size:0.70rem;font-weight:600;color:{SEMANTIC["text_muted"]};background:{SEMANTIC["surface"]};border:1px solid {SEMANTIC["border"]};padding:4px 9px;border-radius:999px;">Postgres · live</span>
            </div>
            <div style="margin-top:6px;font-size:0.84rem;color:{SEMANTIC["text_muted"]};display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
                <span>📅 {start_date:%b %d, %Y} – {end_date_inclusive:%b %d, %Y}</span>
                <span style="opacity:0.35;">·</span>
                <span>Updated {html.escape(last_ts_str)} · {meta.get("fact_rows", 0):,} active fact rows</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hdr_right:
    r1, r2 = st.columns(2)
    if r1.button(
        "↻ Refresh",
        use_container_width=True,
        key="refresh_btn",
        help="Clear Streamlit cache and reload from Postgres",
    ):
        st.cache_data.clear()
        st.rerun()
    # Download current filtered trend as CSV (quick export)
    # We defer actual CSV until after data loads; placeholder button just scrolls to tabs where per-chart downloads live.
    r2.link_button(
        "Docs ↗",
        "https://github.com/anomalyco/walmart/blob/main/dashboard/README.md",
        use_container_width=True,
    )

filter_chips(filters)

# ---------------------------------------------------------------------------
# KPIs + deltas
# ---------------------------------------------------------------------------
try:
    with st.spinner("Loading KPIs…"):
        current = get_kpis(filters)
        previous = get_kpis(filters.previous_period())
except Exception as exc:
    log.exception("get_kpis failed")
    st.error(f"Failed to load KPIs: {exc}")
    st.stop()

if current["orders"] == 0:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.info(
        "No order lines match the current filters. Try widening the date range or choosing more stores/categories."
    )
    st.stop()

deltas = {
    "revenue": _delta_pct(current["revenue"], previous["revenue"]),
    "orders": _delta_pct(float(current["orders"]), float(previous["orders"])),
    "customers": _delta_pct(float(current["customers"]), float(previous["customers"])),
    "aov": _delta_pct(current["aov"], previous["aov"]),
}

kpi_cards(
    current["revenue"], current["orders"], current["customers"], current["aov"], deltas
)

# ---------------------------------------------------------------------------
# Data loads (outside tabs so all tabs share same queries without re-fetch)
# ---------------------------------------------------------------------------
try:
    with st.spinner("Loading charts…"):
        trend = get_revenue_trend(filters, granularity)
        by_store = get_revenue_by(filters, "store")
        by_category = get_revenue_by(filters, "category")
        by_brand = get_revenue_by(filters, "brand", limit=10)
        by_payment = get_revenue_by(filters, "payment_method")
        by_status = get_revenue_by(filters, "order_status")
        treemap_data = get_category_brand_treemap(filters)
        top_products = get_top_products(filters, limit=10)
        top_customers = get_top_customers(filters, limit=10)
        recent = get_recent_order_lines(filters, limit=200)
except Exception as exc:
    log.exception("Chart data load failed")
    st.error(f"Failed to load chart data: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs — professional information architecture
# ---------------------------------------------------------------------------
tab_overview, tab_trends, tab_breakdown, tab_data = st.tabs(
    ["📊 Overview", "📈 Trends & Mix", "🧩 Breakdown", "📋 Data"]
)

# ============ OVERVIEW TAB ============
with tab_overview:
    # Revenue trend
    st.markdown(
        f"""
        <div class="section-head"><h3>Revenue Trend</h3><p>Aggregated in Postgres via <code>date_trunc('{html.escape(granularity)}', order_timestamp)</code></p></div>
        """,
        unsafe_allow_html=True,
    )
    if trend.empty:
        empty_state(
            "No trend data for the current filters.",
            "Try a broader date range or a coarser granularity.",
        )
    else:
        # Clean labels
        trend_plot = trend.copy()
        trend_plot["period"] = pd.to_datetime(trend_plot["period"])
        fig_trend = px.area(
            trend_plot,
            x="period",
            y="revenue",
            labels={"period": "", "revenue": "Revenue"},
        )
        fig_trend.update_traces(
            line={"color": WALMART_BLUE, "width": 2.6},
            fillcolor="rgba(0,113,206,0.12)",
            hovertemplate="Revenue: $%{y:,.0f}<br>%{x|%b %d, %Y}<extra></extra>",
        )
        fig_trend.update_xaxes(
            tickformat="%b %d" if granularity == "day" else "%b %d, %Y"
        )
        with st.container(border=False):
            st.markdown('<div class="dash-card">', unsafe_allow_html=True)
            st.plotly_chart(
                style(fig_trend, height=360),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            # Inline CSV
            if not trend_plot.empty:
                csv = trend_plot.to_csv(index=False).encode()
                st.download_button(
                    "⬇ Download trend CSV",
                    data=csv,
                    file_name=f"revenue_trend_{granularity}_{start_date}_{end_date_inclusive}.csv",
                    mime="text/csv",
                    key="dl_trend",
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # Store + Category side-by-side
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Revenue by Store</div><p class="dash-card__subtitle">Share of filtered revenue across active stores</p><div class="dash-card__accent"></div>',
            unsafe_allow_html=True,
        )
        if by_store.empty:
            empty_state("No store breakdown.", "")
        else:
            fig_store = px.bar(
                by_store,
                x="store",
                y="revenue",
                color="revenue",
                color_continuous_scale=["#DBEAFE", WALMART_BLUE],
                labels={"store": "", "revenue": "Revenue"},
            )
            fig_store.update_layout(coloraxis_showscale=False)
            fig_store.update_traces(
                hovertemplate="%{x}: $%{y:,.0f}<extra></extra>", marker_line_width=0
            )
            st.plotly_chart(
                style(fig_store, height=360),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Revenue by Category</div><p class="dash-card__subtitle">Donut share — hover for values</p><div class="dash-card__accent dash-card__accent--amber"></div>',
            unsafe_allow_html=True,
        )
        if by_category.empty:
            empty_state("No category breakdown.", "")
        else:
            fig_cat = px.pie(by_category, names="category", values="revenue", hole=0.58)
            fig_cat.update_traces(
                textposition="outside",
                textinfo="percent+label",
                hovertemplate="%{label}: $%{value:,.0f} (%{percent})<extra></extra>",
                marker={"line": {"color": "white", "width": 2}},
            )
            st.plotly_chart(
                style(fig_cat, currency=False, legend=True, height=360),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # KPI vs previous period — small comparison bar
    st.markdown(
        '<div class="section-head"><h3>Period comparison</h3><p>Current vs. equal-length prior period</p></div>',
        unsafe_allow_html=True,
    )
    comp_df = pd.DataFrame(
        [
            {
                "metric": "Revenue",
                "Current": current["revenue"],
                "Prior": previous["revenue"],
            },
            {
                "metric": "Orders",
                "Current": float(current["orders"]),
                "Prior": float(previous["orders"]),
            },
            {
                "metric": "Customers",
                "Current": float(current["customers"]),
                "Prior": float(previous["customers"]),
            },
        ]
    )
    comp_melt = comp_df.melt(id_vars="metric", var_name="Period", value_name="Value")
    fig_comp = px.bar(
        comp_melt,
        x="metric",
        y="Value",
        color="Period",
        barmode="group",
        color_discrete_map={"Current": WALMART_BLUE, "Prior": "#94A3B8"},
    )
    fig_comp.update_traces(
        hovertemplate="%{x} · %{fullData.name}: %{y:,.0f}<extra></extra>"
    )
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.plotly_chart(
        style(fig_comp, currency=False, height=320),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ============ TRENDS & MIX TAB ============
with tab_trends:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Revenue by Payment Method</div><p class="dash-card__subtitle">How customers pay</p><div class="dash-card__accent dash-card__accent--teal"></div>',
            unsafe_allow_html=True,
        )
        if by_payment.empty:
            empty_state("No payment data.", "")
        else:
            fig_pay = px.pie(
                by_payment,
                names="payment_method",
                values="revenue",
                hole=0.58,
                color_discrete_sequence=PALETTE,
            )
            fig_pay.update_traces(
                textposition="outside",
                textinfo="percent+label",
                hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
                marker={"line": {"color": "white", "width": 2}},
            )
            st.plotly_chart(
                style(fig_pay, currency=False, height=380),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Revenue by Order Status</div><p class="dash-card__subtitle">Fulfillment mix in the filtered window</p><div class="dash-card__accent"></div>',
            unsafe_allow_html=True,
        )
        if by_status.empty:
            empty_state("No status breakdown.", "")
        else:
            fig_status = px.bar(
                by_status,
                x="status" if "status" in by_status.columns else by_status.columns[0],
                y="revenue",
                color="revenue",
                color_continuous_scale=["#FEF3C7", "#D97706"],
                labels={"revenue": "Revenue", by_status.columns[0]: ""},
            )
            fig_status.update_layout(coloraxis_showscale=False)
            fig_status.update_traces(hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
            st.plotly_chart(
                style(fig_status, height=380),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Daily detail when granularity is coarser — show underlying daily series too
    if granularity != "day":
        st.markdown(
            '<div class="section-head"><h3>Daily detail</h3><p>Underlying daily revenue for the same filters</p></div>',
            unsafe_allow_html=True,
        )
        try:
            daily = get_revenue_trend(filters, "day")
        except Exception:  # noqa: BLE001 — daily detail is optional
            daily = pd.DataFrame()
        if daily.empty:
            empty_state("No daily data.", "")
        else:
            daily["period"] = pd.to_datetime(daily["period"])
            fig_daily = px.bar(
                daily,
                x="period",
                y="revenue",
                labels={"period": "", "revenue": "Revenue"},
            )
            fig_daily.update_traces(
                marker_color="rgba(0,113,206,0.75)",
                hovertemplate="$%{y:,.0f}<br>%{x|%b %d}<extra></extra>",
            )
            st.markdown('<div class="dash-card">', unsafe_allow_html=True)
            st.plotly_chart(
                style(fig_daily, height=300),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown("</div>", unsafe_allow_html=True)

# ============ BREAKDOWN TAB ============
with tab_breakdown:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Top 10 Brands</div><p class="dash-card__subtitle">Horizontal bar — highest revenue first</p><div class="dash-card__accent"></div>',
            unsafe_allow_html=True,
        )
        if by_brand.empty:
            empty_state("No brand data.", "")
        else:
            fig_brand = px.bar(
                by_brand,
                x="revenue",
                y="brand",
                orientation="h",
                labels={"brand": "", "revenue": "Revenue"},
            )
            fig_brand.update_layout(yaxis={"categoryorder": "total ascending"})
            fig_brand.update_traces(
                marker_color=WALMART_BLUE,
                hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
            )
            st.plotly_chart(
                style(fig_brand, height=420),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="dash-card"><div class="dash-card__title">Category → Brand</div><p class="dash-card__subtitle">Treemap — area = revenue</p><div class="dash-card__accent dash-card__accent--amber"></div>',
            unsafe_allow_html=True,
        )
        if treemap_data.empty:
            empty_state(
                "No category/brand data for the current filters.",
                "Try including more categories.",
            )
        else:
            fig_tree = px.treemap(
                treemap_data,
                path=["category_name", "brand_name"],
                values="revenue",
                color="revenue",
                color_continuous_scale=["#DBEAFE", "#1E3A5F"],
            )
            fig_tree.update_traces(
                textinfo="label+value",
                hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
            )
            fig_tree.update_layout(coloraxis_showscale=False)
            st.plotly_chart(
                style(fig_tree, currency=False, legend=False, height=420),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Inline tables for brand/category raw numbers
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**Revenue by Category — table**")
        dataframe_with_download(
            by_category.rename(columns={"category": "category", "revenue": "revenue"}),
            "revenue_by_category.csv",
            key="dl_cat",
            column_config={
                "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f")
            },
        )
    with t2:
        st.markdown("**Revenue by Store — table**")
        dataframe_with_download(
            by_store,
            "revenue_by_store.csv",
            key="dl_store",
            column_config={
                "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f")
            },
        )

# ============ DATA TAB ============
with tab_data:
    st.markdown(
        f"""
        <div class="section-head"><h3>Top performers</h3><p>Ranked by revenue in the filtered window · {start_date:%b %d} – {end_date_inclusive:%b %d, %Y}</p></div>
        """,
        unsafe_allow_html=True,
    )
    p_col, c_col = st.columns(2)
    with p_col:
        st.markdown("**Top 10 Products**")
        dataframe_with_download(
            top_products,
            f"top_products_{start_date}_{end_date_inclusive}.csv",
            key="dl_products",
            column_config={
                "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f"),
                "units_sold": st.column_config.NumberColumn("Units Sold", format="%d"),
            },
        )
    with c_col:
        st.markdown("**Top 10 Customers**")
        dataframe_with_download(
            top_customers,
            f"top_customers_{start_date}_{end_date_inclusive}.csv",
            key="dl_customers",
            column_config={
                "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f"),
                "orders": st.column_config.NumberColumn("Orders", format="%d"),
            },
        )

    st.markdown("---")
    st.markdown("**Recent order lines (most recent 200)**")
    # Lightweight in-table search — filters the already-fetched 200 rows client-side
    search = st.text_input(
        "Search in recent orders",
        placeholder="Filter by product, customer, store, brand…",
        key="recent_search",
    )
    recent_view = recent
    if search and not recent.empty:
        mask = pd.Series(False, index=recent.index)
        q = search.lower()
        for col in recent.columns:
            mask = mask | recent[col].astype(str).str.lower().str.contains(q, na=False)
        recent_view = recent[mask]
        st.caption(
            f"Showing {len(recent_view)} of {len(recent)} rows matching “{search}”."
        )
    dataframe_with_download(
        recent_view,
        f"recent_orders_{start_date}_{end_date_inclusive}.csv",
        key="dl_recent",
        column_config={
            "line_amount": st.column_config.NumberColumn("Line Amount", format="$%.2f"),
            "unit_price": st.column_config.NumberColumn("Unit Price", format="$%.2f"),
            "quantity": st.column_config.NumberColumn("Qty", format="%d"),
        },
    )
    st.caption(
        "Bounded to 200 rows for performance — download the CSV for the same sample. Full history lives in `gold.fact_order_items`."
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
footer()
