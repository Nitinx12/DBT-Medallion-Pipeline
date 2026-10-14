# AGENTS.md

Instructions for AI coding agents (Codex CLI, Claude Code, others) working in this repo.
Scope: the Streamlit dashboard under `dashboard/` and its supporting files. The dbt and Airflow
pipeline is out of scope unless the task says otherwise.

Read this file fully before touching code. Then check `.claude/skills/` for a skill that matches
the task and follow it.

## 1. What this project is

A Walmart medallion pipeline (bronze, silver, gold) built with dbt and PostgreSQL. The dashboard is
a multipage Streamlit and Plotly app that reads the `gold` star schema directly from Postgres.
Production data lives on Neon. Local development uses Docker Postgres. The public app is deployed
on Streamlit Community Cloud from repo `Nitinx12/walmart_dbt`, branch `main`.

Entry point is `dashboard/home.py`. There is no `app.py`. Any mention of one is stale.

## 2. Repo map

```
dashboard/home.py                 entry point, KPI cards, gold freshness banner
dashboard/pages/                  1_Sales.py to 6_Data_Health.py (numeric prefix sets sidebar order)
dashboard/helpers/theme.py        palette, Plotly style(), global CSS
dashboard/helpers/components.py   reusable HTML blocks, _safe_html, KPI cards, tables, footer
dashboard/helpers/queries.py      ALL gold SQL, Filters dataclass
dashboard/lib/queries.py          stable re export shim used by pages
dashboard/lib/filters.py          shared sidebar filter builder
dashboard/lib/charts.py           shared Plotly figure builders
dashboard/lib/db.py               st.secrets to os.environ bridge, engine accessor
dashboard/.streamlit/             config.toml, secrets.toml (git ignored), secrets.toml.example
dashboard/requirements.txt        pinned deps for Cloud and the container
dashboard/Dockerfile              container image
scripts/seed_demo_db.py           one off public demo seeder, not part of the pipeline
src/utils/                        engine.py and connection.py, shared by pipeline and dashboard
```

## 3. Commands

Always use `uv`. Never `pip install` and never bare `python`.

```
uv sync
uv run streamlit run dashboard/home.py
uv run python scripts/seed_demo_db.py "<target url>" --schema gold
uv run ruff check dashboard
uv run pytest tests/unit
uv run python .claude/skills/dashboard-verify/scripts/smoke_check.py
```

Never run a page with `python dashboard/home.py`. Without the Streamlit runtime every widget call
fails with ScriptRunContext warnings. Always go through `streamlit run`.

Add a dependency with `uv add <package>`, then update `dashboard/requirements.txt` to match, since
Cloud and Docker read that file and not `pyproject.toml`.

## 4. Architecture rules (non negotiable)

1. **Layering.** Pages stay thin: import, filter, query, plot. SQL goes in `helpers/queries.py` and
   is re exported in `lib/queries.py`. Figure builders go in `lib/charts.py`. Shared widgets and
   HTML go in `helpers/components.py`. Pages import data functions from `dashboard.lib.queries` only.
2. **SQL safety.** Bind every value with SQLAlchemy `text()` and params. Never interpolate user or
   filter input into SQL. New GROUP BY dimensions must go through the `_DIMENSION_COLUMNS` whitelist.
   Granularity and LIMIT values are validated or cast to int.
3. **Aggregate in Postgres.** Pages receive summarized rows. The only exception is the bounded
   200 row recent orders sample.
4. **Soft delete.** Every query filters `foi.is_active = true` and `o.is_active = true`. Reuse
   `_where()` and `BASE_FROM`. Do not write a second join graph.
5. **Date windows.** `Filters.end_date` is an EXCLUSIVE upper bound. The sidebar converts the
   inclusive end date by adding one day. Do not break this convention.
6. **Empty selections.** An empty tuple means match nothing, via expanding IN binds. Every page must
   render `empty_state` for empty frames and never crash or show a traceback.
7. **Raw HTML.** Every `st.markdown` call with HTML goes through `components._safe_html`. Indented
   or blank line HTML renders as literal text. This bug has already happened once.
8. **sys.path bootstrap.** Every entry page keeps the PROJECT_ROOT snippet from `home.py` so
   `dashboard...` and `src...` imports resolve from any working directory.
9. **Widget keys.** Sidebar widgets use `key_prefix` so pages keep independent state. New widgets
   must have unique keys. Download buttons use keys like `dl_<page>_<name>`.
