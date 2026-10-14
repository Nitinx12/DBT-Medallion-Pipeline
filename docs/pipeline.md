# Pipeline

Windows entry point: `pipeline/run_pipeline.ps1` (mirrored by `run_pipeline.bat` at the repo root and `main.py`). Same 8 stages, same exit contract. Linux stage wrappers live flat in `scripts/`.

## Stages

| # | Stage | Command |
|---|---|---|
| 0 | Preflight | `uv run python -c "import pyspark"` (3.5.x check) |
| 1 | Extract | `uv run python src/jobs/extract.py` |
| 2 | Bronze tests | `uv run python src/jobs/sql_test.py tests/data-quality/bronze` |
| 3 | dbt silver | `cd dbt && dbt run --select silver && dbt test --select silver` |
| 4 | Silver tests | `sql_test.py tests/data-quality/silver` |
| 5 | dbt gold | `dbt run/test --select gold` |
| 6 | Gold tests | `sql_test.py tests/data-quality/gold` |
| 7 | GX | `python -m gx.run --layer all` |

dbt stages `cd dbt/` and back; others run from repo root.

## Behavior

- **Stop on failure**: checks `$LASTEXITCODE`, calls `Stop-Pipeline` → summary + `exit 1`.
- **Env**: `Import-DotEnv` loads `.env` into process; `PYTHONPATH=$ProjectRoot`.
- **Sync rule**: stage order/success changes must update `run_pipeline.ps1` + Airflow DAG together.

## Run

```powershell
.\pipeline\run_pipeline.ps1
.\pipeline\run_pipeline.ps1 --dry-run
```

Exit `0` all pass, `1` any fail.

See `architecture.md` §2, `airflow.md` for DAG mirror.
