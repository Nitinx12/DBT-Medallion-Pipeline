# Testing

Two independent systems — do not conflate.

| System | Where | Run |
|---|---|---|
| dbt tests | `dbt/models/*/schema.yml` | `uv run dbt test --select silver|gold` |
| SQL suite | `tests/data-quality/{bronze,silver,gold}/*.sql` | `uv run python scripts/python/sql_test.py tests/data-quality/<layer>` |
| GX | `gx/` | `uv run python -m gx.run --layer all` |

## SQL suite

- **SELECT-style**: query returns violating rows → empty = PASS, rows = FAIL.
- **DO-block**: `RAISE EXCEPTION` on violation → no exception = PASS.

Auto-detected per file via `ResourceClosedError` vs rows. One connection per layer, `rollback()` on fail.

Add `schema.yml` tests for new models, `tests/unit/test_*.py` for new extract/utils logic (small fixtures, no live DB).

See `scripts.md` §2, `great-expectations.md`.
