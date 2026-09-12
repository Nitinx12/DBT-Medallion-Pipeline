---
paths:
  - "**/*.py"
  - "**/*.sql"
  - "pyproject.toml"
  - ".sqlfluffignore"
---

# Lint conventions

- Don't reorder imports in `dashboard/app.py`, `extract.py`,
  `seed_demo_db.py`, or `sync_gold_to_databricks.py` to "fix" E402 — the
  `sys.path.insert(...)` calls before those imports are intentional, and
  the E402 rule is already suppressed for these files in
  `pyproject.toml`'s `per-file-ignores`.
- Don't remove `sql/00_init_schema.sql` from `.sqlfluffignore` or try to
  make it parse — it contains psql meta-commands (`\gexec`, `\c`), which
  are not SQL and will never be parseable by sqlfluff.
- Run `uv run pre-commit run --all-files` after any lint-config change and
  confirm a clean pass before committing.
