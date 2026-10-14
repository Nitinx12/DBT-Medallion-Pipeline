---
name: dashboard-verify
description: Run dashboard static checks and the manual test matrix before declaring done. Use after any dashboard edit.
---

# Dashboard verify

## Automated gate

Run `.claude/skills/dashboard-verify/scripts/smoke_check.py` via
`uv run python .claude/skills/dashboard-verify/scripts/smoke_check.py`.
It runs `ruff check`, `ruff format --check` on `dashboard/`, and the
smoke suite. All three must pass.

## Manual matrix (all must render, no tracebacks)

1. Empty selections on every touched page.
2. A single-day window.
3. A window with no prior period (deltas must degrade gracefully).
4. Default filters on all six pages plus home.

## Prose and secret hygiene

- No credentials in code, docs, logs, tests, screenshots, or commits.
- Prose without hyphens or em dashes (rewrite with a comma, colon,
  or the word "to"); hyphens inside code and commands are fine.
- No stray debugging output.
