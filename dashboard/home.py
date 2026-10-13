"""Walmart Gold Dashboard — home."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.lib.db import apply_secrets

# Secrets first: pages after this read config at import time.
apply_secrets()

from dashboard.helpers import plotly_template
from dashboard.helpers.components import (
    filter_chips,
    footer,
    kpi_cards,
    kpi_quality_cards,
)
from dashboard.helpers.theme import get_theme, inject_css
from dashboard.lib.filters import sidebar_filters
from dashboard.lib.queries import (
    get_daily_kpis,
    get_gold_meta,
    get_kpis,
    get_kpis_extended,
    get_monthly_revenue,
    get_top_products,
)

st.set_page_config(page_title="Walmart — Home", page_icon="🛒", layout="wide")
plotly_template.apply_default_template(get_theme())
st.markdown(inject_css(), unsafe_allow_html=True)

st.title("Walmart Gold Dashboard")
st.caption("Use the sidebar pages: Sales, Products, Customers, Categories.")

try:
    filters, meta = sidebar_filters()
    filter_chips(filters)
    gold = get_gold_meta()
    current = get_kpis(filters)
    previous = get_kpis(filters.previous_period())
    daily = get_daily_kpis(filters)

    def _pct(curr: float, prev: float) -> float | None:
        return (curr - prev) / prev * 100 if prev else None

    def _div(a: float, b: float) -> float:
        return float(a) / float(b) if b else 0.0

    kpi_cards(
        current["revenue"],
        current["orders"],
        current["customers"],
        current["aov"],
        {
            "revenue": _pct(current["revenue"], previous["revenue"]),
            "orders": _pct(float(current["orders"]), float(previous["orders"])),
            "customers": _pct(
                float(current["customers"]), float(previous["customers"])
            ),
            "aov": _pct(current["aov"], previous["aov"]),
        },
        sparklines={
            "revenue": daily["revenue"].tolist() if not daily.empty else [],
            "orders": daily["orders"].tolist() if not daily.empty else [],
            "customers": daily["customers"].tolist() if not daily.empty else [],
            "aov": (
                (daily["revenue"] / daily["orders"].replace(0, float("nan")))
                .fillna(0.0)
                .tolist()
                if not daily.empty
                else []
            ),
        },
    )

    st.subheader("Quality and growth")
    ext = get_kpis_extended(filters)
    prev_ext = get_kpis_extended(filters.previous_period())
    monthly = get_monthly_revenue(filters)
    mom = (
        _pct(float(monthly["revenue"].iloc[-1]), float(monthly["revenue"].iloc[-2]))
        if len(monthly) >= 2
        else None
    )
    top10 = get_top_products(filters, limit=10)
    concentration = (
        _div(float(top10["revenue"].sum()), ext["revenue"]) * 100
        if ext["revenue"]
        else None
    )
    kpi_quality_cards(
        [
            {
                "label": "Units Sold",
                "icon": "📦",
                "value": f"{ext['units']:,}",
                "delta": _pct(float(ext["units"]), float(prev_ext["units"])),
                "foot": "Total quantity",
                "accent": "#0E9F6E",
            },
            {
                "label": "Items per Order",
                "icon": "🧺",
                "value": f"{_div(ext['units'], ext['orders']):.2f}",
                "delta": _pct(
                    _div(ext["units"], ext["orders"]),
                    _div(prev_ext["units"], prev_ext["orders"]),
                ),
                "foot": "Basket depth",
                "accent": "#00A9E0",
            },
            {
                "label": "Revenue per Customer",
                "icon": "💳",
                "value": f"${_div(ext['revenue'], ext['customers']):,.2f}",
                "delta": _pct(
                    _div(ext["revenue"], ext["customers"]),
                    _div(prev_ext["revenue"], prev_ext["customers"]),
                ),
                "foot": "Customer value",
                "accent": "#7B5CFF",
            },
            {
                "label": "Repeat Rate",
                "icon": "🔁",
                "value": f"{_div(ext['repeat_customers'], ext['customers']) * 100:.1f}%",
                "delta": _pct(
                    _div(ext["repeat_customers"], ext["customers"]),
                    _div(prev_ext["repeat_customers"], prev_ext["customers"]),
                ),
                "foot": "Customers with 2+ orders",
                "accent": "#0071CE",
            },
            {
                "label": "Cancel/Return Rate",
                "icon": "⚠️",
                "value": f"{_div(ext['cancelled'], ext['orders']) * 100:.1f}%",
                "delta": _pct(
                    _div(ext["cancelled"], ext["orders"]),
                    _div(prev_ext["cancelled"], prev_ext["orders"]),
                ),
                "foot": "Cancelled + returned orders",
                "accent": "#E7462A",
            },
            {
                "label": "MoM Growth",
                "icon": "📈",
                "value": f"{mom:+.1f}%" if mom is not None else "—",
                "delta": mom,
                "foot": "Last vs previous month",
                "accent": "#0E9F6E",
            },
            {
                "label": "Top 10 Share",
                "icon": "🏆",
                "value": f"{concentration:.1f}%" if concentration is not None else "—",
                "delta": None,
                "foot": "Top products revenue share",
                "accent": "#FFC220",
            },
        ]
    )
    selected = {str(s).lower() for s in filters.statuses}
    if not ({"cancelled", "returned"} & selected):
        st.caption(
            "Cancel/Return rate reads 0 because the status filter excludes "
            "cancelled and returned orders."
        )
    st.info(
        f"Gold fact rows: {gold.get('fact_rows', 0):,} · Last order: {gold.get('last_order_ts') or '—'}"
    )
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not connect to Postgres: {exc}")
    st.stop()

footer()
