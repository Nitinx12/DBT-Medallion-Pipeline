# AGENTS.md

Day-to-day conventions for this repo. For system design, read `docs/architecture.md` first.

## Overview
- Medallion ETL: MongoDB → Postgres bronze → silver → gold
- Quality gates: dbt tests, raw SQL checks, Great Expectations
- Three runners, one pipeline: `pipeline/run_pipeline.ps1`, Docker image (`main.py`), Airflow DAG
- Data contracts live in `contracts/<layer>/<table>.yml`
- Package manager: `uv`

## Setup
```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
```
- Add deps with `uv add <pkg>` (`--dev` for dev-only)
- Run everything through `uv run`, never bare `python` or `pip`
- `uv.lock` is the source of truth; run `uv lock` after editing `pyproject.toml`

## Dev Container
- Open in VS Code → "Reopen in Container", then run `uv sync`
- Image mirrors `docker/Dockerfile` (JDK 17 + `uv`)
- Postgres and Mongo are reached via `host.docker.internal`; never edit `.env` for this

## Structure
```
airflow/     DAGs, logs, plugins
contracts/   per-table data contracts
docker/      Dockerfiles, compose, entrypoint
docs/        deep-dive docs
gx/          Great Expectations suites + runner
jars/        Spark connectors (offline startup)
pipeline/    Windows entry point
scripts/     ops and dev scripts
src/jobs/    pipeline runtime
src/utils/   engine, connection, logger
sql/         functions, triggers, reports
tests/       SQL data-quality suite per layer
dbt/         silver + gold models
reports/     generated reports and charts
main.py      Docker entry point
```

## Coding Style
- `snake_case` for variables, functions, files, dbt models
- Type hints on every signature; docstring on every public function
- One function, one job
- Run `uv run ruff format .` and `uv run ruff check .` before committing

### Comments
- One short line above the function or block, explaining *why*
- No comments between lines of code
- Use an inline comment only when a line is not obvious
- Keep them plain and brief; no paragraphs

```python
# Postgres has no ObjectId type, so cast _id to string
def sanitize_for_postgres(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc
```

## Pipeline Stages
Eight fixed stages: preflight → extract → bronze tests → dbt silver → silver tests → dbt gold → gold tests → Great Expectations.

If you change the order, add a stage, or redefine success, update `run_pipeline.ps1` and the Airflow DAG in the same change.

## Data Contracts
- One YAML per table, never one per layer
- Edit only human fields (`description`, `transformation`, `tests`)
- Never hand-edit machine fields (`row_count`, `observed_*`, `sync_status`, `last_observed_at`)
- Re-sync after any schema change:
```bash
uv run python scripts/run_update_contract.py --check-only   # drift gate, writes nothing
uv run python scripts/run_update_contract.py                # sync counts, types, stats
uv run python scripts/run_update_contract.py --fix-types    # adopt observed DB types
```

## Testing
```bash
uv run dbt test --select silver          # dbt tests (also: gold)
uv run python src/jobs/sql_test.py tests/data-quality/silver   # SQL suite
uv run python -m gx.run --layer all      # Great Expectations
uv run pytest                            # unit + smoke
```
- Every new dbt model needs `schema.yml` tests
- Every new extract/transform function needs a unit test
- Use small fixtures, never real data

## Git
- Pull first: `git pull --rebase`
- One logical change per commit; stage files explicitly with `git add <file>`
- Conventional Commits, enforced by the local hook: `type(scope): summary`
- Types: `feat|fix|docs|chore|refactor|test|ci|build|perf|style|revert`
- Present tense, subject under 72 chars (aim for 50)
- Bare `area:` prefixes fail the hook; always use `type(scope):`
- Add a body line only when the *why* isn't obvious

```bash
git commit -m "fix(docker): pin JDK to 17" -m "Mongo connector is untested on JDK 21"
```

## Rules for Agents
**Do**
- Keep `.env` untouched; host fixes go in the DAG `_PREAMBLE` or `docker run` flags
- Read schema names from `.env` via `src/utils/engine.py`
- Auto-discover Mongo collections
- Run `uv run pytest` and the SQL suite before committing pipeline changes

**Don't**
- Commit `.venv`, `__pycache__`, `.env`, `data/raw`, or `data/processed`
- Mix unrelated changes in one commit
- Rewrite working stage logic unless asked
- Hardcode schema names or collection lists
