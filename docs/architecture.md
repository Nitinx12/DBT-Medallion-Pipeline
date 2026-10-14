# Architecture

Medallion ETL: MongoDB → Postgres (bronze → silver → gold) with 8 quality gates.

```mermaid
flowchart LR
  MONGO[(MongoDB)] -->|extract.py| BRONZE[(bronze<br/>raw)]
  BRONZE -->|dbt silver| SILVER[(silver<br/>clean)]
  SILVER -->|dbt gold| GOLD[(gold<br/>star)]
  GOLD --> BI[reports/]

  classDef mongo fill:#13AA52,color:#fff,stroke:#0d7a3b
  classDef bronze fill:#B5651D,color:#fff,stroke:#7a4413
  classDef silver fill:#6B7B8C,color:#fff,stroke:#4a565f
  classDef gold fill:#D4A017,color:#1A1F2B,stroke:#8a6d1f
  classDef bi fill:#0071CE,color:#fff,stroke:#004C91
  class MONGO mongo
  class BRONZE bronze
  class SILVER silver
  class GOLD gold
  class BI bi
```

## Pipeline (8 stages)
`0 preflight → 1 extract → 2 bronze tests → 3 dbt silver → 4 silver tests → 5 dbt gold → 6 gold tests → 7 GX`

- **Stops on first failure** (exit code check / Airflow `all_success`).
- **One logic, five runners**: `pipeline/run_pipeline.ps1` (canonical, Windows),
  `run_pipeline.bat` (repo root, double-clickable CMD), `main.py` (standalone
  image), `airflow/dags/walmart_pipeline_dag.py` (scheduled), `make data-pipeline`
  (granular targets). Keep stage order in sync.

## Layers & Gates

- **Bronze**: `src/jobs/extract.py` — auto-discovers collections, watermark `updated_* > created_*`, `INSERT ... ON CONFLICT (_id)` upsert via `etl_watermarks`/`etl_logs`.
- **Silver**: 9 dbt models — `dbt test` + 9 SQL checks (`tests/data-quality/silver/`).
- **Gold**: 8 dbt models (7 dims + 1 fact, snowflake) — `dbt test` + 7 SQL checks (`tests/data-quality/gold/`).
- **Tests**: dbt tests (`schema.yml`) + standalone SQL suite (`src/jobs/sql_test.py`) — separate systems.

## Infra

- **Docker**: `docker/Dockerfile.pipeline` (standalone) + `docker/Dockerfile.airflow` (Compose stack). See `docker.md`.
- **Localhost fix**: `.env` stays `localhost`; containers rewrite to `host.docker.internal` in DAG `_PREAMBLE`/`docker run`.
- **Shared**: `src/utils/engine.py` (env validation at import), `src/utils/connection.py` (cached), `src/utils/logger.py` (console+file).

## Layout
```
airflow/  contracts/  dashboard/  docker/  docs/  gx/  jars/  pipeline/
scripts/  sql/  tests/  src/  dbt/  reports/
```

## Next
`pipeline.md` · `airflow.md` · `docker.md` · `dbt.md` · `scripts.md` · `tests.md` · `src-utils.md` · `health.md`
