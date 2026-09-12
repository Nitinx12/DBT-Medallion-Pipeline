<!--
PR Title must follow Conventional Commits:  <type>(scope): <summary>
Types: feat, fix, docs, chore, refactor, test, ci, build, perf, style, revert
Example: feat(extract): add watermark fallback when no unique index
 AGENTS.md enforces this via commitlint.yml
-->

## What & Why

<!-- One paragraph: what changes, why needed. Link issue if any: Closes #123 -->

## Changes

- [ ]
- [ ]

## How tested

- [ ] `uv run ruff format . && uv run ruff check .`
- [ ] `uv run pytest` (or `tests/unit` gate in CI)
- [ ] `uv run dbt test --select <silver|gold>` (if models changed)
- [ ] `uv run python scripts/python/sql_test.py tests/<layer>` (if SQL checks changed)

## Pipeline impact

<!-- Check one. If you change stage order/add a stage/redefine success, you MUST update BOTH pipeline/run_pipeline.ps1 AND airflow/dags/walmart_pipeline_dag.py in this PR (ARCHITECTURE.md §7, AGENTS.md Pipeline Stage Rule) -->

- [ ] No pipeline stage change
- [ ] Stage order / success definition changed — updated both runners

## Checklist

- [ ] One logical change only (no bundled unrelated fixes)
- [ ] `uv.lock` updated via `uv lock` if `pyproject.toml` changed
- [ ] No secrets, `.env`, or generated artifacts (`gx/expectations/*`, `reports/charts/*`, `jars/*.jar` unless intentional)
- [ ] Docs updated (`docs/` or `README.md`) if behavior changed

## Screenshots / logs (if UI or pipeline output changed)
