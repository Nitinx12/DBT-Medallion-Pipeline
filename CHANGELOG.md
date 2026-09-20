# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bumps happen on `release/vX.Y.Z` branches; the `vX.Y.Z` tag triggers
`release.yml` which publishes versioned GHCR images and the GitHub Release
(see [docs/git-workflow.md](docs/git-workflow.md)).

## [Unreleased]

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
