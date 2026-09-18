<p align="center">
  <a href="https://github.com/Nitinx12/Walmart_DBT">
    <img src="assets/dbt-logo.png" width="84" height="84" alt="dbt logo" />
  </a>
</p>

<h1 align="center">DBT Medallion Data Pipeline</h1>

<p align="center">
  A production-style <b>MongoDB → PostgreSQL → dbt</b> pipeline: incremental PySpark extraction,<br/>
  a tested medallion warehouse (<b>bronze → silver → gold</b>), orchestrated with <b>Airflow</b>,<br/>
  containerized with <b>Docker</b>, and gated by two independent layers of data-quality checks at every handoff.
</p>
<p align="center">
  <em>Built to mirror how a real analytics-engineering team would ship this — not a notebook demo.</em>
</p>

<!-- Primary stack -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13"/>
  <img src="https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white" alt="Ubuntu"/>
  <img src="https://img.shields.io/badge/PySpark-4.1-E25A1C?logo=apachespark&logoColor=white" alt="PySpark 4.1"/>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/MongoDB-source-47A248?logo=mongodb&logoColor=white" alt="MongoDB"/>
  <img src="https://img.shields.io/badge/Apache%20Airflow-3.3.0-017CEE?logo=apacheairflow&logoColor=white" alt="Airflow"/>
  <img src="https://img.shields.io/badge/dbt-core-FF694B?logo=dbt&logoColor=white" alt="dbt"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Architecture-Medallion-D4AF37" alt="Medallion"/>
</p>

<!-- Tooling & quality -->
<p align="center">
  <img src="https://img.shields.io/badge/Streamlit-1.62-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/Plotly-7.0-3F4F75?logo=plotly&logoColor=white" alt="Plotly"/>
  <a href="https://github.com/Nitinx12/Walmart_DBT/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Nitinx12/Walmart_DBT/ci.yml?label=CI&logo=github&labelColor=0F172A" alt="CI"/></a>
  <a href="https://github.com/Nitinx12/Walmart_DBT/releases"><img src="https://img.shields.io/github/v/release/Nitinx12/Walmart_DBT?label=Last%20Release&color=0ea5e9" alt="Last Release"/></a>
  <img src="https://img.shields.io/badge/Ruff-checked-000000?logo=ruff&logoColor=white" alt="Ruff"/>
  <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=precommit&logoColor=white" alt="pre-commit"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"/></a>
</p>

<!-- Community -->
<p align="center">
  <a href="https://discord.gg/"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white" alt="Discord"/></a>
  <a href="https://www.linkedin.com/"><img src="https://img.shields.io/badge/LinkedIn-Connect-0077B5?logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
  <a href="https://twitter.com/"><img src="https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white" alt="Twitter"/></a>
  <a href="https://github.com/vinta/awesome-python"><img src="https://awesome.re/mentioned-badge.svg" alt="Awesome Python"/></a>
</p>

<p align="center">
  <a href="https://walmartdbt-b3fdfqwyky3ghzr5syyxtu.streamlit.app/"><img src="https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white&style=for-the-badge" alt="Live Demo"/></a>
  &nbsp;
  <a href="https://github.com/Nitinx12/Walmart_DBT"><img src="https://img.shields.io/badge/View%20on%20GitHub-0F172A?logo=github&logoColor=white&style=for-the-badge" alt="GitHub"/></a>
</p>

---

## Live Dashboard

<p align="center">
  <a href="https://walmartdbt-b3fdfqwyky3ghzr5syyxtu.streamlit.app/"><b>Live Demo</b></a> &mdash; interactive dashboard on the <code>gold</code> schema &middot; <a href="dashboard/README.md">docs</a>
</p>

<p align="center">
  <a href="https://walmartdbt-b3fdfqwyky3ghzr5syyxtu.streamlit.app/">
    <img src="assets/image.png" width="90%" alt="Walmart Sales Dashboard — gold schema" style="border-radius:12px; border:1px solid #e2e8f0; box-shadow: 0 8px 30px rgba(15,23,42,0.12);" />
  </a>
</p>
<p align="center"><sub>Seeded demo DB &mdash; not the live pipeline. See <a href="scripts/python/seed_demo_db.py"><code>seed_demo_db.py</code></a>.</sub></p>

## Architecture at a glance

