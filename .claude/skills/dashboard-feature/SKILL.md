---
name: dashboard-feature
description: Add dashboard KPIs, charts, filters, pages, and map views the right way. Use for any dashboard enhancement.
---

# Dashboard feature

Scope: `dashboard/` only. Read `dashboard/AGENTS.md` section 4 first;
the layering and SQL rules there are non-negotiable.

## Where things go

- New SQL → `helpers/queries.py`, re-exported in `lib/queries.py`.
  Pages import from `dashboard.lib.queries` only.
- New figure → builder in `lib/charts.py` (wrapped in `theme.style()`).
- New shared widget/HTML → `helpers/components.py` (HTML via
  `_safe_html`).
- New page → `dashboard/pages/N_Name.py` (numeric prefix sets order),
  thin by rule: import, filter, query, plot.

## Rules that apply to every feature

- Bind every value with SQLAlchemy `text()` params; new GROUP BY
  dimensions go through `_DIMENSION_COLUMNS`. Aggregate in Postgres;
  pages receive summarized rows (200-row sample is the only exception).
- Keep `Filters` frozen and hashable; tuples, not lists, into cached
  functions. Sidebar widgets take `key_prefix`.
- `end_date` stays an EXCLUSIVE upper bound; empty selections match
  nothing and render `empty_state`, never a traceback.
- Guard every ratio against zero denominators.
- Map views: coordinates in `lib/geo.py` are synthetic demo points.
  Never present them as real addresses.
- New dependency: `uv add <pkg>`, then mirror it in
  `dashboard/requirements.txt` (Cloud/Docker read that file, not
  `pyproject.toml`). Never add `databricks-sql-connector` there.
