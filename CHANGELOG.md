# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bumps happen on `release/vX.Y.Z` branches; the `vX.Y.Z` tag triggers
`release.yml` which publishes versioned GHCR images and the GitHub Release
(see [docs/git-workflow.md](docs/git-workflow.md)).

## [Unreleased]

### Added

- **Split-schedule Airflow pipelines.** Replaced the single DAG with
  `walmart_mwf_morning` (Mon/Wed/Fri 11:00 Asia/Kolkata) and
  `walmart_rest_night` (Tue/Thu/Sat/Sun 23:00 Asia/Kolkata) in
  `airflow/dags/walmart_pipeline_dag.py`, covering all 7 days. Both run the
  same 10 tasks mirroring `run_pipeline.ps1`/`main.py`, with HTML
  success/failure summary mails via the `AIRFLOW__SMTP__*` settings.
  SMTP verified with a live test mail.
- **Hourly health-check DAG.** Added
  `airflow/dags/walmart_health_dag.py` (`walmart_hourly_health_check`,
  hourly Asia/Kolkata): parallel Postgres + Mongo pings via
  `src/utils/connection.py`, failure-only mail (`ONE_FAILED`) to avoid hourly
  spam.
- **Dashboard multipage restructure.** Added `dashboard/home.py` landing
  (KPIs + gold meta), `dashboard/pages/` (`1_Sales`, `2_Products`,
  `3_Customers`, `4_Categories`), and `dashboard/lib/` (`db.py`,
  `filters.py`, `charts.py`, `queries.py` re-export layer) plus
  `dashboard/Dockerfile`. Professionalized `.streamlit/config.toml`
  (server/runner/logger sections) with `secrets.toml.example`; per-deploy
  secrets live in `dashboard/.streamlit/secrets.toml` (git-ignored).
- **Pipeline image command sheet.** Added `file.txt` (repo root): env
  setup, tests, `Dockerfile.pipeline` build/run, Airflow stack up, DAG
  trigger, and cleanup commands.

### Changed

- **Docker stack rewritten from scratch.** `docker/` now holds minimal
  working files: `Dockerfile.pipeline` (python slim + JDK 17 + uv),
  `Dockerfile.airflow` (Airflow 3.3.0 + JDK 17 + uv), `compose.yml`
  (LocalExecutor: metadata db + api-server + scheduler), `entrypoint.sh`
  (Postgres wait + exec), and `dev-container.yml`.
- **dbt profiles moved out of `docker/`.** `docker/dbt/profiles.yml`
  moved to `dbt/profiles.yml`; `DBT_PROFILES_DIR` is now `/app/dbt`
  (`${{ github.workspace }}/dbt` in CI). Updated both Dockerfiles, the
  pipeline DAG `_PREAMBLE`, `ci.yml`/`dbt.yml`/`release.yml`, and
  `docs/docker.md`.
- **All GX code consolidated under `gx/`.** `pipeline/data_quality/`
  (`context.py`, `run.py`, `suites/`) moved to `gx/context.py`,
  `gx/run.py`, `gx/suites/` via `git mv` (history preserved); entry point
  is now `uv run python -m gx.run --layer all`. Updated `main.py`,
  `run_pipeline.ps1/.bat/.sh`, `Makefile`, the Airflow DAG, `README.md`,
  `docs/great-expectations.md`, `docs/pipeline.md`, `docs/tests.md`, and
  `build_report.py`; logger names renamed to `gx.*`. `pipeline/` keeps
  only the shell runners.
- **Dashboard helpers consolidated.** `dashboard/components.py`,
  `queries.py`, `theme.py` moved to `dashboard/helpers/`; all page/lib
  imports updated; legacy single-file `dashboard/app.py` removed in favor
  of `home.py` + `pages/`. Updated `README.md`, `pyproject.toml`
  per-file-ignores, lint docs, and report strings.
- **`.gitignore` hardened.** Added `**/secrets.toml` (real Streamlit
  secrets were committable) with `!**/secrets.toml.example` kept tracked;
  added `!dashboard/...`, `!gx/...` `__init__.py` exceptions so the new
  packages commit; `gx/.gitignore` now also covers generated
  `checkpoints/` + `validation_definitions/`.
- **Root `.streamlit/config.toml` restored.** Streamlit only reads
  `./.streamlit/` from the working directory, so the dashboard-owned
  config was ignored on local runs; root copy mirrors it while
  `dashboard/.streamlit/` stays the deploy source of truth.

- **SQL rectification (`sql/`).** New layout `analytics/` (16 gold
  reports), `functions/` (3 report functions), `procedure/`, `triggers/`,
  `scripts/init_schema.sql` — all at scripts-level commenting (header
  Purpose/Parameters/Security blocks, why-comments, usage examples).
  Wrote `sp_run_dq_tests` (in-DB DQ runner mirroring
  `tests/data-quality/`, logging to `gold.dq_test_runs`, never aborts
  early) and `sp_schema_monitor` (catalog snapshots +
  `gold.vw_schema_drift` view). Fixed: `RAISE` placeholder/arg mismatch
  in `sp_attach_loaded_at_triggers`, illegal OUT-after-default signature
  in `sp_run_dq_tests`, `COMMENT ON SCHEMA source` → `bronze` plus lost
  `\gexec`/`\c` flow in `init_schema.sql`, `schema_montior` typo and
  `dq-tests_runs` dashes in filenames. Live-deployed to `walmart_db`:
  bronze 12/12, full run 46/46 PASS. `docs/sql.md` rewritten for the new
  layout; `.sqlfluffignore` restored for the psql-only init script
  (zero parse errors repo-wide).

