---
name: dashboard-bugfix
description: Diagnose and fix Streamlit dashboard bugs using the symptom-to-cause map. Use when a dashboard page errors, renders wrong, or misbehaves.
---

# Dashboard bugfix

Scope: `dashboard/` only. Read `dashboard/AGENTS.md` first.

## Symptom map (check in order)

1. **Literal HTML on screen** — indented or blank-line HTML in
   `st.markdown` renders as text. Route every HTML block through
   `helpers/components.py::_safe_html`.
2. **Cloud connects fail, local works** — page never calls
   `lib/db.py::apply_secrets()` before config reads. Cloud has no
   `.env`; call it at the top of the entry page.
3. **Import error for `databricks`** — unconditional `from databricks`
   import somewhere. The connector is excluded from
   `dashboard/requirements.txt` on purpose; guard the import.
4. **Stale `app.py` reference** — entry point is `dashboard/home.py`.
   No `app.py` exists; fix the reference, don't create the file.
5. **First query slow or failing on Cloud** — Neon free tier sleeps.
   Engine needs `pool_pre_ping=True` and the pooled host.
6. **Widget state leaks between pages** — missing `key_prefix` or
   duplicate download keys (`dl_<page>_<name>`).

## Workflow

1. Reproduce with `uv run streamlit run dashboard/home.py` (never
   `python dashboard/home.py`).
2. Narrow to layer: page (import/filter/query/plot), `lib/`, `helpers/`.
3. Fix at the layer that owns the bug; don't duplicate SQL or charts.
4. Re-run `dashboard-verify` before declaring done.
