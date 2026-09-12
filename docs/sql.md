# SQL

Hand-written analytics on `gold` (and `silver` staging).

## Reports (`sql/`)

- `00_init_schema.sql` — schemas
- `01-03` — brand/category/payment reference
- `04-07` — functions/triggers (`fn_customer_report`, `trg_loaded`)
- `08-11` — order/payment/KPI analysis
- `12-15` — segmentation, cohorts, Pareto
- `16-20` — store performance, basket, ABC, repeat purchase, no-sales dates

All `postgres` dialect, linted via `sqlfluff lint --dialect postgres`.

## Checks (`tests/`)

- **Bronze (3)**: tables exist, columns exist, metadata cols.
- **Silver (9)**: dupes, nulls, negative, FK, date ranges, domain, spaces, business rules.
- **Gold (7)**: not empty, date ranges, dupes, negative, referential, spaces, row counts.

Run: `uv run python scripts/python/sql_test.py tests/<layer>`

See `tests.md`, `dbt.md`.
