# Scripts

```
src/jobs/                   # pipeline runtime (moved out of scripts/python/)
├── extract.py              # Mongo → bronze (incremental, watermark, upsert)
├── sql_test.py             # runs tests/data-quality/<layer>/*.sql
└── ci_seed_bronze.py       # CI fixture loader

scripts/
├── python/                 # ops/dev utilities
│   ├── health_check.py
│   ├── security_check.py
│   ├── inspect_gold_schema.py
│   ├── seed_demo_db.py
│   └── sync_gold_to_databricks.py
└── bash/                   # bash — detailed helpers
    ├── preflight.sh         # env & deps check
    ├── extract.sh           # wrapper for python extract
    ├── run_tests.sh         # bronze/silver/gold
    ├── run_pipeline.sh      # full 8 stages (Linux)
    ├── health_check.sh
    ├── security_check.sh
    ├── setup_env.sh
    ├── clean.sh
    └── monitor_logs.sh
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

Mirrors `pipeline/run_pipeline.ps1` for Linux. See `scripts/bash/README.md`.

```bash
bash scripts/bash/preflight.sh --strict
bash scripts/bash/run_pipeline.sh --full-refresh
```
