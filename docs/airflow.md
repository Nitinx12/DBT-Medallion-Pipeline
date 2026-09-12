# Airflow

DAG `walmart_medallion_pipeline` in `airflow/dags/walmart_pipeline_dag.py` — 10 tasks mirroring the 8 stages (dbt run/test split).

## DAG

`0 preflight → 1 extract → 2 bronze_tests → 3 dbt_silver_run → 3b dbt_silver_test → 4 silver_tests → 5 dbt_gold_run → 5b dbt_gold_test → 6 gold_tests → 7 gx`

- **Trigger**: `all_success` — downstream blocked if upstream fails.
- **Executor**: CeleryExecutor; `airflow-worker` runs all `bash` tasks.
- **Env**: `_PREAMBLE` sources `.env`, rewrites `POSTGRES_HOST`/`MONGO_URI` to `host.docker.internal`, fixes `PYSPARK_PYTHON`.

## Run

```bash
docker compose -f docker/compose.yml up
# UI: http://localhost:8080
```

## Parity

Keep `run_pipeline.ps1` and DAG stage order/success in sync — no automatic enforcement.

See `architecture.md` §2, `pipeline.md`, `docker.md`.
