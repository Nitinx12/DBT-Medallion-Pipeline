"""Sidebar filter builder shared by every page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from dashboard.helpers.queries import Filters, get_filter_options

# One shared state across pages: the default prefix is empty so choosing
# "Last 30 days" on Sales persists on Products. Page specific controls
# (granularity, Top N) keep their own keys on their own pages.
COMPARE_LABELS = {"Prior period": "prior", "Last year": "yoy"}


def _parse_date(raw: str | None, fallback: date) -> date:
    """Parse an ISO date from the URL, falling back safely on garbage."""
    try:
        return date.fromisoformat(raw) if raw else fallback
    except ValueError:
        return fallback


def _multi(label: str, options: list, key: str) -> tuple:
    """Multiselect defaulting to all options; empty means match nothing."""
    return tuple(
        st.multiselect(label, options, default=options, key=key),
    )


def sidebar_filters(key_prefix: str = "") -> tuple[Filters, dict]:
    options = get_filter_options()
    min_date: date = options["min_date"]
    max_date: date = options["max_date"]

    with st.sidebar:
        # Global theme switch (one key for every page so the choice sticks
        # across navigation; read by theme.get_theme()/inject_css()/style()).
        is_dark = st.checkbox(
            "Dark mode",
            value=st.session_state.get("theme", "light") == "dark",
            key="theme_toggle_global",
        )
        st.session_state["theme"] = "dark" if is_dark else "light"

        st.markdown("**Date presets**")
        c1, c2, c3 = st.columns(3)
        if c1.button("7D", use_container_width=True, key=f"{key_prefix}preset_7d"):
            st.session_state[f"{key_prefix}_date_range"] = (
                max_date - timedelta(days=6),
                max_date,
            )
        if c2.button("30D", use_container_width=True, key=f"{key_prefix}preset_30d"):
            st.session_state[f"{key_prefix}_date_range"] = (
                max_date - timedelta(days=29),
                max_date,
            )
        if c3.button("90D", use_container_width=True, key=f"{key_prefix}preset_90d"):
            st.session_state[f"{key_prefix}_date_range"] = (
                max_date - timedelta(days=89),
                max_date,
            )

        # Shareable URL: ?from=YYYY-MM-DD&to=YYYY-MM-DD seeds the picker.
        params = st.query_params
        url_range = (
            _parse_date(params.get("from"), min_date),
            _parse_date(params.get("to"), max_date),
        )
        default_range: tuple[date, date] = st.session_state.get(
            f"{key_prefix}_date_range", url_range
        )
        default_range = (
            max(min_date, min(default_range[0], max_date)),
            max(min_date, min(default_range[1], max_date)),
        )

        selected_range = st.date_input(
            "Order date range",
            value=default_range,
            min_value=min_date,
            max_value=max_date,
            key=f"{key_prefix}date_range_input",
        )
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_date, end_inclusive = selected_range
        else:
            start_date, end_inclusive = default_range
        if start_date > end_inclusive:
            start_date, end_inclusive = end_inclusive, start_date
        params["from"] = start_date.isoformat()
        params["to"] = end_inclusive.isoformat()

        st.markdown("---")
        selected_stores = _multi("Store(s)", options["stores"], f"{key_prefix}stores")
        selected_categories = _multi(
            "Categor(y/ies)", options["categories"], f"{key_prefix}cats"
        )
        selected_statuses = _multi(
            "Order status", options["statuses"], f"{key_prefix}status"
        )
        selected_provinces = _multi(
            "Province/State", options["provinces"], f"{key_prefix}provinces"
        )
        selected_brands = _multi("Brand(s)", options["brands"], f"{key_prefix}brands")
        selected_payments = _multi(
            "Payment method(s)", options["payments"], f"{key_prefix}payments"
        )

        search = st.text_input(
            "Customer search",
            placeholder="Name contains…",
            key=f"{key_prefix}search",
        )
        min_value = float(
            st.number_input(
                "Min order value",
                min_value=0.0,
                step=50.0,
                key=f"{key_prefix}min_value",
            )
        )
        compare_label = st.radio(
            "Compare against",
            list(COMPARE_LABELS),
            horizontal=True,
            key=f"{key_prefix}compare",
        )

        if st.button(
            "Reset filters", use_container_width=True, key=f"{key_prefix}reset"
        ):
            for k in list(st.session_state.keys()):
                if k.startswith(key_prefix) and not k.startswith("theme"):
                    del st.session_state[k]
            st.query_params.clear()
            st.rerun()

    filters = Filters(
        start_date=start_date,
        end_date=end_inclusive + timedelta(days=1),
        stores=selected_stores,
        categories=selected_categories,
        statuses=selected_statuses,
        provinces=selected_provinces,
        brands=selected_brands,
        payments=selected_payments,
        search=str(search or "").strip(),
        min_value=min_value,
        compare=COMPARE_LABELS[compare_label],
    )
    meta = {
        "start_date": start_date,
        "end_inclusive": end_inclusive,
        "options": options,
    }
    return filters, meta