10. **Caching.** `st.cache_data` with ttl 3600 for filter options and ttl 600 for data queries unless
    the task changes it. `Filters` is a frozen dataclass so it can be a cache key. Use tuples, not
    lists, in anything that reaches a cached function.
11. **Division safety.** Every ratio and percentage guards against a zero denominator.
12. **Secrets.** Local runs read `.env`. Cloud reads `st.secrets` through `lib/db.py`. Never write
    credentials into code, docs, logs, tests, screenshots or commit messages. Never commit
    `secrets.toml`. Only `secrets.toml.example` with dummy values is committed.

## 5. Known issues to be aware of

Verify each one before relying on it. Fix only when the task covers it, otherwise report it.

* `home.py` caption says "Full tabbed view lives in app.py". It is stale. No `app.py` exists.
* `lib/db.py` `apply_secrets()` is not imported by any page. On Streamlit Cloud there is no `.env`,
  so the app can fail to connect. The fix is to call it once at the top of every entry page before
  any import that reads config.
* The Cloud deployment main file must be `dashboard/home.py`. Older notes mention `dashboard/app.py`.
* `card_header`, `section_head` and `filter_chips` in `components.py` are written but unused.
* Neon free tier suspends computes when idle. First query after wake can fail or be slow. The engine
  should use `pool_pre_ping=True` and the pooled host for the app.

## 6. Code style

Comments:
* One short useful header comment at the top of each file.
* No paragraph comments. No comments between lines of code.

Python:
* Follow PEP 8, type hints on public functions, small functions, no dead code.
* Imports ordered standard library, third party, local. No wildcard imports.
* Use `pathlib`, f strings for non SQL text, and logging instead of print for anything that is not
  CLI output.

SQL:
* Uppercase keywords, one column per line, 4 space indent, snake_case names.
* Casts use the `::VARCHAR` style, not `CAST(... AS VARCHAR)`. SQLFluff rules RF02, LT05 and LT12
  must stay clean.

Shell and PowerShell:
* Scripts must work on Windows PowerShell and Linux. Quote paths. Fail fast on errors.
* Keep `.env` and `.env.example` in sync. Add any new variable to `.env.example` with a dummy value.

Documentation and prose, including README text, docstrings and commit messages:
* Do not use hyphens or em dashes in prose. Rewrite the sentence or use a comma, colon or the
  word "to". Hyphens inside code, identifiers, file names, commands and Markdown syntax are fine.
* Plain, direct wording. No filler.

## 7. Git hygiene

* Work on a branch named `fix/<short topic>` or `feat/<short topic>`. Never commit directly to `main`.
* One logical change per commit. Commit message format: `type(scope): short summary` where type is
  one of fix, feat, refactor, docs, test, chore.
* Run `git status` and `git diff` before every commit. Stage files by name. Never run `git add .`
  or `git add -A` blindly.
* Never commit `.env`, `secrets.toml`, `.venv`, caches, CSV exports or screenshots with real data.
* Never rewrite shared history. No force push. No amending commits already pushed.
* Do not push, open pull requests, merge or trigger a deploy unless the task explicitly says so.
* Never edit files outside the task scope. Do not reformat unrelated code.

## 8. Definition of done

A task is done only when all of these hold:

1. The change follows sections 4 and 6.
2. `dashboard-verify` has been run and passes, or any failure is reported honestly with the cause.
3. Empty selections, a single day window and a window with no prior period still render.
4. No secret, hyphenated prose or stray debugging output was introduced.
5. The final message lists: files changed, what and why, how it was verified, and anything left open.

## 9. When to stop and ask

Stop and ask the owner before:
* Changing gold table columns, dbt models, the schema or any Airflow DAG.
* Running anything against the Neon production database that writes or deletes data.
* Adding a paid service, a new cloud account or a new top level dependency.
* Any step that needs credentials you do not have. Never invent or guess credentials.

## 10. Skills available

Each skill lives at `.claude/skills/<name>/SKILL.md` with its procedure.
`dashboard-verify` additionally ships
`.claude/skills/dashboard-verify/scripts/smoke_check.py` (ruff plus pytest
smoke gate, run via `uv run python`).

* `dashboard-bugfix`: diagnose and fix dashboard bugs, with a symptom to cause map.
* `dashboard-feature`: add KPIs, charts, filters, pages and map views the right way.
* `dashboard-verify`: run static checks and manual test matrix before declaring done.
* `dashboard-release`: prepare and check a Streamlit Cloud and Neon deployment.
