# Scripts

```
src/jobs/                   # pipeline runtime
├── extract.py              # Mongo → bronze (incremental, watermark, upsert)
├── run_dbt_models.py       # dbt deps → silver/gold run+test
├── sql_test.py             # runs tests/data-quality/<layer>/*.sql
└── ci_seed_bronze.py       # CI fixture loader

scripts/                    # flat ops/dev scripts (Python + bash side by side)
├── run_tests.py / run_gx.py       # layer test wrappers
├── run_health_check.py / run_security_check.py
├── inspect_gold_schema.py / seed_demo_db.py / sync_gold_to_databricks.py
├── preflight.sh / clean.sh / setup_env.sh / monitor_logs.sh
└── backup.sh / ci_local.sh / db_shell.sh
```

## Python — `extract.py`

- Auto-discovers Mongo collections, picks watermark `updated_* > created_*`, `$gt` pushdown, `_id` upsert via `INSERT ... ON CONFLICT`, validates via recount. See `architecture.md`.

```bash
uv run python src/jobs/extract.py --tables orders,customers --full-refresh --dry-run
```

## Python — `sql_test.py`

Runs `tests/data-quality/<layer>/*.sql` — `SELECT` violating rows or `DO` block `RAISE`. `rollback()` on fail.

```bash
uv run python src/jobs/sql_test.py tests/data-quality/bronze
```

See `testing.md` for conventions.

## Bash

Ops helpers in `scripts/`: `preflight` (env/deps), `backup` (pg_dump/restore),
`ci_local` (local CI gates), `db_shell` (psql via `.env`), plus
`clean`/`setup_env`/`monitor_logs`.

```bash
bash scripts/preflight.sh --strict
bash scripts/ci_local.sh
uv run python scripts/run_tests.py all
```
