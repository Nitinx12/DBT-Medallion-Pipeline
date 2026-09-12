# Walmart Medallion Pipeline

## Stack
uv (Python), dbt-postgres, Airflow, Great Expectations, pre-commit, sqlfluff, ruff.
Package manager is uv — always prefix Python tool invocations with `uv run`
(`uv run pytest`, `uv run pre-commit run --all-files`, `uv run ruff check .`).
Tools installed globally are NOT on PATH inside uv's project venv; don't assume
`pytest` or `pre-commit` work bare.

## Commands
- Install/sync deps: `uv sync`
- Run tests: `uv run pytest`
- Run all lint/format hooks: `uv run pre-commit run --all-files`
- dbt: run from inside `walmart_dbt/` or pass `--project-dir walmart_dbt`
  (`dbt debug`, `dbt parse`, `dbt test`)

## Git workflow
- `core.hooksPath` is `.githooks` — commit-msg enforces Conventional Commits
  (`type(scope): summary`, subject ≤72 chars) and pre-commit runs ruff,
  ruff-format, sqlfluff, and file-hygiene checks.
- Hook files must have the executable bit set (`git ls-files -s .githooks/`
  should show `100755`, not `100644`) or they silently fail to fire.
- `main` has a GitHub ruleset requiring CodeQL code scanning to complete
  before a push is accepted. **Direct pushes to main will be rejected.**
  Always: branch → push branch → open PR on GitHub → wait for CodeQL →
  merge via GitHub UI → delete branch. Don't retry a direct push to main
  expecting it to eventually pass; the check runs per-PR, not per-push.

## Secrets
- Never commit `.env` — only `.env.example` with placeholder values.
- If a secret is ever committed, rotate it immediately, then purge it from
  history with `git filter-repo --path .env --invert-paths --force`
  (invoke via its install path directly if `git filter-repo` isn't on PATH;
  don't assume `python -m git_filter_repo` works — it only works in the
  Python environment it was actually installed into).

## Known lint exceptions (don't "fix" these)
- `pyproject.toml` has `[tool.ruff.lint.per-file-ignores]` suppressing E402 in
  `dashboard/app.py`, `extract.py`, `seed_demo_db.py`, and
  `sync_gold_to_databricks.py` — these intentionally call
  `sys.path.insert(...)` before local imports.
- `.sqlfluffignore` excludes `sql/00_init_schema.sql` — it contains psql
  meta-commands (`\gexec`, `\c`) that aren't valid SQL and will never parse.

## Windows/PowerShell notes
- `!` is not a PowerShell comment character — use `#`.
- `Select-Object -Index` needs a parenthesized range: `-Index (24..33)`, not
  `-Index 24..33`.
- `dos2unix` isn't available by default; check line endings with
  `file <path>` via `bash -c` instead, or normalize via `.gitattributes`.
