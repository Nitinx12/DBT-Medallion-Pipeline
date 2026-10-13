# SQL

Hand-written analytics on `gold` (and `silver` staging).

## Layout (`sql/`)

- `scripts/init_schema.sql` — database + bronze/silver/gold schemas (psql only)
- `functions/` — report functions (`fn_customer_report`, `fn_product_report`,
  `fn_sales_trend_analysis`): dynamic filters, whitelisted sorts, usage examples
- `procedure/` — `sp_run_dq_tests` (in-DB DQ runner logging to
  `gold.dq_test_runs`), `sp_schema_monitor` (catalog snapshots +
  `gold.vw_schema_drift` view)
- `triggers/trg_loaded.sql` — `*_loaded_at` stamp functions + deploy procedure
- `analytics/` — 16 gold read-only reports (revenue share, KPI summary,
  cohorts, Pareto, basket, ABC, ...)

All `postgres` dialect, linted via `sqlfluff lint --dialect postgres`.

## Checks (`tests/`)

- **Bronze (3)**: tables exist, columns exist, metadata cols.
- **Silver (9)**: dupes, nulls, negative, FK, date ranges, domain, spaces, business rules.
- **Gold (7)**: not empty, date ranges, dupes, negative, referential, spaces, row counts.

Run: `uv run python src/jobs/sql_test.py tests/data-quality/<layer>`

See `tests.md`, `dbt.md`.
