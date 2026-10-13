"""
dashboard/helpers/queries.py

All SQL against the gold star schema lives here, separate from the
Streamlit pages. Two design choices drive this file:

1. Every query is parameterized via SQLAlchemy `text()` + bound params —
   never f-string-interpolated filter values — so this stays immune to
   SQL injection regardless of what a user types into a multiselect.
2. Filtering AND aggregation both happen in Postgres, not pandas. Only
   the already-summarized rows a chart needs come back over the wire —
   this scales to a much larger fact table than "load everything, group
   in pandas" would.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text

from src.utils import engine as config
from src.utils.connection import get_postgres_engine

GOLD = config.POSTGRES_SCHEMA_GOLD

# Single shared join graph — every query below selects/aggregates from
# this same FROM clause so results stay consistent with each other.
BASE_FROM = f"""
    FROM {GOLD}.fact_order_items foi
    JOIN {GOLD}.dim_orders o ON foi.order_id = o.order_id
    JOIN {GOLD}.dim_products p ON foi.product_id = p.product_id
    LEFT JOIN {GOLD}.dim_brands b ON p.brand_id = b.brand_id
    LEFT JOIN {GOLD}.dim_categories c ON p.category_id = c.category_id
    LEFT JOIN {GOLD}.dim_stores s ON o.store_id = s.store_id
    LEFT JOIN {GOLD}.dim_payment_methods pm ON o.payment_method_id = pm.payment_method_id
    LEFT JOIN {GOLD}.dim_customers cu ON o.customer_id = cu.customer_id
