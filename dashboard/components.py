"""
dashboard/components.py — Reusable UI building blocks.

Keeps app.py focused on layout/data flow; all HTML card rendering lives here
so it can be tested and restyled in one place.
"""

from __future__ import annotations

import html as html_lib

import pandas as pd
import streamlit as st

from dashboard.theme import SEMANTIC, WALMART_BLUE, WALMART_YELLOW

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
_DELTA_ICON = {"up": "▲", "down": "▼", "flat": "—"}


def _delta_state(pct: float | None) -> str:
    if pct is None:
        return "flat"
    if pct > 0.05:
        return "up"
    if pct < -0.05:
        return "down"
    return "flat"


def kpi_cards(
    revenue: float,
    orders: int,
    customers: int,
    aov: float,
    deltas: dict[str, float | None],
) -> None:
    """Render the 4-card KPI row as a single HTML grid (one st.markdown call)."""
    items = [
        {
            "label": "Total Revenue",
            "icon": "💰",
            "value": f"${revenue:,.0f}",
            "delta": deltas.get("revenue"),
            "foot": "Gross merchandise value",
            "accent": WALMART_BLUE,
        },
        {
            "label": "Orders",
            "icon": "📦",
            "value": f"{orders:,}",
            "delta": deltas.get("orders"),
            "foot": "Distinct order_id",
            "accent": "#0E9F6E",
        },
        {
            "label": "Customers",
            "icon": "👥",
            "value": f"{customers:,}",
            "delta": deltas.get("customers"),
            "foot": "Unique shoppers",
            "accent": "#7B5CFF",
        },
        {
            "label": "Avg Order Value",
            "icon": "🧾",
            "value": f"${aov:,.2f}",
            "delta": deltas.get("aov"),
            "foot": "Revenue / orders",
            "accent": WALMART_YELLOW,
        },
    ]

    cards_html = ""
    for item in items:
        pct = item["delta"]
        state = _delta_state(pct)
        icon = _DELTA_ICON[state]
        if pct is None:
            delta_html = '<span class="kpi-card__delta kpi-card__delta--flat">— no prior period</span>'
        else:
            cls = {
                "up": "kpi-card__delta--up",
                "down": "kpi-card__delta--down",
                "flat": "kpi-card__delta--flat",
            }[state]
            # green for up on revenue/orders, but keep same treatment for all 4 for simplicity
            delta_html = f'<span class="kpi-card__delta {cls}">{icon} {pct:+.1f}% vs prior</span>'

        # Escape dynamic text safely
        label = html_lib.escape(item["label"])
        value = html_lib.escape(item["value"])
        foot = html_lib.escape(item["foot"])
        cards_html += f"""
        <div class="kpi-card" style="--kpi-accent:{item["accent"]};">
            <div class="kpi-card__label">{item["icon"]} {label}</div>
            <div class="kpi-card__value">{value}</div>
            {delta_html}
            <div class="kpi-card__foot">{foot}</div>
        </div>
        """

    st.markdown(f'<div class="kpi-grid">{cards_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Card wrapper helpers
# ---------------------------------------------------------------------------
def card_header(title: str, subtitle: str = "", accent: str = "blue") -> None:
    """Render a card header (title + subtitle + accent bar)."""
    accent_cls = {
        "blue": "",
        "amber": " dash-card__accent--amber",
        "teal": " dash-card__accent--teal",
    }.get(accent, "")
    title_e = html_lib.escape(title)
    sub_e = html_lib.escape(subtitle)
    sub_html = f'<p class="dash-card__subtitle">{sub_e}</p>' if subtitle else ""
    # This is the opening of a card — caller should close with card_footer or just let markdown flow;
    # for Streamlit we render it as a standalone block above the chart.
    st.markdown(
        f"""
        <div style="margin-bottom:2px;">
            <div class="dash-card__title">{title_e}</div>
            {sub_html}
            <div class="dash-card__accent{accent_cls}"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_head(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <h3>{html_lib.escape(title)}</h3>
            <p>{html_lib.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_chips(filters) -> None:
    """Compact row of active-filter chips."""
    chips: list[str] = []
    # Date
    chips.append(
        f'<span class="chip">📅 {filters.start_date:%b %d, %Y} → {filters.end_date:%b %d, %Y} <span style="opacity:0.6">(exclusive end)</span></span>'
    )
    # Counts
    chips.append(
        f'<span class="chip chip--amber">🏬 {len(filters.stores)} store(s)</span>'
    )
    chips.append(
        f'<span class="chip chip--slate">🏷️ {len(filters.categories)} categor(ies)</span>'
    )
    chips.append(
        f'<span class="chip chip--slate">● {len(filters.statuses)} status(s)</span>'
    )
    row = "".join(chips)
    st.markdown(f'<div class="chip-row">{row}</div>', unsafe_allow_html=True)


def empty_state(title: str, hint: str = "") -> None:
    st.markdown(
        f'<div class="empty-state"><strong>{html_lib.escape(title)}</strong><br/>{html_lib.escape(hint)}</div>',
        unsafe_allow_html=True,
    )


def dataframe_with_download(
    df: pd.DataFrame, filename: str, key: str, column_config: dict | None = None
) -> None:
    """Render a dataframe + a CSV download button side-by-side."""
    if df.empty:
        empty_state(
            "No rows for the current filters.",
            "Try widening the date range or clearing a filter.",
        )
        return
    st.dataframe(
        df, use_container_width=True, hide_index=True, column_config=column_config
    )  # type: ignore[arg-type]
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=key,
        use_container_width=False,
    )


def footer() -> None:
    st.markdown(
        f"""
        <div class="dash-footer">
            <span>© 2026 Walmart Medallion Pipeline · <span style="color:{SEMANTIC["text_muted"]}; font-family:{SEMANTIC.get("text", "")}">gold</span> schema · live from Postgres</span>
            <span><a href="https://github.com/anomalyco/walmart" target="_blank">View source</a> &nbsp;·&nbsp; Built with Streamlit + Plotly</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
