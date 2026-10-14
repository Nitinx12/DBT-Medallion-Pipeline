---
name: dashboard-release
description: Prepare and check a Streamlit Cloud and Neon deployment. Use for dashboard releases and deploy debugging.
---

# Dashboard release

## Preconditions (stop and ask if any is missing)

- Neon project with pooled (app) and direct (dbt) hosts; connection
  strings stored outside the repo.
- GitHub secrets for the refresh workflow; `dashboard_ro` role created
  from `sql/security/dashboard_readonly_role.sql` with a generated secret.
- Cloud app main file is `dashboard/home.py`, branch `main`.

## Checklist

1. `dashboard/requirements.txt` installs without `databricks-sql-connector`;
   CI `dashboard-smoke` proves the import guard.
2. Cloud secrets carry the same keys as
   `dashboard/.streamlit/secrets.toml.example` (Neon values,
   `dashboard_ro` user). Never commit `secrets.toml`.
3. Cold start works: app sleep plus Neon wake is slow on first visit;
   confirm Home loads and the freshness badge goes green.
4. Click all six pages with default filters; CSV downloads work.
5. Refresh workflow: scheduled runs stay green and the Data Health page
   shows fresh row counts.
6. Never run anything against Neon production that writes or deletes;
   never add paid services without owner approval.
