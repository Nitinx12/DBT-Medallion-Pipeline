"""Plotly chart helpers shared by every page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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


def treemap(df: pd.DataFrame):
    fig = px.treemap(
        df,
        path=[px.Constant("All"), "category_name", "brand_name"],
        values="revenue",
        color="revenue",
        color_continuous_scale=["#DCEBFA", WALMART_BLUE, "#0B1F3A"],
    )
    fig.update_traces(
        textinfo="label+percent root",
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percentRoot:.1%} of total<extra></extra>",
        marker={"cornerradius": 6, "line": {"width": 2, "color": "white"}},
    )
    fig.update_layout(
        coloraxis_showscale=False, height=460, margin={"t": 8, "l": 0, "r": 0, "b": 0}
    )
    return style(fig, currency=False, legend=False)


def pareto(df: pd.DataFrame):
    """80/20 chart: bars for revenue plus cumulative share line.

    Expects product_name + revenue columns sorted desc (see
    get_product_revenue). Returns (fig, products_for_80_pct).
    """
    df = df.copy()
    df["cum"] = df.revenue.cumsum() / df.revenue.sum() * 100
    n80 = int((df["cum"] < 80).sum()) + 1 if not df.empty else 0
    fig = go.Figure()
    fig.add_bar(
        x=df.product_name,
        y=df.revenue,
        name="Revenue",
        marker_color=WALMART_BLUE,
        hovertemplate="%{x}: $%{y:,.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=df.product_name,
        y=df.cum,
        name="Cumulative %",
        yaxis="y2",
        mode="lines+markers",
        line={"color": "#FFC220", "width": 3},
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    )
    fig.update_layout(
        yaxis2={
            "overlaying": "y",
            "side": "right",
            "range": [0, 105],
            "ticksuffix": "%",
            "showgrid": False,
        },
        height=420,
        xaxis={"tickangle": -35},
        showlegend=True,
    )
    return style(fig), n80


def bubble(df: pd.DataFrame):
    """Product portfolio: units vs revenue, size = revenue, color = category."""
    df = df.copy()
    df["avg_price"] = df.revenue / df.units_sold.replace(0, float("nan"))
    fig = px.scatter(
        df,
        x="units_sold",
        y="revenue",
        size="revenue",
        color="category_name",
        hover_name="product_name",
        hover_data={"units_sold": True, "revenue": ":$,.0f", "avg_price": ":$,.2f"},
        size_max=48,
        labels={
            "units_sold": "Units sold",
            "revenue": "Revenue",
            "category_name": "Category",
        },
    )
    return style(fig, height=420)