"""


@dataclass(frozen=True)
class Filters:
    """Immutable filter state, built once from the sidebar each rerun.
    Frozen + hashable so Streamlit's cache can key on it directly."""

    start_date: date
    end_date: date  # exclusive upper bound
    stores: tuple = field(default_factory=tuple)
    categories: tuple = field(default_factory=tuple)
    statuses: tuple = field(default_factory=tuple)
    provinces: tuple = field(default_factory=tuple)
    brands: tuple = field(default_factory=tuple)
    payments: tuple = field(default_factory=tuple)
    search: str = ""
    min_value: float = 0.0
    compare: str = (
        "prior"  # "prior" (previous equal window) or "yoy" (same window last year)
    )

    def previous_period(self) -> Filters:
        """Baseline window for period over period KPI deltas."""
        if self.compare == "yoy":
            return self.year_ago()
        span = (self.end_date - self.start_date).days
        return replace(
            self,
            start_date=self.start_date - timedelta(days=span),
            end_date=self.start_date,
        )

    def year_ago(self) -> Filters:
        """Same window shifted back 365 days for year over year comparison."""
        return replace(
            self,
            start_date=self.start_date - timedelta(days=365),
            end_date=self.end_date - timedelta(days=365),
        )

    def split_in_half(self) -> tuple[Filters, Filters]:
        """Split the window into two equal halves — fallback baseline when
        the prior period is empty (e.g. 'All time' starts at MIN(date))."""
        span = (self.end_date - self.start_date).days
        mid = self.start_date + timedelta(days=span // 2)
        return (
            replace(self, end_date=mid),
            replace(self, start_date=mid),
        )


def _escape_like(raw: str) -> str:
    """Escape SQL LIKE wildcards so free text search matches literally."""
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _where(filters: Filters) -> tuple[str, dict]:
    """Shared WHERE clause + params for every query.

    An empty selection means 'match nothing'. SQLAlchemy renders an empty
    expanding IN as a typed INTEGER NULL set, which Postgres refuses to
    compare against varchar columns — so an empty tuple short circuits to
    `1 = 0` with no tuple params instead of reaching the database.
    """
    in_filters = {
        "stores": "s.store_name",
        "categories": "c.category_name",
        "statuses": "o.order_status",
        "provinces": "s.province",
        "brands": "b.brand_name",
        "payments": "pm.payment_method_name",
    }
    if any(not tuple(getattr(filters, key)) for key in in_filters):
        return "1 = 0", {}
    sql = """
        foi.is_active = true
        AND o.is_active = true
        AND o.order_timestamp >= :start_date
        AND o.order_timestamp < :end_date
        AND s.store_name IN :stores
        AND c.category_name IN :categories
        AND o.order_status IN :statuses
        AND s.province IN :provinces
        AND b.brand_name IN :brands
        AND pm.payment_method_name IN :payments
        AND o.total_amount >= :min_value
    """
    params = {
        "start_date": filters.start_date,
        "end_date": filters.end_date,
        "stores": tuple(filters.stores),
        "categories": tuple(filters.categories),
        "statuses": tuple(filters.statuses),
        "provinces": tuple(filters.provinces),
        "brands": tuple(filters.brands),
        "payments": tuple(filters.payments),
        "min_value": float(filters.min_value),
    }
    if filters.search.strip():
        # Bound ILIKE with escaped wildcards: free text can never alter
        # the query shape, only the matched literal.
        sql += " AND cu.customer_name ILIKE :search ESCAPE '\\'"
        params["search"] = f"%{_escape_like(filters.search.strip())}%"
    return sql, params


def _run(sql: str, params: dict) -> pd.DataFrame:
    """Execute a parameterized query, auto-detecting which params need
    an expanding IN bind (tuples) vs. a plain scalar bind."""
    stmt = text(sql)
    expanding = [k for k, v in params.items() if isinstance(v, tuple)]
    if expanding:
        stmt = stmt.bindparams(*[bindparam(k, expanding=True) for k in expanding])
    with get_postgres_engine().connect() as conn:
        return pd.read_sql(stmt, conn, params=params)


# ---------------------------------------------------------------------------
# Filter option lists — small and slow-changing, cached longer than data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_filter_options() -> dict:
    engine = get_postgres_engine()
    stores = pd.read_sql(
        f"SELECT DISTINCT store_name FROM {GOLD}.dim_stores WHERE is_active = true ORDER BY 1",
        engine,
    )["store_name"].tolist()
    categories = pd.read_sql(
        f"SELECT DISTINCT category_name FROM {GOLD}.dim_categories ORDER BY 1", engine
    )["category_name"].tolist()
    statuses = pd.read_sql(
        f"SELECT DISTINCT order_status FROM {GOLD}.dim_orders WHERE is_active = true ORDER BY 1",
        engine,
    )["order_status"].tolist()
    provinces = pd.read_sql(
        f"SELECT DISTINCT province FROM {GOLD}.dim_stores WHERE is_active = true AND province IS NOT NULL ORDER BY 1",
        engine,
    )["province"].tolist()
    brands = pd.read_sql(
        f"SELECT DISTINCT brand_name FROM {GOLD}.dim_brands ORDER BY 1", engine
    )["brand_name"].tolist()
    payments = pd.read_sql(
        f"SELECT DISTINCT payment_method_name FROM {GOLD}.dim_payment_methods ORDER BY 1",
        engine,
    )["payment_method_name"].tolist()
    bounds = pd.read_sql(
        f"""SELECT MIN(order_timestamp)::date AS min_date, MAX(order_timestamp)::date AS max_date
            FROM {GOLD}.dim_orders WHERE is_active = true""",
        engine,
    ).iloc[0]
    return {
        "stores": stores,
        "categories": categories,
        "statuses": statuses,
        "provinces": provinces,
        "brands": brands,
        "payments": payments,
        "min_date": bounds["min_date"],
        "max_date": bounds["max_date"],
    }


@st.cache_data(ttl=600)
def get_gold_meta() -> dict:
    """Lightweight warehouse metadata for the header/footer."""
    engine = get_postgres_engine()
    row = pd.read_sql(
        f"""
        SELECT
            (SELECT COUNT(*) FROM {GOLD}.fact_order_items WHERE is_active = true) AS fact_rows,
            (SELECT MAX(order_timestamp) FROM {GOLD}.dim_orders WHERE is_active = true) AS last_order_ts
        """,
        engine,
    ).iloc[0]
    return {"fact_rows": int(row["fact_rows"]), "last_order_ts": row["last_order_ts"]}


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def get_kpis(filters: Filters) -> dict:
    where, params = _where(filters)
    sql = f"""
        SELECT
            COALESCE(SUM(foi.line_amount), 0) AS revenue,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(DISTINCT o.customer_id) AS customers
        {BASE_FROM}
        WHERE {where}
    """
    row = _run(sql, params)
    if row.empty:
        # Empty selection (or impossible window): zeros, not an IndexError.
        return {"revenue": 0.0, "orders": 0, "customers": 0, "aov": 0.0}
    row = row.iloc[0]
    revenue = float(row["revenue"])
    orders = int(row["orders"])
    return {
        "revenue": revenue,
        "orders": orders,
        "customers": int(row["customers"]),
        "aov": revenue / orders if orders else 0.0,
    }


# ---------------------------------------------------------------------------
# Extended KPIs — volume, loyalty, and operational leak in one pass
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def get_kpis_extended(filters: Filters) -> dict:
    """Units, repeat customers, and cancelled/returned orders.

    Totals always return exactly one row (COALESCE, no GROUP BY); the
    repeat count is 0 when the per customer CTE is empty. Ratios are
    derived in Python with zero guards (see safe_div in callers).
    """
    where, params = _where(filters)
    sql = f"""
        WITH per_customer AS (
            SELECT cu.customer_id, COUNT(DISTINCT o.order_id) AS n_orders
            {BASE_FROM}
            WHERE {where} AND cu.customer_id IS NOT NULL
            GROUP BY cu.customer_id
        ),
        totals AS (
            SELECT
                COALESCE(SUM(foi.line_amount), 0) AS revenue,
                COALESCE(SUM(foi.quantity), 0)    AS units,
                COUNT(DISTINCT o.order_id)        AS orders,
                COUNT(DISTINCT cu.customer_id)    AS customers,
                COUNT(DISTINCT o.order_id) FILTER (
                    WHERE LOWER(o.order_status) IN ('cancelled', 'returned')
                ) AS cancelled
            {BASE_FROM}
            WHERE {where}
        )
        SELECT t.*,
               (SELECT COUNT(*) FROM per_customer WHERE n_orders >= 2)
                   AS repeat_customers
        FROM totals t
    """
    row = _run(sql, params).iloc[0]
    return {
        "revenue": float(row["revenue"]),
        "units": int(row["units"]),
        "orders": int(row["orders"]),
        "customers": int(row["customers"]),
        "cancelled": int(row["cancelled"]),
        "repeat_customers": int(row["repeat_customers"]),
    }


@st.cache_data(ttl=600)
def get_daily_kpis(filters: Filters) -> pd.DataFrame:
    """One row per day: revenue, distinct orders, distinct customers.

    Feeds the KPI sparklines. Bounded by the window length (a full year
    is ~366 rows), so it stays cheap.
    """
    where, params = _where(filters)
    sql = f"""
        SELECT o.order_timestamp::date AS day,
               SUM(foi.line_amount) AS revenue,
               COUNT(DISTINCT foi.order_id) AS orders,
               COUNT(DISTINCT o.customer_id) AS customers
        {BASE_FROM}
        WHERE {where}
        GROUP BY 1
        ORDER BY 1
    """
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_monthly_revenue(filters: Filters) -> pd.DataFrame:
    """Revenue per calendar month in the window (month-over-month growth)."""
    where, params = _where(filters)
    sql = f"""
        SELECT date_trunc('month', o.order_timestamp) AS month,
               SUM(foi.line_amount) AS revenue
        {BASE_FROM}
        WHERE {where}
        GROUP BY 1
        ORDER BY 1
    """
    return _run(sql, params)


# ---------------------------------------------------------------------------
# Revenue trend — aggregated in SQL at the requested granularity
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def get_revenue_trend(filters: Filters, granularity: str) -> pd.DataFrame:
    if granularity not in {"day", "week", "month"}:
        raise ValueError(f"Unsupported granularity: {granularity}")
    where, params = _where(filters)
    sql = f"""
        SELECT date_trunc(:granularity, o.order_timestamp) AS period,
               SUM(foi.line_amount) AS revenue
        {BASE_FROM}
        WHERE {where}
        GROUP BY 1
        ORDER BY 1
    """
    params["granularity"] = granularity
    return _run(sql, params)


# ---------------------------------------------------------------------------
# Breakdown queries — one GROUP BY each, computed in Postgres
# ---------------------------------------------------------------------------
_DIMENSION_COLUMNS = {
    "store": "s.store_name",
    "category": "c.category_name",
    "brand": "b.brand_name",
    "payment_method": "pm.payment_method_name",
    "order_status": "o.order_status",
}


@st.cache_data(ttl=600)
def get_revenue_by(
    filters: Filters, dimension: str, limit: int | None = None
) -> pd.DataFrame:
    """Revenue grouped by one dimension. `dimension` must be a key in the
    fixed whitelist above — never raw user text — so this can't be used
    to build arbitrary SQL."""
    if dimension not in _DIMENSION_COLUMNS:
        raise ValueError(f"Unsupported dimension: {dimension}")
    col = _DIMENSION_COLUMNS[dimension]
    where, params = _where(filters)
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    sql = f"""
        SELECT {col} AS {dimension}, SUM(foi.line_amount) AS revenue
        {BASE_FROM}
        WHERE {where} AND {col} IS NOT NULL
        GROUP BY 1
        ORDER BY revenue DESC
        {limit_sql}
    """
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_category_brand_treemap(filters: Filters) -> pd.DataFrame:
    where, params = _where(filters)
    sql = f"""
        SELECT c.category_name, b.brand_name, SUM(foi.line_amount) AS revenue
        {BASE_FROM}
        WHERE {where} AND c.category_name IS NOT NULL AND b.brand_name IS NOT NULL
        GROUP BY c.category_name, b.brand_name
        ORDER BY revenue DESC
    """
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_top_products(filters: Filters, limit: int = 10) -> pd.DataFrame:
    where, params = _where(filters)
    sql = f"""
        SELECT p.product_name, b.brand_name, c.category_name,
               SUM(foi.line_amount) AS revenue,
               SUM(foi.quantity) AS units_sold
        {BASE_FROM}
        WHERE {where}
        GROUP BY p.product_name, b.brand_name, c.category_name
        ORDER BY revenue DESC
        LIMIT :limit
    """
    params["limit"] = limit
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_product_revenue(filters: Filters) -> pd.DataFrame:
    """Revenue per product, full list ordered desc (Pareto analysis)."""
    where, params = _where(filters)
    sql = f"""
        SELECT p.product_name, SUM(foi.line_amount) AS revenue
        {BASE_FROM}
        WHERE {where}
        GROUP BY p.product_name
        ORDER BY revenue DESC
    """
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_top_customers(filters: Filters, limit: int = 10) -> pd.DataFrame:
    where, params = _where(filters)
    sql = f"""
        SELECT cu.customer_name,
               SUM(foi.line_amount) AS revenue,
               COUNT(DISTINCT o.order_id) AS orders
        {BASE_FROM}
        WHERE {where} AND cu.customer_name IS NOT NULL
        GROUP BY cu.customer_name
        ORDER BY revenue DESC
        LIMIT :limit
    """
    params["limit"] = limit
    return _run(sql, params)


@st.cache_data(ttl=600)
def get_recent_order_lines(filters: Filters, limit: int = 200) -> pd.DataFrame:
    """A bounded sample for the 'raw data' expander — not the full
    filtered set, to avoid pulling unbounded rows into the app."""
    where, params = _where(filters)
    sql = f"""
        SELECT o.order_timestamp, s.store_name, cu.customer_name, p.product_name,
               b.brand_name, c.category_name, foi.quantity, foi.unit_price,
               foi.line_amount, o.order_status, pm.payment_method_name
        {BASE_FROM}
        WHERE {where}
        ORDER BY o.order_timestamp DESC
        LIMIT :limit
    """
    params["limit"] = limit
    return _run(sql, params)