### Fixed

- **`AIRFLOW__CORE__FERNET_KEY` compose warning.** Removed the
  host-interpolated `${AIRFLOW__CORE__FERNET_KEY}` line from
  `docker/compose.yml` (`env_file: ../.env` already injects it);
  `docker compose config` now resolves the key with no warning.
- **Container Postgres `localhost` trap.** Documented that standalone
  `docker run` needs `-e POSTGRES_HOST=host.docker.internal -e
  MONGO_URI=mongodb://host.docker.internal:27017` (`.env` stays
  `localhost`; only DAG `_PREAMBLE`/run flags rewrite it).

## [0.2.1] — 2026-10-13

### Fixed

- **Airflow tasks could not reach the Execution API.** Set
  `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` in the
  `docker/compose.yml` shared block — workers defaulted to
  `localhost:8080` inside the scheduler container, got
  connection-refused, and the supervisor killed them after 4 retries.
  All 3 DAGs verified green end to end after the fix.
- **Execution API JWT 403s after any independent recreate.**
  `AIRFLOW__API__SECRET_KEY` / `AIRFLOW__API_AUTH__JWT_SECRET` were
  unset, so Airflow 3.3 autogenerated them per container and
  scheduler/apiserver disagreed (`Signature verification failed`).
  Both are now pinned as shared local-dev values in compose (move to a
  secret store for real deploys).
- **Pipeline/health mails crashed on manual runs.** Subjects/bodies
  templated `{{ ds }}` (undefined without a logical date); they now use
  `{{ run_id }}` plus the XCom `date` fallback. Also created the missing
  `smtp_default` connection (Gmail STARTTLS + sender) — live mail
  received and a full `walmart_mwf_morning` run went green.
- **LaTeX report rebuilt.** `reports/report.tex` fixed (UTF-8 error in a
  listing, tables overflowing the page) and content synced to the repo
  (LocalExecutor stack, 3 DAGs, `src/` layout, `gx/` runner, 7 CI jobs);
  `reports/report.pdf` regenerated (15 pages, clean build).

### Changed

- **DAG tasks call venv binaries directly.** All `@task.bash` bodies in
  both DAG files use `/app/.venv/bin/python` + `/app/.venv/bin/dbt`
  instead of `uv run`, with a `uv sync --frozen` bootstrap guard in
  `_PREAMBLE` if the venv is missing.

## [0.2.0] — 2026-10-01

### Added

- **Windows Batch runner.** Added `pipeline/run_pipeline.bat` — CMD-native mirror of `pipeline/run_pipeline.ps1` and `scripts/bash/run_pipeline.sh` — plus root wrapper `run_pipeline.bat`. Same 8-stage gate (preflight → extract → bronze tests → dbt silver → silver tests → dbt gold → gold tests → Great Expectations), fail-fast, `.env` loading, `pyspark 3.5.x` preflight, ANSI colors, and `logs/pipeline_YYYY-MM-DD.log` logging. Enables double-click / `cmd.exe` execution on Windows without PowerShell.

### Changed

- **Dependencies pruned to what the code actually imports.** Removed phantom
  PyPI packages (`logging`, `npm`, `package-name`, `postgres`, `yml`, `mongo`,
  `dotenv`, `databricks`) and unused ones (`dash`, `matplotlib`, `seaborn`,
  `pyarrow`). Fixed the `polors` typo to `polars`, and declared `pendulum`,
  which the DAG imports directly. `uv.lock` regenerated.
- **Generated artifacts out of git.** `jars/*.jar` moved to Git LFS;
  `reports/charts/` untracked and ignored (PR template already forbade them).

## [0.1.0] — 2026-09-12

First tagged release: the Walmart medallion data pipeline (bronze → silver →
gold) with Airflow orchestration, dbt models, Great Expectations data quality,
Streamlit dashboard, and a production-ready git/CI workflow.

### Added

- Git workflow: `feature/*` → PR → `develop` → PR → `main` → tag, with branch
  guardrails, commitlint commit-msg hook (CR-safe on Windows), CODEOWNERS, and
  PR template.
- CI gate: lint (Ruff + SQLFluff) → unit tests (pytest, mocked) → DAG
  integrity (DagBag import + cycle check) → docker build (both images) →
  integration (live Postgres: bronze SQL checks → dbt silver → dbt gold →
  Great Expectations).
- Release pipeline: `release.yml` publishes semver GHCR images + GitHub
  Release; `cd.yml` owns only the rolling `latest` image.
- Unit tests for `utils/` and the extract decision logic (mocked, no live
  services).
- Streamlit sales dashboard (`dashboard/`).
- Docs suite: `docs/` — architecture, ci-cd, git-workflow, dbt, docker,
  airflow, great-expectations, pipeline, scripts, sql, tests, utils, health.

### Changed

- Scripts reorganized into `scripts/python/` and `scripts/bash/`; duplicate
  shims removed.
- Docs renamed to industry-standard filenames and trimmed.
- `gx/expectations/` and `gx/uncommitted/` no longer tracked (generated).

### Fixed

- `commit-msg` git hook strips CR so commitlint works on Windows checkouts.
