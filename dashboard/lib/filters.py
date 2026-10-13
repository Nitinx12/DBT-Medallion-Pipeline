"""Sidebar filter builder shared by every page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from dashboard.helpers.queries import Filters, get_filter_options


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

        default_range: tuple[date, date] = st.session_state.get(
            f"{key_prefix}_date_range", (min_date, max_date)
        )
        default_range = (
            max(min_date, default_range[0]),
            min(max_date, default_range[1]),
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

        st.markdown("---")
        selected_stores = st.multiselect(
            "Store(s)",
            options["stores"],
            default=options["stores"],
            key=f"{key_prefix}stores",
        )
        selected_categories = st.multiselect(
            "Categor(y/ies)",
            options["categories"],
            default=options["categories"],
            key=f"{key_prefix}cats",
        )
        selected_statuses = st.multiselect(
            "Order status",
            options["statuses"],
            default=options["statuses"],
            key=f"{key_prefix}status",
        )

    filters = Filters(
        start_date=start_date,
        end_date=end_inclusive + timedelta(days=1),
        stores=tuple(selected_stores),
        categories=tuple(selected_categories),
        statuses=tuple(selected_statuses),
    )
    meta = {
        "start_date": start_date,
        "end_inclusive": end_inclusive,
        "options": options,
    }
    return filters, meta
