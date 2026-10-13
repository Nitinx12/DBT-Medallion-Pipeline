"""Plotly chart helpers shared by every page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px

from dashboard.helpers.theme import PALETTE, WALMART_BLUE, style


def revenue_trend_chart(trend: pd.DataFrame, granularity: str = "week"):
    df = trend.copy()
    df["period"] = pd.to_datetime(df["period"])
    fig = px.area(
        df, x="period", y="revenue", labels={"period": "", "revenue": "Revenue"}
    )
    fig.update_traces(
        line={"color": WALMART_BLUE, "width": 2.6},
        fillcolor="rgba(0,113,206,0.12)",
        hovertemplate="Revenue: $%{y:,.0f}<br>%{x|%b %d, %Y}<extra></extra>",
    )
    return style(fig, height=360)


def bar_by(df: pd.DataFrame, x: str, title: str = ""):
    fig = px.bar(
        df,
        x=x,
        y="revenue",
        color="revenue",
        color_continuous_scale=["#DBEAFE", WALMART_BLUE],
        labels={x: "", "revenue": "Revenue"},
        title=title,
    )
    fig.update_layout(coloraxis_showscale=False)
    fig.update_traces(
        hovertemplate="%{x}: $%{y:,.0f}<extra></extra>", marker_line_width=0
    )
    return style(fig, height=360)


def donut(df: pd.DataFrame, names: str):
    fig = px.pie(
        df, names=names, values="revenue", hole=0.58, color_discrete_sequence=PALETTE
    )
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
        marker={"line": {"color": "white", "width": 2}},
    )
    return style(fig, currency=False, height=360)