<p align="center">
  <img src="https://img.shields.io/badge/Postgres-walmart__db-4169E1?style=flat-square" alt="walmart_db"/>
  &nbsp;
  <img src="https://img.shields.io/badge/bronze-raw%201%3A1-CD7F32?style=flat-square" alt="bronze"/>
  <img src="https://img.shields.io/badge/silver-typed%20%2B%20SCD2-C0C0C0?style=flat-square" alt="silver"/>
  <img src="https://img.shields.io/badge/gold-star%2Fsnowflake-D4AF37?style=flat-square" alt="gold"/>
</p>

```mermaid
flowchart LR
    MONGO[("MongoDB<br/>operational source")] -->|"PySpark, watermark-based<br/>incremental extract"| BRONZE

    subgraph PG["PostgreSQL — walmart_db"]
        BRONZE[("bronze<br/>raw, 1:1 with Mongo")]
        SILVER[("silver<br/>deduped, typed, SCD2")]
        GOLD[("gold<br/>dimensional star/snowflake")]
        BRONZE -->|"dbt + SQL tests"| SILVER
        SILVER -->|"dbt + SQL tests"| GOLD
    end

    GOLD --> BI["reports/<br/>brand & category analysis"]

    classDef bronze fill:#CD7F32,color:#fff,stroke:#8b5a2b
    classDef silver fill:#C0C0C0,color:#1a1a1a,stroke:#888888
    classDef gold fill:#D4AF37,color:#1a1a1a,stroke:#8a6d1f
    class BRONZE bronze
    class SILVER silver
    class GOLD gold
```

<p align="center"><sub>Every arrow into <code>silver</code> and <code>gold</code> is a <b>quality gate</b> — the next layer only builds if the prior layer's tests pass. Full breakdown: <a href="docs/architecture.md"><code>docs/architecture.md</code></a> §4.</sub></p>

## Orchestration — one pipeline, run three ways

The same eight stages run locally via PowerShell, on a schedule in Airflow, or through the standalone Docker runner:

```mermaid
flowchart TD
    S0["0 · Preflight"] --> S1["1 · Extract<br/>Mongo → bronze"]
    S1 --> S2["2 · Bronze SQL tests"]
    S2 --> S3["3 · dbt run + test — silver"]
    S3 --> S4["4 · Silver SQL tests"]
    S4 --> S5["5 · dbt run + test — gold"]
    S5 --> S6["6 · Gold SQL tests"]
    S6 --> S7["7 · Great Expectations<br/>Bronze · Silver · Gold"]

    classDef stage fill:#1a2a3a,color:#fff,stroke:#4a90d9
    class S0,S1,S2,S3,S4,S5,S6 stage
```

<p align="center"><sub>In Airflow this is <code>walmart_medallion_pipeline</code>, with <code>all_success</code> trigger rules stopping the DAG the moment any stage fails. Full DAG detail: <a href="docs/airflow.md"><code>docs/airflow.md</code></a>.</sub></p>

## Highlights

