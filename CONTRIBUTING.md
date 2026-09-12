# Contributing

> Branch from `develop`, one logical change per PR, Conventional Commits enforced.

Full workflow, branch naming, and release steps: `docs/GIT_WORKFLOW.md`. This file is the short checklist.

## Setup
```bash
uv venv && uv sync
# enable local guards (commit-msg + pre-commit)
git config core.hooksPath .githooks
pipx install pre-commit && pre-commit install --hook-type commit-msg --hook-type pre-commit
# optional: run all hooks on demand
pre-commit run --all-files
```

## Before you push
```bash
uv run ruff format . && uv run ruff check .
uv run pytest
# if you touched models / SQL:
uv run dbt test --select silver|gold
uv run python scripts/python/sql_test.py tests/<layer>
```

## PR rules
- Title: `<type>(scope): <summary>` — see `pull_request_template.md` and `commitlint.yml`
- One responsibility per PR (AGENTS.md: one function = one responsibility, same for PRs)
- If you change stage order or redefine “success”, update **both** `pipeline/run_pipeline.ps1` and `airflow/dags/walmart_pipeline_dag.py` in the same PR
- Never commit `.env`, `gx/expectations/*` (generated), or large binaries without `git add -f` + review
- Keep `uv.lock` in sync: `uv lock` after any `pyproject.toml` change
