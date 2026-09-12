# Docker

Two images, two jobs. Both `python:3.12-slim` + JDK 17 + `uv`.

| Image | Base | Code delivery | Runs |
|---|---|---|---|
| `walmart-pipeline` (`docker/Dockerfile`) | `python:3.12-slim` | `COPY . .` baked in | `entrypoint.sh` → `main.py` (all 8 stages, standalone) |
| `walmart-airflow` (`docker/Dockerfile.airflow`) | `apache/airflow:3.3.0-python3.11` | bind mount `..:/app` | `airflow-worker` executes DAG tasks |

```bash
# Standalone
docker build -t walmart-pipeline -f docker/Dockerfile .
docker run --env-file .env walmart-pipeline

# Airflow stack
docker compose -f docker/compose.yml up
```

## Key details

- **JDK 17** pinned — mongo connector 10.4.0 needs Spark 3.5.x + JDK 17.
- **PYTHONPATH=/app** in both images.
- **Compose**: CeleryExecutor (scheduler, worker, triggerer, redis, postgres meta). Worker runs `bash` tasks; code changes need no rebuild (bind mount).
- **Localhost fix**: `.env` stays `localhost`; DAG `_PREAMBLE` rewrites to `host.docker.internal` for containers.
- **Profiles**: host uses `~/.dbt/profiles.yml`; Airflow uses `docker/dbt/profiles.yml` via `DBT_PROFILES_DIR`.

See `architecture.md` §6, `docker/Dockerfile` / `docker/Dockerfile.airflow`.