| Area | What's there |
|---|---|
| **Incremental extraction** | Watermark-based `$gt` pushdown from Mongo, real `MERGE`-style upserts, automatic fallback when no watermark or unique index exists |
| **Modeling** | 17 dbt models (9 silver + 8 gold), 100+ tests, SCD Type 2 snapshots |
| **Data quality** | dbt-native tests, standalone schema-driven SQL checks, and a final Great Expectations gate across Bronze, Silver, and Gold |
| **Runners** | Windows/PowerShell, Airflow, and the standalone runner execute the same eight stages |
| **Containerization** | Docker Compose stack (CeleryExecutor: scheduler, workers, triggerer, Redis) plus a self-contained pipeline image |
| **Dashboard** | Professional Streamlit + Plotly dashboard querying the gold schema directly — [live demo](https://walmartdbt-b3fdfqwyky3ghzr5syyxtu.streamlit.app/), source in [`dashboard/`](dashboard/) |
| **CI/CD** | Lint, DAG-integrity checks, and a live bronze→silver→gold run against Postgres on every PR; images published to GHCR on merge — [`docs/ci-cd.md`](docs/ci-cd.md) |

## Tech Stack

<p align="center">

| Layer | Technology | Version / Notes |
|---|---|---|
| **Language** | Python | `3.13` (CI: `3.11`, Docker: `3.12-slim`) |
| **OS** | Ubuntu | `24.04` (CI `ubuntu-latest`, Docker `bookworm`) |
| **Compute** | PySpark | `4.1.x` (with `openjdk-17`) |
| **Warehouse** | PostgreSQL | `16` — medallion schemas `bronze` / `silver` / `gold` |
| **Source** | MongoDB | Operational source, incremental `$gt` watermark |
| **Transform** | dbt-core + dbt-postgres | `1.12` / `1.11` — 17 models, 100+ tests |
| **Orchestration** | Apache Airflow | `3.3.x` CeleryExecutor |
| **Quality** | Great Expectations | `1.21` — Bronze · Silver · Gold suites |
| **BI** | Streamlit + Plotly | `1.62` + `7.0` — gold star schema |
| **Package mgr** | uv | `uv.lock` is source of truth |
| **Lint / Format** | Ruff + SQLFluff + pre-commit | `ruff check` / `ruff format` / `sqlfluff lint` |
| **Containers** | Docker / Compose | `Dockerfile` + `Dockerfile.airflow` |
| **CI** | GitHub Actions | lint · dashboard-smoke · unit · DAG · Docker · integration |

</p>

<p align="center">
  <sub><code>Python</code> · <code>PySpark</code> · <code>dbt-core</code> · <code>PostgreSQL</code> · <code>MongoDB</code> · <code>Apache Airflow</code> · <code>Docker</code> · <code>Streamlit</code> · <code>Plotly</code> · <code>uv</code> · <code>Ruff</code> · <code>Great Expectations</code></sub>
</p>

## Run it

```powershell
# Local, Windows
./pipeline/run_pipeline.ps1

# Run Great Expectations checks alone when needed
uv run python -m pipeline.data_quality.run --layer all

# Standalone container runner (supply container-correct database hosts)
docker run --env-file .env walmart-pipeline

# Full Airflow stack
docker compose -f docker/compose.yml up

# Sales dashboard (reads from your local gold schema)
uv run streamlit run dashboard/app.py
```

## Documentation

This README is the pitch. Everything below is the engineering detail:

| Doc | Covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Full system design and execution-path status |
| [`docs/airflow.md`](docs/airflow.md) | The DAG, task by task |
| [`docs/dbt.md`](docs/dbt.md) | Models, grain, SCD types, tests |
| [`docs/docker.md`](docs/docker.md) | Both images, why two, build details |
| [`docs/pipeline.md`](docs/pipeline.md) | The PowerShell entry point |
| [`docs/scripts.md`](docs/scripts.md) | `extract.py`'s incremental vs. full-reload logic |
| [`docs/tests.md`](docs/tests.md) | What the raw SQL checks actually check |
| [`docs/great-expectations.md`](docs/great-expectations.md) | Great Expectations suites, commands, artifacts, and troubleshooting |
| [`docs/utils.md`](docs/utils.md) | Shared config/connection/logging |
| [`docs/ci-cd.md`](docs/ci-cd.md) | See how CI/CD works |
| [`docs/health.md`](docs/health.md) | Local health and security checks |
| [`dashboard/README.md`](dashboard/README.md) | Dashboard design: schema, caching, chart choices |

Full pipeline script (`run_pipeline.ps1`): [view on Google Drive](https://drive.google.com/file/d/1vSPYN8GvC5cFMEHf7EVjwSq4HHAbCZRF/view?usp=sharing)

---

<p align="center">
  <sub>Built with ❤️ for the data community · <a href="LICENSE">MIT License</a> · <a href="https://github.com/Nitinx12/Walmart_DBT/issues">Report a bug</a> · <a href="https://github.com/Nitinx12/Walmart_DBT">⭐ Star on GitHub</a></sub>
</p>

<p align="center">
  <a href="https://discord.gg/"><img src="https://img.shields.io/badge/chat-on%20Discord-5865F2?logo=discord&logoColor=white" alt="Discord chat"/></a>
  <a href="https://www.linkedin.com/"><img src="https://img.shields.io/badge/connect-on%20LinkedIn-0077B5?logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
  <a href="https://twitter.com/"><img src="https://img.shields.io/badge/follow-on%20X-000000?logo=x&logoColor=white" alt="Twitter"/></a>
</p>

📧 Reach out if you'd like a walkthrough of any part of this project.
